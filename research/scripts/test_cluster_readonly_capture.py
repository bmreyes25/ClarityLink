import pathlib
import unittest

from cluster_readonly_capture import normalize_png, phase_commands, output_dir, process_inventory_commands


class CapturePlanTest(unittest.TestCase):
    def test_snapshot_plan_is_read_only(self):
        commands = phase_commands("maps")
        self.assertIn(["shell", "screencap", "-d", "1", "-p"], commands)
        joined = " ".join(" ".join(command) for command in commands)
        for forbidden in ("remount", "push", "install", "logcat -c", "setprop", "am broadcast", "dd "):
            self.assertNotIn(forbidden, joined)

    def test_png_normalizes_old_adb_pty_line_endings(self):
        raw = b"\x89PNG\r\r\n\x1a\r\n" + b"IHDR\r\n"
        self.assertEqual(normalize_png(raw), b"\x89PNG\r\n\x1a\nIHDR\n")

    def test_output_must_stay_in_analysis_capture_folder(self):
        root = pathlib.Path(__file__).resolve().parent.parent / "captures"
        self.assertEqual(output_dir(root / "focused-test"), (root / "focused-test").resolve())
        with self.assertRaises(ValueError):
            output_dir(pathlib.Path("/tmp/outside"))

    def test_process_inventory_targets_only_jmcs_and_reads_proc(self):
        sample = "root      22893 1     29980  12540 ffffffff 00000000 S /system/bin/jmcs\n"
        commands = process_inventory_commands(sample)
        self.assertEqual(commands, [["shell", "cat", "/proc/22893/status"],
                                    ["shell", "cat", "/proc/22893/maps"],
                                    ["shell", "ls", "-l", "/proc/22893/fd"]])
        self.assertEqual(process_inventory_commands("root 1 0 S /init\n"), [])

    def test_process_inventory_plan_never_requests_root_or_changes_state(self):
        commands = phase_commands("process-inventory")
        self.assertEqual(commands, [["shell", "ps"], ["shell", "cat", "/proc/net/unix"],
                                    ["shell", "cat", "/proc/net/tcp"]])

    def test_capability_survey_checks_existing_kernel_facilities_only(self):
        commands = phase_commands("capability-survey")
        self.assertIn(["shell", "cat", "/proc/config.gz"], commands)
        self.assertIn(["shell", "ls", "-ld", "/sys/kernel/debug/usb/usbmon"], commands)
        self.assertIn(["shell", "cat", "/proc/mounts"], commands)
        flattened = " ".join(" ".join(command) for command in commands)
        for forbidden in ("su", "mount", "insmod", "setprop", "push", "install"):
            self.assertNotIn(" " + forbidden + " ", " " + flattened + " ")

    def test_digital_twin_survey_reads_display_activity_and_audio(self):
        commands = phase_commands("twin-survey")
        self.assertIn(["shell", "dumpsys", "SurfaceFlinger"], commands)
        self.assertIn(["shell", "dumpsys", "activity", "services"], commands)
        self.assertIn(["shell", "dumpsys", "audio"], commands)
        self.assertIn(["shell", "dumpsys", "media.audio_flinger"], commands)
        self.assertIn(["shell", "screencap", "-d", "1", "-p"], commands)
        self.assertFalse(any(command[1] in ("am", "pm", "setprop") for command in commands))


if __name__ == "__main__":
    unittest.main()
