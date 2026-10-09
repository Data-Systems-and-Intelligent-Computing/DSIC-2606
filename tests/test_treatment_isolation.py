import unittest
from pathlib import Path

import yaml

from src.checkpointing.treatment_config import resolve_checkpoint_location


ROOT = Path(__file__).resolve().parents[1]
TREATMENTS_PATH = ROOT / "configs" / "treatments.yaml"
CHECKPOINT_PATH = ROOT / "configs" / "checkpoint.yaml"


class TreatmentIsolationConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with TREATMENTS_PATH.open("r", encoding="utf-8-sig") as stream:
            cls.config = yaml.safe_load(stream)["treatments"]
        with CHECKPOINT_PATH.open("r", encoding="utf-8-sig") as stream:
            cls.checkpoint = yaml.safe_load(stream)["checkpoint"]

    def test_b0_and_b1_differ_only_by_checkpoint_location(self):
        common = self.config["common"]
        b0 = {**common, **self.config["B0"]}
        b1 = {**common, **self.config["B1"]}

        changed_keys = sorted(
            key for key in set(b0) | set(b1)
            if b0.get(key) != b1.get(key)
        )
        self.assertEqual(changed_keys, ["checkpoint_location"])
        self.assertIn("{ephemeral_root}", b0["checkpoint_location"])
        self.assertIn("{persistent_root}", b1["checkpoint_location"])

    def test_idempotence_is_off_for_both_treatments(self):
        self.assertNotIn("idempotence_enabled", self.config["common"])
        self.assertFalse(self.config["B0"]["idempotence_enabled"])
        self.assertFalse(self.config["B1"]["idempotence_enabled"])

    def test_b0_resolves_to_ephemeral_path(self):
        with self.assertRaises(ValueError):
            resolve_checkpoint_location(
                self.config["B0"]["checkpoint_location"],
                persistent_root=self.checkpoint["persistent_root"],
                ephemeral_root=None,
                run_id="pilot-001",
                treatment="B0",
            )

        self.assertEqual(
            resolve_checkpoint_location(
                self.config["B0"]["checkpoint_location"],
                persistent_root=self.checkpoint["persistent_root"],
                ephemeral_root=self.checkpoint["ephemeral_root"],
                run_id="pilot-001",
                treatment="B0",
            ),
            "/checkpoints/ephemeral/pilot-001/B0",
        )

    def test_b1_requires_a_persistent_root_and_resolves_per_run(self):
        template = self.config["B1"]["checkpoint_location"]

        with self.assertRaises(ValueError):
            resolve_checkpoint_location(
                template,
                persistent_root=None,
                ephemeral_root=self.checkpoint["ephemeral_root"],
                run_id="pilot-001",
                treatment="B1",
            )

        location = resolve_checkpoint_location(
            template,
            persistent_root=self.checkpoint["persistent_root"],
            ephemeral_root=self.checkpoint["ephemeral_root"],
            run_id="pilot-001",
            treatment="B1",
        )
        self.assertEqual(location, "/checkpoints/persistent/pilot-001/B1")

    def test_checkpoint_roots_match_instrument(self):
        self.assertEqual(self.checkpoint["persistent_root"], "/checkpoints/persistent")
        self.assertEqual(self.checkpoint["ephemeral_root"], "/checkpoints/ephemeral")


if __name__ == "__main__":
    unittest.main()
