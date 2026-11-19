import json
import tempfile
import unittest
from pathlib import Path

from src.ingestion.source_replay import ReplayFeeder


class ReplayFeederTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.landing_root = self.root / "landing"
        self.source.mkdir()
        self._write_events(3)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_events(self, count):
        for batch_id in range(count):
            event = {
                "batch_id": batch_id,
                "recording_ids": [f"REC-{batch_id:03d}-{index:02d}" for index in range(10)],
            }
            path = self.source / f"event-{batch_id:03d}.json"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    def _feeder(self):
        return ReplayFeeder(
            landing_root=self.landing_root,
            run_id="unit-test-run",
            event_source=self.source,
        )

    def test_publishes_only_the_next_event_after_completion(self):
        feeder = self._feeder()

        first = feeder.publish_initial()
        self.assertEqual(first.batch_id, 0)
        self.assertEqual(sorted(path.name for path in feeder.landing.glob("*.json")), [
            "event-000.json",
        ])

        second = feeder.after_batch_completed(0)
        self.assertEqual(second.batch_id, 1)
        self.assertIsNone(feeder.after_batch_completed(0))

        third = feeder.after_batch_completed(1)
        self.assertEqual(third.batch_id, 2)
        self.assertIsNone(feeder.after_batch_completed(2))

    def test_restart_preserves_published_events_and_waits_for_latest(self):
        feeder = self._feeder()
        feeder.publish_initial()
        feeder.after_batch_completed(0)

        restarted = self._feeder()
        last_existing = restarted.publish_initial()
        self.assertEqual(last_existing.batch_id, 1)
        self.assertIsNone(restarted.after_batch_completed(0))
        next_event = restarted.after_batch_completed(1)
        self.assertEqual(next_event.batch_id, 2)
        self.assertEqual(
            sorted(path.name for path in restarted.landing.glob("*.json")),
            ["event-000.json", "event-001.json", "event-002.json"],
        )

    def test_rejects_a_gap_in_source_event_numbers(self):
        (self.source / "event-001.json").unlink()
        with self.assertRaisesRegex(ValueError, "contiguous"):
            self._feeder().publish_initial()

    def test_rejects_event_with_wrong_id_count(self):
        bad_event = {
            "batch_id": 0,
            "recording_ids": ["ONLY-ONE"],
        }
        (self.source / "event-000.json").write_text(
            json.dumps(bad_event), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "10 unique recording_ids"):
            self._feeder().publish_initial()


if __name__ == "__main__":
    unittest.main()
