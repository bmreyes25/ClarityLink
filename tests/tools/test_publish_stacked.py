"""Stacked-publication rules for tools/publish_checkpoint.py (real Git, local bare origin)."""
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("publisher_s", ROOT / "tools/publish_checkpoint.py")
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def sh(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture
def world(tmp_path):
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
    (work / "a.md").write_text("a\n")
    sh(work, "add", "-A"); sh(work, "commit", "-qm", "base"); sh(work, "push", "-q", "origin", "HEAD:refs/heads/main")
    sh(work, "checkout", "-q", "-b", "parent")
    shas = []
    for name in ("p1.md", "p2.md"):
        (work / name).write_text(name + "\n")
        sh(work, "add", "-A"); sh(work, "commit", "-qm", name); shas.append(sh(work, "rev-parse", "HEAD"))
    sh(work, "push", "-q", "origin", "parent")
    sh(work, "fetch", "-q", "origin")
    info = {"number": 81, "state": "OPEN", "baseRefName": "main", "headRefName": "parent", "headRefOid": shas[-1],
            "isCrossRepository": False, "mergeStateStatus": "CLEAN", "commit_oids": shas}
    return work, origin, info


def check(work, info, branch="child", **over):
    info = {**info, **over}
    sh(work, "checkout", "-q", "-B", branch, info["headRefOid"] if "headRefOid" not in over else over["headRefOid"])
    return pub.ensure_no_unpublished_history(work, branch, info)


def test_valid_stack_returns_the_verified_parent_head(world):
    work, _, info = world
    assert check(work, info) == info["headRefOid"]


@pytest.mark.parametrize("override,fragment", [
    ({"state": "MERGED"}, "not OPEN"),
    ({"state": "CLOSED"}, "not OPEN"),
    ({"isCrossRepository": True}, "fork"),
    ({"baseRefName": "other"}, "one level"),
    ({"mergeStateStatus": "DIRTY"}, "conflicts"),
])
def test_unsuitable_parent_is_refused(world, override, fragment):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    with pytest.raises(pub.Failure, match=fragment):
        pub.ensure_no_unpublished_history(work, "child", {**info, **override})


def test_parent_branch_that_moved_after_the_pr_was_read_is_refused(world):
    work, _, info = world
    sh(work, "checkout", "-q", "parent")
    (work / "late.md").write_text("late\n")
    sh(work, "add", "-A"); sh(work, "commit", "-qm", "late"); sh(work, "push", "-q", "origin", "parent")
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    with pytest.raises(pub.Failure, match="live SHA"):
        pub.ensure_no_unpublished_history(work, "child", info)


def test_parent_commits_not_shown_by_the_pr_are_refused(world):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    with pytest.raises(pub.Failure, match="not reviewed there"):
        pub.ensure_no_unpublished_history(work, "child", {**info, "commit_oids": info["commit_oids"][1:]})


def test_extra_local_history_on_the_new_branch_is_refused(world):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    (work / "x.md").write_text("x\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "unreviewed")
    with pytest.raises(pub.Failure, match="exactly at the parent PR head"):
        pub.ensure_no_unpublished_history(work, "child", info)


def test_parent_that_does_not_descend_from_current_main_is_refused(world):
    work, _, info = world
    sh(work, "checkout", "-q", "main")
    (work / "m.md").write_text("m\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "main moved")
    sh(work, "push", "-q", "origin", "main")
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    with pytest.raises(pub.Failure, match="descend"):
        pub.ensure_no_unpublished_history(work, "child", info)


def test_without_a_declared_parent_history_is_still_blocked(world):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    with pytest.raises(pub.Failure, match="--stack-parent-pr"):
        pub.ensure_no_unpublished_history(work, "child")


def test_a_branch_at_main_needs_no_parent(world):
    work, _, _ = world
    sh(work, "checkout", "-q", "-B", "fresh", "origin/main")
    assert pub.ensure_no_unpublished_history(work, "fresh") is None


def test_resuming_an_existing_stacked_branch_rechecks_the_parent(world):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    (work / "c.md").write_text("c\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "child 1")
    sh(work, "push", "-q", "origin", "child")
    assert pub.ensure_no_unpublished_history(work, "child", info) == info["headRefOid"]
    sh(work, "checkout", "-q", "parent")
    (work / "late.md").write_text("late\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "late")
    sh(work, "push", "-q", "origin", "parent"); sh(work, "checkout", "-q", "child")
    with pytest.raises(pub.Failure, match="parent branch moved"):
        pub.ensure_no_unpublished_history(work, "child", info)


def test_an_unsynchronized_stacked_branch_is_refused(world):
    work, _, info = world
    sh(work, "checkout", "-q", "-B", "child", info["headRefOid"])
    (work / "c.md").write_text("c\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "child 1")
    sh(work, "push", "-q", "origin", "child")
    (work / "d.md").write_text("d\n"); sh(work, "add", "-A"); sh(work, "commit", "-qm", "unpublished")
    with pytest.raises(pub.Failure, match="unpublished commits"):
        pub.ensure_no_unpublished_history(work, "child", info)


def test_the_publisher_never_force_pushes():
    text = (ROOT / "tools/publish_checkpoint.py").read_text()
    assert "--force" not in text and "+refs" not in text and "reset --hard" not in text


def test_pr_titles_are_one_short_line_and_details_go_to_the_body():
    title, details = pub.split_pr_message("fix(x): short title\n\nLong explanation\nmore\n\nCo-Authored-By: x")
    assert title == "fix(x): short title" and "Long explanation" in details and "\n" not in title
    assert len(pub.split_pr_message("a" * 300)[0]) == 100
    assert pub.split_pr_message("   \n\nbody only")[0] == "body only"
    with pytest.raises(pub.Failure):
        pub.split_pr_message("  \n \n")


def test_the_public_safety_gate_blocks_staged_unsafe_content(tmp_path):
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    for rel in ("tools/check_public_safety.py",):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, tmp_path / rel)
    allow = tmp_path / "docs/security/public-safety-allowlist.json"
    allow.parent.mkdir(parents=True)
    allow.write_text('{"schema": 1, "vin_samples": [], "allow": []}')
    (tmp_path / "notes.md").write_text("see /Users/" + "alice" + "/work\n")
    sh(tmp_path, "add", "-A")
    with pytest.raises(pub.UnsafeContent, match="public-safety gate failed"):
        pub.run_public_safety_gate(tmp_path)
    sh(tmp_path, "rm", "-q", "--cached", "notes.md")
    pub.run_public_safety_gate(tmp_path)   # clean index passes
