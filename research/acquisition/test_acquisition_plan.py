from __future__ import annotations

import datetime as dt
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import build_acquisition_plan as plan


def fixture(folder: Path, *, free_kib: int = 100_000_000, sectors: int = 14_745_600) -> None:
    values = {
        "proc-mounts": "/dev/block/vold/8:1 /mnt/usbdrive1 vfat rw 0 0\n",
        "backup-dir": "drwx------ 1 root root 4096 CLARITY_BACKUP_20260918_0225\n",
        "root-startup-list": "".join(f"-r--r--r-- {path.rsplit('/', 1)[-1]}\n" for path in plan.ROOT_STARTUP_PATHS),
        "usb-root": "CLARITY_BACKUP_20260918_0225\nWirebug.apk\n",
        "busybox-applets": "\n".join(sorted(plan.REQUIRED_APPLETS)) + "\n",
        "emmc-sectors": f"{sectors}\n",
        "usb-sda-sectors": "242040832\n",
        "usb-serial": "TESTUSB1234\n",
        "emmc-logical-block": "512\n",
        "proc-mtd": 'mtd0: 00200000 00020000 "USP"\nmtd7: 04000000 00020000 "whole_device"\n',
        "boot0-sectors": "8192\n",
        "usb-df": f"Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/vold/8:1 121019392 1000 {free_kib} 1% /mnt/usbdrive1\n",
        "filesystem-du": "524288 /system\n2097152 /data\n131072 /mnt/data1\n131072 /mnt/data2\n1048576 /mnt/media\n",
    }
    commands = {}
    for name, value in values.items():
        (folder / f"{name}.stdout.txt").write_text(value)
        commands[name] = {"exit": 0}
    for name in ("readable-mmcblk0", "readable-mmcblk0boot0", "readable-mtdblock0", "readable-mtdblock7"):
        commands[name] = {"exit": 0}
    (folder / "manifest.json").write_text(json.dumps({
        "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "serial": "test-device",
        "commands": commands,
    }))


class AcquisitionPlanTests(unittest.TestCase):
    def test_historical_size_has_seven_gib_chunks_and_one_32mib_chunk(self) -> None:
        chunks = plan.chunks(7_549_747_200)
        self.assertEqual(len(chunks), 8)
        self.assertEqual([x["expected_bytes"] for x in chunks[:7]], [2**30] * 7)
        self.assertEqual(chunks[-1]["expected_bytes"], 32 * 2**20)
        self.assertEqual(sum(x["expected_bytes"] for x in chunks), 7_549_747_200)
        self.assertTrue(all(x["expected_bytes"] < 4 * 2**30 for x in chunks))

    def test_generated_shell_has_only_allowlisted_device_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            result = plan.build(folder, "20260925_120000")
            self.assertEqual(result["emmc_bytes"], 7_549_747_200)
            self.assertEqual(len(result["chunks"]), 8)
            self.assertEqual(len(result["mtd"]), 2)
            self.assertEqual(len(result["boot_read_only_candidates"]), 1)
            self.assertEqual(result["usb_identity"], {"mode": "sysfs-serial", "value": "TESTUSB1234"})
            shell = plan.render_script(result)
            self.assertNotIn("@BLOCK_COPY_COMMANDS@", shell)
            self.assertNotIn("of=/dev/block", shell)
            self.assertNotIn("force_ro=", shell)
            self.assertIn("CLARITY_FORENSIC_", shell)
            parsed = subprocess.run(["sh", "-n"], input=shell, text=True, capture_output=True)
            self.assertEqual(parsed.returncode, 0, parsed.stderr)

    def test_low_space_aborts_before_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder, free_kib=1_000_000)
            with self.assertRaisesRegex(ValueError, "USB free"):
                plan.build(folder, "20260925_120000")

    def test_incomplete_inventory_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            manifest = json.loads((folder / "manifest.json").read_text())
            manifest["commands"]["emmc-sectors"]["exit"] = 1
            (folder / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "emmc-sectors"):
                plan.build(folder, "20260925_120000")

    def test_unreadable_mtd_is_explicitly_omitted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            manifest = json.loads((folder / "manifest.json").read_text())
            manifest["commands"]["readable-mtdblock7"]["exit"] = 1
            (folder / "manifest.json").write_text(json.dumps(manifest))
            result = plan.build(folder, "20260925_120000")
            self.assertEqual([x["index"] for x in result["mtd"]], [0])
            self.assertEqual([x["index"] for x in result["mtd_unavailable"]], [7])

    def test_existing_usb_sibling_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            (folder / "usb-root.stdout.txt").write_text("CLARITY_FORENSIC_20260925_120000\n")
            with self.assertRaisesRegex(ValueError, "already exists"):
                plan.build(folder, "20260925_120000")

    def test_missing_startup_path_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            (folder / "root-startup-list.stdout.txt").write_text("-r--r--r-- /init.rc\n")
            with self.assertRaisesRegex(ValueError, "root-startup paths missing"):
                plan.build(folder, "20260925_120000")

    def test_existing_root_inventory_requires_root_and_selects_protected_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fixture(folder)
            manifest = json.loads((folder / "manifest.json").read_text())
            manifest["root_verified"] = True
            for name in ("readable-root-mmcblk0", "readable-root-mtdblock0", "readable-root-mtdblock7"):
                manifest["commands"][name] = {"exit": 0}
            manifest["commands"]["filesystem-du-root"] = {"exit": 0}
            (folder / "filesystem-du-root.stdout.txt").write_text((folder / "filesystem-du.stdout.txt").read_text())
            (folder / "manifest.json").write_text(json.dumps(manifest))
            result = plan.build(folder, "20260925_120000")
            self.assertTrue(result["requires_existing_root"])
            self.assertEqual([x["index"] for x in result["mtd"]], [0, 7])
            shell = plan.render_script(result)
            self.assertIn("generated acquisition requires existing root read access", shell)
            self.assertIn("base64 -d", shell)


if __name__ == "__main__":
    unittest.main()
