"""Tests for tools/verify_apk_dex_classes.py using synthetic dexdump text and a generated zip.

No real APK and no Android SDK are needed: the APK is a zip built at run time and the dexdump text
is written to match the tool's documented format, so this exercises parsing and verdict logic only.
The real dexdump run happens in the CL-R12 workflow.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools/verify_apk_dex_classes.py"

DUMP = """Processing 'x.apk'...
Opened 'x.apk', DEX version '035'
Class #0            -
  Class descriptor  : 'Lorg/claritylink/renderer/PaneLease;'
  Access flags      : 0x0011 (PUBLIC FINAL)
  Direct methods    -
    #0              : (in Lorg/claritylink/renderer/PaneLease;)
      name          : '<init>'
  Virtual methods   -
    #0              : (in Lorg/claritylink/renderer/PaneLease;)
      name          : 'revoke'
Class #1            -
  Class descriptor  : 'Lorg/claritylink/android/SyntheticFrameFill;'
  Direct methods    -
    #0              : (in Lorg/claritylink/android/SyntheticFrameFill;)
      name          : 'fill'
"""


def make(tmp_path, dex=True):
    apk = tmp_path / "t.apk"
    with zipfile.ZipFile(apk, "w") as z:
        z.writestr("AndroidManifest.xml", "m")
        if dex:
            z.writestr("classes.dex", b"dex\n035\x00" + b"x" * 20)
    out = tmp_path / "dump.txt"
    out.write_text(DUMP)
    return apk, out


def run(apk, dump, *extra):
    p = subprocess.run([sys.executable, "-I", str(TOOL), "--apk", str(apk), "--label", "lab",
                        "--dexdump-output", str(dump), *extra], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def test_required_classes_and_methods_pass_and_the_report_records_hashes(tmp_path):
    apk, dump = make(tmp_path)
    code, out = run(apk, dump, "--require", "org.claritylink.renderer.PaneLease",
                    "--require", "org.claritylink.android.SyntheticFrameFill",
                    "--require-method", "org.claritylink.android.SyntheticFrameFill#fill",
                    "--source-commit", "abc")
    assert code == 0, out
    assert "DEX_VERIFICATION_RESULT label=lab PASS" in out and "source_commit=abc" in out
    assert "apk_sha256=" in out and "classes.dex sha256=" in out


def test_a_missing_class_fails(tmp_path):
    apk, dump = make(tmp_path)
    code, out = run(apk, dump, "--require", "org.claritylink.renderer.PaneEvent")
    assert code == 1 and "DEX_CLASS_MISSING" in out and "RESULT label=lab FAIL" in out


def test_a_missing_method_fails(tmp_path):
    apk, dump = make(tmp_path)
    code, out = run(apk, dump, "--require-method", "org.claritylink.android.SyntheticFrameFill#fillNothing")
    assert code == 1 and "DEX_METHOD_MISSING" in out


def test_a_forbidden_class_that_is_present_fails_and_an_absent_one_passes(tmp_path):
    apk, dump = make(tmp_path)
    assert run(apk, dump, "--forbid", "org.claritylink.renderer.PaneEvent")[0] == 0
    code, out = run(apk, dump, "--forbid", "org.claritylink.renderer.PaneLease")
    assert code == 1 and "UNEXPECTEDLY_PRESENT" in out


def test_source_names_alone_do_not_count_a_class_that_is_only_a_substring_is_not_present(tmp_path):
    apk, dump = make(tmp_path)
    code, _ = run(apk, dump, "--require", "org.claritylink.renderer.Pane")
    assert code == 1


@pytest.mark.parametrize("problem", ["no-dex", "empty-dump", "not-a-zip"])
def test_inputs_the_tool_cannot_trust_are_errors_not_passes(tmp_path, problem):
    apk, dump = make(tmp_path, dex=(problem != "no-dex"))
    if problem == "empty-dump":
        dump.write_text("nothing useful here\n")
    if problem == "not-a-zip":
        apk.write_bytes(b"this is not a zip")
    code, out = run(apk, dump, "--require", "org.claritylink.renderer.PaneLease")
    assert code == 2 and "DEX_VERIFICATION_ERROR" in out


def test_without_a_dexdump_source_it_is_an_error(tmp_path):
    apk, _ = make(tmp_path)
    p = subprocess.run([sys.executable, "-I", str(TOOL), "--apk", str(apk), "--label", "x"], capture_output=True, text=True)
    assert p.returncode == 2
