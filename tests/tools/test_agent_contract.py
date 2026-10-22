"""The agent operating contract stays single-sourced and complete."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENTS = (REPO / "AGENTS.md").read_text()
CLAUDE = (REPO / "CLAUDE.md").read_text()
TEMPLATE = (REPO / "docs/development/agent-task-prompt-template.md").read_text()


def test_agents_md_governs_claude_and_codex_alike():
    assert "Claude Code or Codex" in AGENTS
    assert "every Codex campaign" not in AGENTS
    for must in ("safeForHonda()", "tools/publish_checkpoint.sh", "tools/verify_remote_publication.py",
                 "--stack-parent-pr", "@ECC", "check_public_safety.py", "force-push"):
        assert must in AGENTS, must


def test_claude_md_is_a_short_pointer_not_a_second_rulebook():
    assert "AGENTS.md" in CLAUDE and len(CLAUDE.splitlines()) <= 20
    assert not re.search(r"^#+ .*Autonomous Milestone", CLAUDE, re.M)


def test_template_requires_every_item_the_contract_names():
    for must in ("Dedicated worktree", "publish_checkpoint.sh", "--stack-parent-pr", "verify_remote_publication.py",
                 "@ECC", "safeForHonda() == false", "public-safety", "fabricated approval", "unpublished commits"):
        assert must.lower() in TEMPLATE.lower() or must in TEMPLATE, must


def test_linked_documents_exist():
    for text, base in ((CLAUDE, REPO), (TEMPLATE, REPO / "docs/development"), (AGENTS, REPO)):
        for target in re.findall(r"\]\(([^)#]+)\)", text):
            if target.startswith("http"):
                continue
            assert (base / target).resolve().exists(), target
