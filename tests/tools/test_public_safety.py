"""Negative and positive tests for tools/check_public_safety.py.

Every unsafe fixture is assembled at run time inside a throwaway Git repository, so the
test source itself contains no key, token, VIN or account path for a scanner to find.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools/check_public_safety.py"
ALLOW = "docs/security/public-safety-allowlist.json"


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          check=True, capture_output=True, text=True).stdout


def make_repo(tmp_path, files, allow=None):
    git(tmp_path, "init", "-q", "-b", "main")
    base = {ALLOW: json.dumps(allow or {"schema": 1, "vin_samples": [], "allow": []})}
    base["README.md"] = "hello\n"
    for name, data in {**base, **files}.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "c")
    return tmp_path


def run(root, *args):
    p = subprocess.run([sys.executable, str(TOOL), "--root", str(root), *args], capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def rules(output):
    return {line.split()[0] for line in output.splitlines() if line.startswith("PS")}


def secret(): return "ghp_" + "A1b2C3d4E5" * 4
def vin(): return "1M8GDM9AX" + "KP042788"
def account_path(): return "/Users/" + "alice" + "/work/notes"


CASES = [
    ("firmware/boot.img", b"x", "PS001"),
    ("lib/native.so", b"x", "PS001"),
    ("notes/capture.pcap", b"x", "PS001"),
    ("keys/dev.pem", b"x", "PS001"),
    ("docs/readme.txt", b"\x7fELF" + b"\x01" * 40, "PS002"),
    ("docs/archive.txt", b"PK\x03\x04" + b"\x00" * 30, "PS002"),
    ("docs/blob.txt", b"abc\x00\x01\x02def", "PS002"),
    ("docs/big.md", b"a" * (1024 * 1024 + 1), "PS003"),
    ("docs/key.md", ("-----BEGIN " + "RSA PRIVATE KEY-----\n").encode(), "PS004"),
    ("docs/tok.md", ("token " + secret() + "\n").encode(), "PS004"),
    ("docs/vin.md", ("VIN " + vin() + "\n").encode(), "PS005"),
    ("docs/path.md", ("see " + account_path() + "\n").encode(), "PS006"),
    ("research/acquisition/new.md", b"plain text\n", "PS007"),
    ("research/captures/run/notes.md", b"plain text\n", "PS007"),
]


@pytest.mark.parametrize("name,data,rule", CASES, ids=[f"{c[2]}-{c[0]}" for c in CASES])
def test_unsafe_candidate_fails(tmp_path, name, data, rule):
    root = make_repo(tmp_path, {name: data})
    code, out = run(root, "--all")
    assert code == 1 and rule in rules(out), out
    assert "PUBLIC_SAFETY_FAIL" in out


def test_output_never_echoes_the_matched_value(tmp_path):
    root = make_repo(tmp_path, {"docs/a.md": f"{secret()} {vin()} {account_path()}\n"})
    code, out = run(root, "--all")
    assert code == 1
    for value in (secret(), vin(), "alice"):
        assert value not in out


def test_safe_text_binary_image_and_script_pass(tmp_path):
    files = {"docs/a.md": "plain notes about /Users/<name>/ and /home/runner/work\n",
             "tools/x.py": "print('ok')\n", "docs/fig.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
             "docs/fig.svg": "<svg/>\n"}
    code, out = run(make_repo(tmp_path, files), "--all")
    assert code == 0 and "PUBLIC_SAFETY_PASS" in out, out


def test_oversize_image_still_fails(tmp_path):
    code, out = run(make_repo(tmp_path, {"docs/f.png": b"\x89PNG" + b"\x00" * (1024 * 1024 + 8)}), "--all")
    assert code == 1 and "PS003" in rules(out)


def test_public_sample_vin_is_allowed_only_when_listed(tmp_path):
    files = {"tests/t.py": "raw = 'VIN 1HGCM82633A004352'\n"}
    unlisted, listed = tmp_path / "unlisted", tmp_path / "listed"
    unlisted.mkdir(); listed.mkdir()
    assert run(make_repo(unlisted, files), "--all")[0] == 1
    allow = {"schema": 1, "vin_samples": ["1HGCM82633A004352"], "allow": []}
    code, out = run(make_repo(listed, files, allow), "--all")
    assert code == 0, out


def candidate(root, files=None, allow=None, delete=(), symlinks=None):
    """Branch off main and commit a candidate; returns the repo. Everything is built at run time."""
    git(root, "checkout", "-q", "-b", "feature")
    if allow is not None:
        (root / ALLOW).write_text(json.dumps(allow))
    for name, data in (files or {}).items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else data.encode())
    for name in delete:
        (root / name).unlink()
    for name, target in (symlinks or {}).items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).symlink_to(target)
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "candidate")
    return root


def gate(root):
    return run(root, "--base", "main")


TRUSTED = {"schema": 1, "vin_samples": [], "allow": [
    {"path": "research/old/a.md", "rule": "PS006", "max": 1, "reason": "historical"}]}
BASE_FILES = {"research/old/a.md": "x " + account_path() + "\n"}


def trusted_repo(tmp_path, extra=None):
    return make_repo(tmp_path, {**BASE_FILES, **(extra or {})}, TRUSTED)


def test_an_unchanged_trusted_allowlist_still_exempts_the_documented_baseline(tmp_path):
    root = candidate(trusted_repo(tmp_path), {"docs/new.md": "fine\n"})
    code, out = gate(root)
    assert code == 0, out


def test_new_permissive_allowlist_entry_fails_closed(tmp_path):
    root = trusted_repo(tmp_path)
    widened = {**TRUSTED, "allow": TRUSTED["allow"] + [
        {"path": "docs/leak.md", "rule": "PS006", "max": 5, "reason": "please"}]}
    candidate(root, {"docs/leak.md": f"{account_path()}\n"}, widened)
    code, out = gate(root)
    assert code == 1 and {"PS009"} <= rules(out)


def test_raising_an_existing_exception_count_fails_closed(tmp_path):
    root = trusted_repo(tmp_path)
    raised = {**TRUSTED, "allow": [{**TRUSTED["allow"][0], "max": 9}]}
    candidate(root, {"research/old/a.md": f"{account_path()}\n" * 3}, raised)
    code, out = gate(root)
    assert code == 1 and "PS009" in rules(out) and "PS006" in rules(out)   # the content is also judged by the trusted ceiling


def test_broadening_a_path_wildcard_fails_closed(tmp_path):
    root = trusted_repo(tmp_path)
    broad = {**TRUSTED, "allow": [{**TRUSTED["allow"][0], "path": "research/*"}]}
    candidate(root, {"research/new/b.md": f"{account_path()}\n"}, broad)
    code, out = gate(root)
    assert code == 1 and "PS009" in rules(out) and "PS006" in rules(out)


def test_an_exception_for_a_restricted_binary_fails_closed(tmp_path):
    root = trusted_repo(tmp_path)
    allow = {**TRUSTED, "allow": TRUSTED["allow"] + [
        {"path": "firmware/boot.img", "rule": "PS001", "max": 1, "reason": "needed"}]}
    candidate(root, {"firmware/boot.img": b"x"}, allow)
    code, out = gate(root)
    assert code == 1 and {"PS009", "PS001"} <= rules(out)


def test_altering_the_exempted_sample_list_fails_closed(tmp_path):
    root = trusted_repo(tmp_path)
    allow = {**TRUSTED, "vin_samples": [vin()]}
    candidate(root, {"docs/v.md": f"VIN {vin()}\n"}, allow)
    code, out = gate(root)
    assert code == 1 and {"PS009", "PS005"} <= rules(out)
    assert vin() not in out                                     # the value is never echoed


def test_removing_or_lowering_exceptions_is_permitted(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, {"research/old/a.md": "clean\n"}, {"schema": 1, "vin_samples": [], "allow": []})
    code, out = gate(root)
    assert code == 0, out


def test_a_secret_hidden_in_the_allowlist_file_is_still_found(tmp_path):
    root = trusted_repo(tmp_path)
    allow = {**TRUSTED, "allow": [{**TRUSTED["allow"][0], "reason": secret()}]}
    candidate(root, {}, allow)
    code, out = gate(root)
    assert code == 1 and "PS004" in rules(out) and ALLOW in out


@pytest.mark.parametrize("control", ["tools/check_public_safety.py", ".github/workflows/public-safety.yml"])
def test_modifying_the_gate_itself_requires_owner_approval(tmp_path, control):
    root = trusted_repo(tmp_path, {control: "original\n"})
    candidate(root, {control: "weakened\n"})
    code, out = gate(root)
    assert code == 1 and "PS008" in rules(out) and control in out


def test_deleting_the_gate_is_also_flagged(tmp_path):
    control = "tools/check_public_safety.py"
    root = trusted_repo(tmp_path, {control: "original\n"})
    candidate(root, delete=[control])
    code, out = gate(root)
    assert code == 1 and "PS008" in rules(out)


def test_invalid_candidate_allowlist_cannot_be_used_even_with_a_valid_baseline(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, allow={"schema": 1, "allow": [{"path": "a", "rule": "PS006", "max": 1}]})
    code, out = gate(root)
    assert code == 2 and "invalid allowlist" in out


def test_a_candidate_without_an_allowlist_gets_no_exemptions_but_is_not_an_error(tmp_path):
    # a branch cut before the trusted allowlist existed (or one that deletes it) grants nothing itself
    root = trusted_repo(tmp_path)
    candidate(root, {"docs/new.md": "fine\n"}, delete=[ALLOW])
    code, out = gate(root)
    assert code == 0 and "no allowlist file" in out, out


def test_deleting_the_allowlist_does_not_hide_a_violation_or_widen_anything(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, {"docs/leak.md": f"{account_path()}\n"}, delete=[ALLOW])
    code, out = gate(root)
    assert code == 1 and "PS006" in rules(out)          # judged by the trusted allowlist, which exempts only one other path


def test_without_any_allowlist_at_all_the_gate_still_refuses(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.md").write_text("x\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-q", "-m", "c")
    assert run(tmp_path, "--all")[0] == 2
    candidate(tmp_path, {"b.md": "y\n"})
    assert gate(tmp_path)[0] == 2


def test_an_allowlist_that_is_not_json_is_an_error(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, {"docs/x.md": "fine\n"})
    (root / ALLOW).write_text("{not json")
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "broken")
    assert gate(root)[0] == 2


def test_an_unresolvable_trusted_ref_is_an_error(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, {"docs/x.md": "fine\n"})
    code, out = run(root, "--base", "main", "--trusted-ref", "no-such-ref")
    assert code == 2 and "PUBLIC_SAFETY_ERROR" in out


def test_a_missing_trusted_allowlist_refuses_unless_bootstrap_is_explicit(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "README.md").write_text("x\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-q", "-m", "base")
    candidate(tmp_path, {ALLOW: json.dumps({"schema": 1, "vin_samples": [], "allow": []})})
    code, out = gate(tmp_path)
    assert code == 2 and "no allowlist" in out
    code, out = run(tmp_path, "--base", "main", "--allow-bootstrap")
    assert code == 0 and "PUBLIC_SAFETY_BOOTSTRAP_UNTRUSTED" in out and "trust=bootstrap-untrusted" in out


def test_bootstrap_still_judges_content_and_cannot_be_reused_once_a_baseline_exists(tmp_path):
    root = trusted_repo(tmp_path)
    widened = {**TRUSTED, "allow": TRUSTED["allow"] + [
        {"path": "docs/leak.md", "rule": "PS006", "max": 5, "reason": "x"}]}
    candidate(root, {"docs/leak.md": f"{account_path()}\n"}, widened)
    code, out = run(root, "--base", "main", "--allow-bootstrap")   # the flag changes nothing when a baseline exists
    assert code == 1 and "PS009" in rules(out)


def test_symlink_outside_the_repository_fails(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, symlinks={"docs/link": "../../../outside", "docs/abs": "/etc/passwd"})
    code, out = gate(root)
    assert code == 1 and "PS010" in rules(out) and "docs/link" in out and "docs/abs" in out


def test_symlink_inside_the_repository_is_accepted(tmp_path):
    root = trusted_repo(tmp_path, {"docs/real.md": "ok\n"})
    candidate(root, symlinks={"docs/alias": "real.md"})
    code, out = gate(root)
    assert code == 0, out


def test_gitlink_is_not_inspectable_and_fails(tmp_path):
    root = trusted_repo(tmp_path)
    git(root, "checkout", "-q", "-b", "feature")
    git(root, "update-index", "--add", "--cacheinfo", "160000," + "a" * 40 + ",vendor/sub")
    git(root, "commit", "-q", "-m", "gitlink")
    code, out = gate(root)
    assert code == 1 and "PS010" in rules(out) and "vendor/sub" in out


def test_a_git_read_failure_is_an_error_not_a_pass(tmp_path):
    root = trusted_repo(tmp_path)
    candidate(root, {"docs/x.md": "fine\n"})
    code, out = run(root, "--base", "does-not-exist")
    assert code == 2


def test_staged_mode_compares_against_the_committed_allowlist(tmp_path):
    root = trusted_repo(tmp_path)
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/leak.md").write_text(f"{account_path()}\n")
    (root / ALLOW).write_text(json.dumps({**TRUSTED, "allow": TRUSTED["allow"] + [
        {"path": "docs/leak.md", "rule": "PS006", "max": 5, "reason": "x"}]}))
    git(root, "add", "docs/leak.md", ALLOW)
    code, out = run(root, "--staged", "--trusted-ref", "HEAD")
    assert code == 1 and "PS009" in rules(out)


def test_allowance_is_a_ceiling_per_path_and_rule(tmp_path):
    allow = {"schema": 1, "vin_samples": [], "allow": [
        {"path": "research/old/*.md", "rule": "PS006", "max": 1, "reason": "historical"}]}
    one = {"research/old/a.md": f"x {account_path()}\n"}
    (tmp_path / "ok").mkdir()
    assert run(make_repo(tmp_path / "ok", one, allow), "--all")[0] == 0
    (tmp_path / "more").mkdir()
    two = {"research/old/a.md": f"x {account_path()}\ny {account_path()}\n"}
    code, out = run(make_repo(tmp_path / "more", two, allow), "--all")
    assert code == 1 and "PS006" in rules(out)
    (tmp_path / "elsewhere").mkdir()
    code, out = run(make_repo(tmp_path / "elsewhere", {"docs/other.md": f"x {account_path()}\n"}, allow), "--all")
    assert code == 1 and "PS006" in rules(out)


def test_an_allowlisted_file_does_not_hide_a_different_rule(tmp_path):
    allow = {"schema": 1, "vin_samples": [], "allow": [
        {"path": "research/old/a.md", "rule": "PS006", "max": 5, "reason": "historical"}]}
    root = make_repo(tmp_path, {"research/old/a.md": f"{account_path()}\n{secret()}\n"}, allow)
    code, out = run(root, "--all")
    assert code == 1 and rules(out) == {"PS004"}


@pytest.mark.parametrize("bad", [
    {"schema": 2, "allow": []},
    {"schema": 1, "allow": [{"path": "a", "rule": "PS006", "max": 1}]},
    {"schema": 1, "allow": [{"path": "a", "rule": "PS006", "max": 1, "reason": "  "}]},
    {"schema": 1, "allow": [{"path": "a", "rule": "PS999", "max": 1, "reason": "x"}]},
    {"schema": 1, "allow": [{"path": "a", "rule": "PS006", "max": -1, "reason": "x"}]},
])
def test_invalid_allowlist_is_a_configuration_error(tmp_path, bad):
    code, out = run(make_repo(tmp_path, {}, bad), "--all")
    assert code == 2 and "invalid allowlist" in out


def test_missing_allowlist_is_a_configuration_error(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.md").write_text("x\n")
    git(tmp_path, "add", "-A"); git(tmp_path, "commit", "-q", "-m", "c")
    assert run(tmp_path, "--all")[0] == 2


def test_base_mode_checks_only_files_changed_since_the_merge_base(tmp_path):
    root = make_repo(tmp_path, {"docs/old.md": f"{account_path()}\n"})   # unsafe, but already on main
    git(root, "checkout", "-q", "-b", "feature")
    (root / "docs/new.md").write_text("fine\n")
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "n")
    assert run(root, "--base", "main")[0] == 0
    (root / "docs/bad.apk").write_bytes(b"x")
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "b")
    code, out = run(root, "--base", "main")
    assert code == 1 and "docs/bad.apk" in out and "old.md" not in out


def test_staged_mode_checks_the_index_not_the_working_tree(tmp_path):
    root = make_repo(tmp_path, {})
    (root / "docs/a.md").parent.mkdir(exist_ok=True)
    (root / "docs/a.md").write_text(f"{secret()}\n")
    git(root, "add", "docs/a.md")
    (root / "docs/a.md").write_text("clean now\n")        # unstaged edit must not hide the staged content
    code, out = run(root, "--staged")
    assert code == 1 and "PS004" in rules(out)


def test_untracked_and_ignored_local_files_are_never_scanned(tmp_path):
    root = make_repo(tmp_path, {".gitignore": "*.img\n"})
    (root / "boot.img").write_bytes(b"\x7fELF")
    (root / "scratch.txt").write_text(f"{secret()}\n")
    code, out = run(root, "--all")
    assert code == 0, out


def test_the_checked_out_repository_head_passes_its_own_gate():
    has_allowlist = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", "HEAD:" + ALLOW],
                                   capture_output=True).returncode == 0
    if not has_allowlist:   # the very commit that introduces the allowlist cannot read it from HEAD yet
        pytest.skip("allowlist not yet committed at HEAD")
    code, out = run(REPO, "--all", "--head", "HEAD")
    assert code == 0, out


WORKFLOW = (REPO / ".github/workflows/public-safety.yml").read_text()


def test_protected_workflow_never_runs_or_checks_out_candidate_code():
    assert "pull_request_target" in WORKFLOW
    # the only checkout is the protected base commit; the candidate is fetched as objects, never checked out
    assert WORKFLOW.count("actions/checkout") == 1
    assert "ref: ${{ github.event.pull_request.base.sha }}" in WORKFLOW
    checkout_block = WORKFLOW.split("actions/checkout@")[1].split("- name:")[0]
    assert "head" not in checkout_block
    for forbidden in ("pip install", "npm ", "setup-python", "setup-node", "make ", "./tools/", "bash tools/",
                      "secrets.", "pull_request.head.ref", "head.repo", "github.head_ref", "workflow_run"):
        assert forbidden not in WORKFLOW, forbidden
    assert "git checkout" not in WORKFLOW and "git switch" not in WORKFLOW


def test_protected_workflow_has_read_only_permissions_and_no_inline_expression_injection():
    assert "permissions:\n  contents: read\n" in WORKFLOW
    for write in ("contents: write", "pull-requests: write", "id-token", "actions: write", "checks: write"):
        assert write not in WORKFLOW
    # untrusted-looking values reach shell commands only through env variables
    run_lines = [l for l in WORKFLOW.splitlines() if l.strip().startswith("run:")]
    assert run_lines and not any("${{" in l for l in run_lines)


def test_protected_workflow_uses_the_base_commit_as_the_trusted_ref():
    assert '--trusted-ref "$BASE_SHA"' in WORKFLOW and '--base "$BASE_SHA"' in WORKFLOW
    assert "refs/candidate/head" in WORKFLOW


def test_ci_gate_step_is_labelled_supplementary():
    ci = (REPO / ".github/workflows/ci.yml").read_text()
    assert "supplementary" in ci and "public-safety.yml" in ci
