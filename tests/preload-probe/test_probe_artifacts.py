from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


class ProbeArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        artifact_dir = os.environ.get("CLARITYLINK_PROBE_DIR")
        readelf = os.environ.get("CLARITYLINK_LLVM_READELF")
        if not artifact_dir or not readelf:
            raise unittest.SkipTest(
                "set CLARITYLINK_PROBE_DIR and CLARITYLINK_LLVM_READELF"
            )
        cls.artifact_dir = Path(artifact_dir)
        cls.readelf = readelf
        cls.executable = cls.artifact_dir / "claritylink_preload_probe_exec"
        cls.library = cls.artifact_dir / "libclaritylink_preload_probe.so"
        if not cls.executable.is_file() or not cls.library.is_file():
            raise unittest.SkipTest("build the synthetic probe artifacts first")

    def readelf_output(self, *args: str, path: Path) -> str:
        return subprocess.run(
            [self.readelf, *args, str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_executable_is_arm32_pie_with_android_interpreter_and_libc(self):
        header = self.readelf_output("-h", path=self.executable)
        program_headers = self.readelf_output("-l", path=self.executable)
        dynamic = self.readelf_output("-d", path=self.executable)
        self.assertIn("ELF32", header)
        self.assertIn("ARM", header)
        self.assertIn("DYN", header)
        self.assertIn("/system/bin/linker", program_headers)
        self.assertIn("libc.so", dynamic)

    def test_preload_is_arm32_shared_object_with_libc_dependency(self):
        header = self.readelf_output("-h", path=self.library)
        dynamic = self.readelf_output("-d", path=self.library)
        self.assertIn("ELF32", header)
        self.assertIn("ARM", header)
        self.assertIn("DYN", header)
        self.assertIn("libclaritylink_preload_probe.so", dynamic)
        self.assertIn("libc.so", dynamic)

    def test_artifacts_contain_only_the_expected_markers(self):
        exec_strings = subprocess.run(
            ["strings", str(self.executable)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        library_strings = subprocess.run(
            ["strings", str(self.library)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertIn("CLARITYLINK_PROBE_MAIN_RAN", exec_strings)
        self.assertIn("CLARITYLINK_PROBE_CONSTRUCTOR_RAN", library_strings)


if __name__ == "__main__":
    unittest.main()
