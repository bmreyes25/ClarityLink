"""The documentation entrypoint, historical-log banners, CODEOWNERS and PR template stay coherent."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_status_readme_links_resolve_and_holds_no_volatile_numbers():
    text = (REPO / "docs/status/README.md").read_text()
    for target in re.findall(r"\]\(([^)#]+)\)", text):
        if not target.startswith("http"):
            assert (REPO / "docs/status" / target).resolve().exists(), target
    assert not re.search(r"\b\d{1,3}\s?%", text), "no completion percentage belongs in the status map"
    for word in ("Merged and verified", "Synthetic lab PASS", "API17 runtime PASS",
                 "Honda receiver NO-GO", "Honda display NO-GO", "NOT AUTHORIZED"):
        assert word in text


def test_historical_logs_point_to_the_status_map():
    for name in ("PROJECT_STATE.md", "ROADMAP.md", "NEXT_ACTION.md", "EVIDENCE_INDEX.md"):
        head = (REPO / name).read_text()[:400]
        assert "Historical log." in head and "docs/status/README.md" in head, name


# Paths introduced by PR #83 (public-safety gate) and PR #84 (agent contract). They are listed now so the
# gate and the agent contract are owned from the commit that merges them; they are the only paths allowed
# to be absent, and the allowance ends when both PRs are on main (then this set can be emptied).
PENDING_PATHS = {"/tools/check_public_safety.py", "/CLAUDE.md"}


def test_codeowners_names_only_a_real_account_and_existing_paths():
    lines = [l for l in (REPO / ".github/CODEOWNERS").read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert lines
    for line in lines:
        pattern, *owners = line.split()
        assert owners == ["@bmreyes25"], line
        if pattern != "*" and pattern not in PENDING_PATHS:
            assert (REPO / pattern.lstrip("/")).exists(), pattern
    assert PENDING_PATHS <= {l.split()[0] for l in lines}


def test_pr_template_asks_for_the_evidence_that_matters():
    t = (REPO / ".github/pull_request_template.md").read_text()
    for must in ("Exact tested state", "verified remote SHA", "check_public_safety.py", "Independent review",
                 "stale run is not evidence", "Vehicle interaction", "Privacy review"):
        assert must in t, must
