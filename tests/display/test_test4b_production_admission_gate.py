"""Source-contract guards for the fail-closed API17 host path."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
POLICY = (ROOT / "android/src/main/java/org/claritylink/android/DisplayPolicy.java").read_text()
HOST = (ROOT / "android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java").read_text()


def method_body(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1:index]
    raise AssertionError("method body is not balanced")


def test_honda_safety_policy_is_literal_fail_closed():
    body = method_body(POLICY, "public boolean safeForHonda()")
    assert re.search(r"return\s+false\s*;", body)
    assert "Build.VERSION.SDK_INT == 17" in POLICY
    assert 'fingerprint.startsWith("generic")' in POLICY
    assert 'hardware.contains("goldfish") || hardware.contains("ranchu")' in POLICY


def test_public_host_path_cannot_select_the_lab_bypass():
    body = method_body(HOST, "public boolean show(Context context")
    assert "showInternal(context, display, generation, warningPolicy, layout, false)" in body
    lab = method_body(HOST, "boolean showOfflineLabForRuntimeTest(")
    assert "isIsolatedApi17EmulatorBuild()" in lab
    assert "layout.testOnly" in lab
    assert "getIntent()" not in lab and "System.getenv" not in lab
    internal = method_body(HOST, "private boolean showInternal(")
    assert "else if (!warningPolicy.safeForHonda() || layout.testOnly)" in internal


def test_local_dismissal_is_not_reported_as_verified_removal():
    close = method_body(HOST, "public void close()")
    assert "finally" in close
    assert "state(DisplayPolicy.Admission.WINDOW_REMOVED_VERIFIED)" not in close
    assert "DISMISS_REQUESTED" in close
