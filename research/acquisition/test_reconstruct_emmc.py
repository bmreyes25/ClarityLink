import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from reconstruct_emmc import reconstruct


class ReconstructTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "emmc").mkdir()
        self.chunks = []
        hashes = []
        for i, value in enumerate((b"A", b"B")):
            name = f"emmc/mmcblk0.part{i:03d}"
            content = value * (1024 * 1024)
            (self.root / name).write_bytes(content)
            self.chunks.append({"name": name, "index": i, "skip_mib": i, "count_mib": 1, "expected_bytes": len(content)})
            hashes.append(f"{hashlib.sha256(content).hexdigest()}  {name}\n")
        (self.root / "SHA256SUMS").write_text("".join(hashes))
        (self.root / "ACQUISITION_MANIFEST.json").write_text(json.dumps({"chunks": self.chunks, "emmc_bytes": 2 * 1024 * 1024}))

    def test_reconstructs_verified_chunks_without_overwrite(self):
        output = self.root / "mmcblk0-full.img"
        size, digest = reconstruct(self.root, output)
        self.assertEqual(size, 2 * 1024 * 1024)
        self.assertEqual(output.read_bytes(), b"A" * (1024 * 1024) + b"B" * (1024 * 1024))
        self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            reconstruct(self.root, output)

    def test_rejects_gap_before_writing(self):
        self.chunks[1]["skip_mib"] = 2
        (self.root / "ACQUISITION_MANIFEST.json").write_text(json.dumps({"chunks": self.chunks, "emmc_bytes": 2 * 1024 * 1024}))
        with self.assertRaisesRegex(ValueError, "not contiguous"):
            reconstruct(self.root, self.root / "mmcblk0-full.img")
        self.assertFalse((self.root / "mmcblk0-full.img").exists())

    def test_rejects_changed_chunk(self):
        (self.root / "emmc/mmcblk0.part001").write_bytes(b"X" * (1024 * 1024))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            reconstruct(self.root, self.root / "mmcblk0-full.img")
        self.assertFalse((self.root / "mmcblk0-full.img").exists())


if __name__ == "__main__":
    unittest.main()
