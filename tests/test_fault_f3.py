from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.fault_injection.fault_plan import load_fault_plan
from src.fault_injection.injector import DriverKillInjector


ROOT = Path(__file__).resolve().parents[1]


class F3FaultTests(unittest.TestCase):
    def setUp(self):
        self.plan = load_fault_plan(
            ROOT / "fault_plans/F3_after_checkpoint.yaml", "F3"
        )

    def test_plan_freezes_checkpoint_before_next_event_publication(self):
        self.assertEqual((self.plan.batch_id, self.plan.record_index), (14, 10))
        self.assertEqual(
            self.plan.stage,
            "after_spark_checkpoint_commit_before_next_event_publication",
        )

    def test_injects_only_after_checkpoint_commit_is_confirmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(
                self.plan, "f3-test", "P1", Path(tmp), wait_for_kill=lambda: None
            )
            with self.assertRaisesRegex(RuntimeError, "F3 wait returned"):
                injector.after_checkpoint_commit(
                    batch_id=14, record_index=10, recording_id="rec-150",
                    object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                    metadata_rows_committed=10, checkpoint_commit_confirmed=True,
                )
            marker = Path(tmp) / "f3-test.kill"
            event = dict(line.split("=", 1) for line in marker.read_text().splitlines())
            self.assertTrue(marker.read_text().startswith("target="))
            self.assertEqual(event["fault_point"], "F3")
            self.assertEqual(event["stage"], self.plan.stage)
            self.assertEqual(event["metadata_rows_committed"], "10")

    def test_rejects_f3_without_confirmed_checkpoint_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(self.plan, "f3-test", "P1", Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "without a confirmed"):
                injector.after_checkpoint_commit(
                    batch_id=14, record_index=10, recording_id="rec-150",
                    object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                    metadata_rows_committed=10, checkpoint_commit_confirmed=False,
                )
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_ignores_non_target_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(self.plan, "f3-test", "P1", Path(tmp))
            self.assertFalse(injector.after_checkpoint_commit(
                batch_id=13, record_index=10, recording_id="rec-140",
                object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                metadata_rows_committed=10, checkpoint_commit_confirmed=True,
            ))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
