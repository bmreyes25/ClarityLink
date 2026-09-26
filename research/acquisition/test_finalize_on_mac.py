from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from finalize_on_mac import ARCHIVES, finalize, sha256
from runtime_snapshot import STATES


class FinalizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.usb = self.root / "usb"
        self.usb.mkdir()
        (self.usb / "CLARITY_BACKUP_20260918_0225").mkdir()
        self.folder = self.usb / "CLARITY_FORENSIC_20260925_120000"
        self.folder.mkdir()
        self.runtime = self.root / "runtime-source"
        self.runtime.mkdir()
        (self.folder / "runtime").mkdir()
        self.manifest = self.root / "ACQUISITION_MANIFEST.json"
        self.manifest.write_text(json.dumps({
            "run_id": "20260925_120000", "serial": "test-device",
            "chunks": [{"name": "emmc/mmcblk0.part000", "expected_bytes": 4}],
            "mtd": [], "boot_read_only_candidates": [],
        }))
        (self.folder / "ACQUISITION_MANIFEST.json").write_bytes(self.manifest.read_bytes())
        hashed = ["ACQUISITION_MANIFEST.json", "emmc/mmcblk0.part000", *sorted(ARCHIVES)]
        for relative in hashed:
            path = self.folder / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative != "ACQUISITION_MANIFEST.json":
                path.write_bytes(b"data")
        (self.folder / "SHA256SUMS").write_text("".join(
            f"{sha256(self.folder / relative)}  {relative}\n" for relative in hashed
        ))
        for name in ("README.txt", "device-map.txt", "acquisition.log", "STORAGE_DONE.txt"):
            (self.folder / name).write_text(name)
        stamp = dt.datetime.now(dt.timezone.utc).isoformat()
        required_commands = {name: {"exit": 0, "stdout_bytes_saved": 3} for name in (
            "ps", "services", "packages", "getprop", "display", "window", "surfaceflinger", "activity"
        )}
        for state in STATES:
            state_dir = self.runtime / state
            state_dir.mkdir()
            (state_dir / "manifest.json").write_text(json.dumps({
                "state": state, "serial": "test-device", "utc": stamp,
                "commands": required_commands,
            }))
            (state_dir / "ps.stdout.txt").write_text("PID")

    def test_finalizes_and_hashes_sidecars_and_runtime(self) -> None:
        (self.folder / "metadata").mkdir()
        (self.folder / "metadata" / "dmesg.errors.txt").write_text("unavailable")
        (self.folder / "SHA256SUMS.original").write_text("preserved prior journal")
        (self.folder / "acquisition.log.original").write_text("preserved prior log")
        result = finalize(self.usb, self.folder, self.manifest, self.runtime)
        self.assertEqual(result["runtime_states"], len(STATES))
        self.assertTrue((self.folder / "FINISHED.txt").exists())
        sums = (self.folder / "SHA256SUMS").read_text()
        self.assertIn("metadata/dmesg.errors.txt", sums)
        self.assertIn(f"runtime/{STATES[0]}/manifest.json", sums)
        self.assertIn("acquisition.log", sums)
        self.assertIn("SHA256SUMS.original", sums)
        self.assertIn("acquisition.log.original", sums)

    def test_bad_source_hash_aborts_before_copy(self) -> None:
        (self.folder / "emmc/mmcblk0.part000").write_bytes(b"evil")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)
        self.assertFalse((self.folder / "FINISHED.txt").exists())

    def test_missing_runtime_state_aborts(self) -> None:
        missing = self.runtime / STATES[-1]
        for child in missing.iterdir():
            child.unlink()
        missing.rmdir()
        with self.assertRaisesRegex(ValueError, "missing or unexpected state"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)

    def test_runtime_serial_mismatch_aborts(self) -> None:
        path = self.runtime / STATES[0] / "manifest.json"
        payload = json.loads(path.read_text())
        payload["serial"] = "different"
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "state/serial mismatch"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)

    def test_stale_reviewed_manifest_aborts(self) -> None:
        self.manifest.write_text(self.manifest.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "does not match"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)

    def test_failed_decisive_display_capture_aborts(self) -> None:
        path = self.runtime / STATES[0] / "manifest.json"
        payload = json.loads(path.read_text())
        payload["commands"]["display"]["exit"] = 1
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "decisive capture failed"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)

    def test_runtime_state_symlink_aborts(self) -> None:
        linked = self.runtime / STATES[0]
        external = self.root / "outside"
        linked.rename(external)
        linked.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            finalize(self.usb, self.folder, self.manifest, self.runtime)


if __name__ == "__main__":
    unittest.main()
