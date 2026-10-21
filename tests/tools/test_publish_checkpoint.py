import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

publisher = load("publisher", "tools/publish_checkpoint.py")
verifier = load("verifier", "tools/verify_remote_publication.py")

class PublishScopeTests(unittest.TestCase):
    def test_detached_head_branch_preserves_uncommitted_work(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Synthetic Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            (root / "note.md").write_text("base\n")
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
            subprocess.run(["git", "-C", str(root), "checkout", "--detach", "-q"], check=True)
            (root / "note.md").write_text("preserved work\n")
            sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            self.assertEqual(publisher.ensure_branch(root, "feature/resume-synthetic"), "feature/resume-synthetic")
            self.assertEqual(subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(), sha)
            self.assertEqual((root / "note.md").read_text(), "preserved work\n")

    def test_unrelated_pre_staged_file_blocks_publication(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "scope.md").write_text("scoped\n")
            (root / "unrelated.md").write_text("unrelated\n")
            subprocess.run(["git", "-C", str(root), "add", "unrelated.md"], check=True)
            with self.assertRaises(publisher.Failure):
                publisher.reject_staged_outside_scope(root, ["scope.md"])

    def test_explicit_tracked_deletion_is_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Synthetic Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            (root / "note.md").write_text("base\n")
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
            (root / "note.md").unlink()
            self.assertEqual(publisher.safe_scope(root, ["note.md"]), ["note.md"])
            subprocess.run(["git", "-C", str(root), "add", "--", "note.md"], check=True)
            publisher.scan_staged(root)

    def test_detached_main_branch_is_rejected_without_moving_head(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Synthetic Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            (root / "note.md").write_text("base\n")
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
            subprocess.run(["git", "-C", str(root), "checkout", "--detach", "-q"], check=True)
            sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            with self.assertRaises(publisher.Failure):
                publisher.ensure_branch(root, "main")
            self.assertEqual(subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(), sha)

    def test_empty_scope_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(Path(d), [])

    def test_pathspec_patterns_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "note.md").write_text("text")
            for value in ("*.md", ":(glob)**"):
                with self.assertRaises(publisher.Failure):
                    publisher.safe_scope(root, [value])

    def test_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(Path(d), ["../secret.md"])

    def test_directories_and_binary_artifacts_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "sub").mkdir()
            (root / "build.apk").write_bytes(b"synthetic")
            (root / "evidence").mkdir()
            (root / "evidence" / "note.md").write_text("restricted evidence")
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(root, ["sub"])
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(root, ["build.apk"])
            with self.assertRaises(publisher.UnsafeContent):
                publisher.safe_scope(root, ["evidence/note.md"])

    def test_explicit_text_file_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "note.md").write_text("synthetic public note\n")
            self.assertEqual(publisher.safe_scope(root, ["note.md"]), ["note.md"])

    def test_staged_binary_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "synthetic.md").write_bytes(b"text\x00binary")
            subprocess.run(["git", "-C", str(root), "add", "synthetic.md"], check=True)
            with self.assertRaises(publisher.UnsafeContent):
                publisher.scan_staged(root)

    def test_staged_token_pattern_is_rejected(self):
        # Exercise the scanner against a temporary index, never repository credentials.
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "note.md").write_text("synthetic token=ghp_" + "A" * 30 + "\n")
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            with self.assertRaises(publisher.Failure):
                publisher.scan_staged(root)

class VerifyResultTests(unittest.TestCase):
    def setUp(self):
        self.root = Path("/synthetic/repo")
        self.remote_code = 0
        self.remote_out = "abc123\trefs/heads/feature/synthetic\n"
        self.remote_err = ""
        self.status_output = ""
        self.upstream_output = "origin/feature/synthetic"
        self.ancestor_result = 0

    def git_result(self, root, *args, **kwargs):
        values = {
            ("rev-parse", "--show-toplevel"): (0, str(self.root)),
            ("rev-parse", "--git-dir"): (0, ".git"),
            ("remote", "get-url", "origin"): (0, "https://github.com/bmreyes25/ClarityLink.git"),
            ("branch", "--show-current"): (0, "feature/synthetic"),
            ("rev-parse", "HEAD"): (0, "abc123"),
            ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): (0, self.upstream_output),
            ("status", "--porcelain"): (0, self.status_output),
        }
        if args and args[0] == "ls-remote":
            return subprocess.CompletedProcess(args, self.remote_code, self.remote_out, self.remote_err)
        if args and args[0] == "merge-base":
            return subprocess.CompletedProcess(args, self.ancestor_result, "", "not ancestor")
        if args and args[0] == "rev-list":
            return subprocess.CompletedProcess(args, 0, "2", "")
        code, out = values.get(tuple(args), (0, ""))
        return subprocess.CompletedProcess(args, code, out + ("\n" if out else ""), "")

    def test_remote_sha_match_is_required(self):
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "REMOTE_VERIFIED")

    def test_missing_remote_branch_is_not_verified(self):
        self.remote_out = ""
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "NO_REMOTE_BRANCH")

    def test_network_failure_is_not_verified(self):
        self.remote_code, self.remote_err = 128, "fatal: unable to access: network unreachable"
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "NO_REMOTE_BRANCH")

    def test_authentication_failure_is_distinguished(self):
        self.remote_code, self.remote_err = 128, "fatal: Authentication failed"
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "AUTHENTICATION_FAILURE")

    def test_remote_moved_concurrently_is_a_sha_mismatch(self):
        self.remote_out = "def456\trefs/heads/feature/synthetic\n"
        self.ancestor_result = 1
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "REMOTE_SHA_MISMATCH")

    def test_local_changes_remain_pending_even_with_matching_remote(self):
        self.status_output = " M notes.md"
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "LOCAL_CHANGES_PENDING")

    def test_missing_upstream_is_not_a_verified_checkpoint(self):
        self.upstream_output = ""
        with patch.object(verifier, "git", side_effect=self.git_result):
            self.assertEqual(verifier.run(self.root)["result"], "NO_REMOTE_BRANCH")

    def test_unpushed_commit_is_detected_even_with_stale_tracking_metadata(self):
        self.remote_out = "def456\trefs/heads/feature/synthetic\n"
        self.ancestor_result = 0
        with patch.object(verifier, "git", side_effect=self.git_result):
            result = verifier.run(self.root)
            self.assertEqual(result["result"], "UNPUSHED_COMMITS")
            self.assertEqual(result["unpushed_commit_count"], 2)

if __name__ == "__main__":
    unittest.main()
