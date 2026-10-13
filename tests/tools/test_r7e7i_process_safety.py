"""Host-only decision tests; these fixtures are not target evidence."""
import pytest

from tools.r7e7i_process_safety import decide


BASE = dict(path_state="PRESENT_REGULAR", identity_verified=True,
            proc_visibility="COMPLETE", exact_inode_references="NONE",
            relaunch_audit="NONE", historical_termination="ESTABLISHED")


def test_conditions_are_cumulative_for_conditional_safety():
    assert decide(**BASE) == "CONDITIONALLY_SAFE_FOR_SEPARATE_REVIEW"


@pytest.mark.parametrize("field,value,result", [
    ("historical_termination", "UNKNOWN", "BLOCKED_PRIOR_TERMINATION_UNKNOWN"),
    ("proc_visibility", "PARTIAL", "BLOCKED_PROCESS_VISIBILITY_INCOMPLETE"),
    ("proc_visibility", "EMPTY_PS_ONLY", "BLOCKED_PROCESS_VISIBILITY_INCOMPLETE"),
    ("exact_inode_references", "PRESENT", "BLOCKED_CURRENT_PROCESS_REFERENCE"),
    ("exact_inode_references", "UNKNOWN", "BLOCKED_CURRENT_PROCESS_REFERENCES_UNKNOWN"),
    ("relaunch_audit", "PRESENT", "BLOCKED_RELAUNCH_PATH_PRESENT"),
    ("relaunch_audit", "UNKNOWN", "BLOCKED_RELAUNCH_PATH_UNKNOWN"),
    ("identity_verified", False, "BLOCKED_PATH_IDENTITY_UNKNOWN"),
])
def test_each_missing_or_conflicting_fact_blocks_safety(field, value, result):
    facts = dict(BASE)
    facts[field] = value
    assert decide(**facts) == result


def test_historical_termination_does_not_imply_current_safety():
    facts = dict(BASE, proc_visibility="UNKNOWN", exact_inode_references="UNKNOWN",
                 relaunch_audit="UNKNOWN")
    assert decide(**facts) == "BLOCKED_PROCESS_VISIBILITY_INCOMPLETE"


def test_absent_path_does_not_establish_no_current_mapping_or_relaunch():
    facts = dict(BASE, path_state="ABSENT")
    assert decide(**facts) == "NO_PATHNAME_TO_REMOVE_CURRENT_SAFETY_UNRESOLVED"
