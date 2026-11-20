"""Keep unsupported exactly-once claims out of code, manuscript, and results."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAIM_SURFACES = (ROOT / "src", ROOT / "paper", ROOT / "results")
FORBIDDEN_CLAIM = re.compile(r"\bexactly[\s-]+once\b", re.IGNORECASE)


class ClaimLanguageTests(unittest.TestCase):
    def test_unsupported_exactly_once_claim_is_absent_from_claim_surfaces(self):
        violations = []

        for surface in CLAIM_SURFACES:
            if not surface.exists():
                continue
            for path in surface.rglob("*"):
                if not path.is_file():
                    continue
                content = path.read_bytes()
                if b"\0" in content:
                    continue
                try:
                    text = content.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if FORBIDDEN_CLAIM.search(line):
                        relative_path = path.relative_to(ROOT)
                        violations.append(f"{relative_path}:{line_number}: {line.strip()}")

        self.assertEqual(
            violations,
            [],
            "Unsupported exactly-once wording found:\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
