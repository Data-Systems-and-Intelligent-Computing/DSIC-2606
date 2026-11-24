from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from src.fault_injection.fault_plan import load_fault_plan
from src.fault_injection.injector import DriverKillInjector


ROOT = Path(__file__).resolve().parents[1]


class F2FaultTests(unittest.TestCase):
    def setUp(self):
        self.plan = load_fault_plan(
            ROOT / "fault_plans/F2_after_metadata_before_checkpoint.yaml", "F2"
        )

    def test_plan_freezes_full_target_batch_before_checkpoint(self):
        self.assertEqual((self.plan.batch_id, self.plan.record_index), (14, 10))
        self.assertEqual(self.plan.stage, "after_metadata_commit_before_checkpoint_commit")

    def test_injects_after_all_batch_metadata_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(
                self.plan, "f2-test", "B1", Path(tmp), wait_for_kill=lambda: None
            )
            with self.assertRaisesRegex(RuntimeError, "F2 wait returned"):
                injector.after_metadata_commit(
                    batch_id=14, record_index=10, recording_id="rec-150",
                    object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                    metadata_rows_committed=10,
                )
            marker = Path(tmp) / "f2-test.kill"
            event = dict(line.split("=", 1) for line in marker.read_text().splitlines())
            self.assertTrue(marker.read_text().startswith("target="))
            self.assertEqual(event["fault_point"], "F2")
            self.assertEqual(event["stage"], self.plan.stage)
            self.assertEqual(event["metadata_rows_committed"], "10")

    def test_rejects_f2_before_all_metadata_rows_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(self.plan, "f2-test", "B0", Path(tmp))
            with self.assertRaisesRegex(RuntimeError, "all ten"):
                injector.after_metadata_commit(
                    batch_id=14, record_index=10, recording_id="rec-150",
                    object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                    metadata_rows_committed=9,
                )
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_ignores_non_target_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            injector = DriverKillInjector(self.plan, "f2-test", "B0", Path(tmp))
            self.assertFalse(injector.after_metadata_commit(
                batch_id=13, record_index=10, recording_id="rec-140",
                object_uri="s3://audiomoth/a.wav", object_key="a.wav",
                metadata_rows_committed=10,
            ))
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
