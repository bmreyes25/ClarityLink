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


def test_a_candidate_that_edits_the_allowlist_is_flagged_for_the_reviewer(tmp_path):
    root = make_repo(tmp_path, {})
    git(root, "checkout", "-q", "-b", "feature")
    (root / ALLOW).write_text(json.dumps({"schema": 1, "vin_samples": [], "allow": []}, indent=1))
    git(root, "add", "-A"); git(root, "commit", "-q", "-m", "a")
    code, out = run(root, "--base", "main")
    assert code == 0 and "PUBLIC_SAFETY_NOTICE" in out


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
