"""CL-IMP-12 artifact packaging checks independent of a local SDK build."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "package_cl_imp_12_artifacts.py")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from package_cl_imp_12_artifacts import (  # noqa: E402
    digest, manifest_permissions, require_regular_output,
)


def test_api17_manifests_have_no_permissions_and_candidate_stays_disabled():
    lab, lab_permissions, lab_disabled = manifest_permissions(
        ROOT / "android/cl-imp-03-app/AndroidManifest.lab.xml")
    candidate, candidate_permissions, candidate_disabled = manifest_permissions(
        ROOT / "android/cl-imp-03-app/AndroidManifest.candidate.xml")

    assert lab == "org.claritylink.independentdisplay.lab"
    assert candidate == "org.claritylink.independentdisplay.candidate"
    assert lab_permissions == candidate_permissions == []
    assert lab_disabled is False
    assert candidate_disabled is True


def test_sha256_streaming_matches_known_fixture(tmp_path):
    sample = tmp_path / "artifact.bin"
    sample.write_bytes(b"ClarityLink CL-IMP-12")
    assert digest(sample) == "d8cd643f55ebca704336b41093b27fd4ec49bed216d7a3674075fb7703848384"


def test_build_script_uses_pinned_api17_armv7_pipeline():
    script = (ROOT / "tools/build_cl_imp_12_artifacts.sh").read_text(encoding="utf-8")
    assert "23.2.8568313" in script
    assert "build_r7c_android_api17_armv7.sh" in script
    assert "audit_r7c_api17_symbols.py" in script
    assert "compile_android_api17_java.sh" in script
    assert "build_cl_imp_03_apks.sh" in script


def test_package_refuses_symlink_destination(tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"preserve")
    destination = tmp_path / "artifact.bin"
    destination.symlink_to(outside)

    try:
        require_regular_output(destination)
    except ValueError as error:
        assert "symbolic-link" in str(error)
    else:
        raise AssertionError("symlink output unexpectedly accepted")
    assert outside.read_bytes() == b"preserve"
