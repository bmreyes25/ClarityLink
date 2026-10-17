"""Collection gate for tests whose implementation is intentionally local-only."""
from pathlib import Path

import pytest


LOCAL_ONLY_TEST_TOOLS = {
    "test_r7e5a_a0w_collector.py": ("r7e5a_a0w_collector.py",),
    "test_cl_imp_12_packaging_contract.py": ("package_cl_imp_12_artifacts.py",),
    "test_r7e7i_phase_s.py": ("r7e7i_clock_attestation.py",),
    "test_r7e7i_phase_c_cleanup.py": ("r7e7i_phase_c_cleanup.py", "r7e6_test_a_collector.py"),
    "test_test3_remote_query.py": ("test3_remote_query.py",),
    "test_r7e6_test_a_collector.py": ("r7e6_test_a_collector.py",),
    "test_r7e7i_current_process_evidence.py": ("r7e7i_current_process_evidence.py",),
    "test_r7e7i_historical_chronology.py": ("r7e7i_historical_chronology.py",),
    "test_r7e7i_boot_witness.py": ("r7e7i_boot_witness.py",),
    "test_r7e7i_host_time_evidence.py": ("r7e7i_host_time_evidence.py",),
    "test_r7e7g_rehearsal.py": ("r7e6_test_a_collector.py",),
    "test_r7e6_api17_timeout_instrumentation.py": ("run_r7e6_api17_runtime.py",),
    "test_r7e7i_clock_attestation.py": ("r7e7i_clock_attestation.py",),
    "test_r7e7i_process_safety.py": ("r7e7i_process_safety.py",),
}


def require_local_tools(test_file: str, *tool_names: str) -> None:
    """Skip only the fixed, documented set of tests needing ignored local tools."""
    test_name = Path(test_file).name
    expected = LOCAL_ONLY_TEST_TOOLS.get(test_name)
    if expected is None or tuple(tool_names) != expected:
        pytest.fail(f"unregistered local-only test gate: {test_name}")
    root = Path(test_file).resolve().parents[2]
    missing = [name for name in tool_names if not (root / "tools" / name).is_file()]
    if missing:
        pytest.skip(
            "requires local-only tool(s) omitted from this public candidate: " + ", ".join(missing),
            allow_module_level=True,
        )
