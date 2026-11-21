from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from src.fault_injection.fault_plan import FaultPlan, load_fault_plan
from src.fault_injection.injector import F1DriverKillInjector


ROOT = Path(__file__).resolve().parents[1]


class FaultPlanTests(unittest.TestCase):
    def test_frozen_f0_plan_disables_injection(self):
        plan = load_fault_plan(ROOT / "fault_plans/F0_no_failure.yaml", "F0")
        self.assertFalse(plan.enabled)

    def test_f1_plan_freezes_interior_batch_and_record_position(self):
        plan = load_fault_plan(ROOT / "fault_plans/F1_after_object_before_metadata.yaml", "F1")
        self.assertEqual((plan.batch_id, plan.record_index), (14, 5))
        self.assertEqual(plan.stage, "after_object_put_before_metadata_commit")

    def test_fault_point_must_match_selected_plan(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            load_fault_plan(ROOT / "fault_plans/F0_no_failure.yaml", "F1")


class F1InjectorTests(unittest.TestCase):
    def setUp(self):
        self.plan = FaultPlan(
            fault_point="F1", enabled=True, batch_id=14, record_index=5,
            stage="after_object_put_before_metadata_commit",
            target="drv-{run_id}-a1", method="sigkill_on_marker",
            rationale="frozen test rationale long enough to meet validation",
        )

    def test_publishes_atomic_marker_then_waits_at_exact_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            waited = []
            injector = F1DriverKillInjector(self.plan, "test-run", "B1", Path(tmp),
                                            wait_for_kill=lambda: waited.append(True))
            with self.assertRaisesRegex(RuntimeError, "wait returned"):
                injector.after_object_put(
                    batch_id=14, record_index=5, recording_id="rec-5",
                    object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                    metadata_rows_committed=4, put_confirmed=True,
                )
            marker = Path(tmp) / "test-run.kill"
            event = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(event["target"], "drv-test-run-a1")
            self.assertEqual(event["fault_point"], "F1")
            self.assertEqual(event["metadata_rows_committed"], 4)
            self.assertFalse((Path(tmp) / ".test-run.kill.tmp").exists())
            self.assertEqual(waited, [True])

    def test_f0_never_writes_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = FaultPlan(fault_point="F0", enabled=False)
            injector = F1DriverKillInjector(plan, "f0-run", "B0", Path(tmp))
            self.assertFalse(injector.after_object_put(
                batch_id=14, record_index=5, recording_id="rec-5",
                object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                metadata_rows_committed=4, put_confirmed=True,
            ))
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_rejects_target_without_confirmed_put_or_wrong_commit_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = F1DriverKillInjector(self.plan, "test-run", "B1", Path(tmp), wait_for_kill=lambda: None)
            args = dict(batch_id=14, record_index=5, recording_id="rec-5",
                        object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                        metadata_rows_committed=4)
            with self.assertRaisesRegex(RuntimeError, "newly confirmed"):
                injector.after_object_put(**args, put_confirmed=False)
            with self.assertRaisesRegex(RuntimeError, "expected 4"):
                injector.after_object_put(**{**args, "metadata_rows_committed": 3}, put_confirmed=True)


if __name__ == "__main__":
    unittest.main()
