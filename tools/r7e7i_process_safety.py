"""Pure decision model for exact-path process safety; performs no inspection."""
from __future__ import annotations


def decide(*, path_state: str, identity_verified: bool,
           proc_visibility: str, exact_inode_references: str,
           relaunch_audit: str, historical_termination: str) -> str:
    """Classify evidence without treating process absence as a termination proof.

    Values are deliberately closed strings so an incomplete observation cannot
    accidentally become a negative finding.
    """
    if path_state == "ABSENT":
        return "NO_PATHNAME_TO_REMOVE_CURRENT_SAFETY_UNRESOLVED"
    if path_state != "PRESENT_REGULAR" or not identity_verified:
        return "BLOCKED_PATH_IDENTITY_UNKNOWN"
    if historical_termination != "ESTABLISHED":
        return "BLOCKED_PRIOR_TERMINATION_UNKNOWN"
    if proc_visibility != "COMPLETE":
        return "BLOCKED_PROCESS_VISIBILITY_INCOMPLETE"
    if exact_inode_references == "PRESENT":
        return "BLOCKED_CURRENT_PROCESS_REFERENCE"
    if exact_inode_references != "NONE":
        return "BLOCKED_CURRENT_PROCESS_REFERENCES_UNKNOWN"
    if relaunch_audit == "PRESENT":
        return "BLOCKED_RELAUNCH_PATH_PRESENT"
    if relaunch_audit != "NONE":
        return "BLOCKED_RELAUNCH_PATH_UNKNOWN"
    return "CONDITIONALLY_SAFE_FOR_SEPARATE_REVIEW"
