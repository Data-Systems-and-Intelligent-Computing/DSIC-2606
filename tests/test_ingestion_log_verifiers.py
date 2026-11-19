import json
import tempfile
import unittest
from pathlib import Path

from scripts.compare_effective_configs import verify_configs
from scripts.verify_replay_batch_logs import read_expected_batches, verify_log

ROOT = Path(__file__).resolve().parents[1]


class IngestionLogVerifierTests(unittest.TestCase):
    def test_effective_configs_must_differ_only_at_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = {
                "idempotence_enabled": False,
                "max_files_per_trigger": 1,
                "batch_size": 10,
            }
            b0 = {**common, "checkpoint_location": "/checkpoints/ephemeral/r/B0"}
            b1 = {**common, "checkpoint_location": "/checkpoints/persistent/r/B1"}
            left = root / "b0.log"
            right = root / "b1.log"
            left.write_text("EFFECTIVE_CONFIG " + json.dumps(b0), encoding="utf-8")
            right.write_text("EFFECTIVE_CONFIG " + json.dumps(b1), encoding="utf-8")
            self.assertEqual(verify_configs(left, right), ["checkpoint_location"])

    def test_replay_log_must_match_frozen_batches(self):
        expected = read_expected_batches(ROOT / "data/batches/batch_order_main.csv")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.log"
            lines = [
                f"REPLAY_BATCH_COMPLETED batch_id={batch_id} recording_ids={json.dumps(ids)}"
                for batch_id, ids in enumerate(expected)
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            verify_log(path, expected)

    def test_replay_log_rejects_wrong_batch_membership(self):
        expected = read_expected_batches(ROOT / "data/batches/batch_order_main.csv")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.log"
            batches = [list(ids) for ids in expected]
            batches[4][0] = "WRONG-ID"
            lines = [
                f"REPLAY_BATCH_COMPLETED batch_id={batch_id} recording_ids={json.dumps(ids)}"
                for batch_id, ids in enumerate(batches)
            ]
            path.write_text("\n".join(lines), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                verify_log(path, expected)


if __name__ == "__main__":
    unittest.main()
