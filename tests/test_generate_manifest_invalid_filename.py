import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_manifest.py"


class GenerateManifestInvalidFilenameTests(unittest.TestCase):
    def test_nama_timestamp_invalid_ditolak_tanpa_membuat_manifest(self):
        with tempfile.TemporaryDirectory(prefix="manifest-invalid-name-") as temp:
            root = Path(temp)
            source = root / "raw"
            source.mkdir()
            (source / "bukan_timestamp.WAV").write_bytes(b"test")
            output = root / "manifest.csv"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--input", str(source),
                    "--corpus-root", str(root),
                    "--device_id", "TEST_DEVICE",
                    "--output", str(output),
                    "--source-timezone", "Asia/Jakarta",
                    "--selection", "all",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("format timestamp", result.stderr)
            self.assertFalse(output.exists(), "Manifest tidak boleh dibuat saat validasi gagal")


if __name__ == "__main__":
    unittest.main()
