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

    def test_unpublished_history_on_existing_branch_is_rejected(self):
        root = Path("/synthetic/repo")
        with patch.object(publisher, "git", side_effect=["", "def456"]), \
             patch.object(publisher, "live_remote_branch_sha", return_value="abc123"):
            with self.assertRaisesRegex(publisher.Failure, "unpublished commits"):
                publisher.ensure_no_unpublished_history(root, "feature/synthetic")

    def test_new_branch_must_start_at_fetched_origin_main(self):
        root = Path("/synthetic/repo")
        with patch.object(publisher, "git", side_effect=["", "def456", "abc123"]), \
             patch.object(publisher, "live_remote_branch_sha", return_value=""):
            with self.assertRaisesRegex(publisher.Failure, "origin/main"):
                publisher.ensure_no_unpublished_history(root, "feature/synthetic")

    def test_new_branch_at_origin_main_has_no_unpublished_history(self):
        root = Path("/synthetic/repo")
        with patch.object(publisher, "git", side_effect=["", "abc123", "abc123"]), \
             patch.object(publisher, "live_remote_branch_sha", return_value=""):
            publisher.ensure_no_unpublished_history(root, "feature/synthetic")

    def test_live_remote_lookup_failure_fails_closed(self):
        root = Path("/synthetic/repo")
        failed = subprocess.CompletedProcess([], 128, "", "fatal: Authentication failed")
        with patch.object(publisher.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(publisher.Failure, "refusing publication"):
                publisher.live_remote_branch_sha(root, "feature/synthetic")

    def test_publish_runs_history_preflight_before_any_publication(self):
        root = Path("/synthetic/repo")
        args = publisher.argparse.Namespace(
            repo=root, task="synthetic", branch="feature/synthetic", file=["note.md"],
            message="docs: smoke", verification="VERIFIED", verify_command="true",
            wip_notes=None, pr=None, public_safe_reviewed=True, maintenance_owner=False,
        )
        with patch.object(publisher, "git", side_effect=[str(root), publisher.REMOTE]), \
             patch.object(publisher, "ensure_branch", return_value="feature/synthetic"), \
             patch.object(publisher, "ensure_no_unpublished_history", side_effect=publisher.Failure("unsafe history")) as preflight:
            with self.assertRaisesRegex(publisher.Failure, "unsafe history"):
                publisher.publish(args)
            preflight.assert_called_once_with(root.resolve(), "feature/synthetic")

    def test_pr_checkpoint_retries_stale_head_after_push(self):
        import json
        expected = {"headRefName": "feature/synthetic", "headRefOid": "abc123",
                    "baseRefName": "main", "state": "OPEN", "url": "https://github.com/bmreyes25/ClarityLink/pull/7"}
        stale = {**expected, "headRefOid": "previous-sha"}
        responses = [
            subprocess.CompletedProcess([], 0, json.dumps(stale), ""),
            subprocess.CompletedProcess([], 0, json.dumps(expected), ""),
        ]
        with patch.object(publisher.subprocess, "run", side_effect=responses), \
             patch.object(publisher.time, "sleep") as sleep:
            actual = publisher.verify_pr_checkpoint(["gh", "pr", "view", "7"], "feature/synthetic", "abc123", label="test PR")
        self.assertEqual(actual, expected)
        sleep.assert_called_once_with(1)

    def test_pr_checkpoint_stops_after_bounded_stale_head_reads(self):
        import json
        stale = {"headRefName": "feature/synthetic", "headRefOid": "previous-sha",
                 "baseRefName": "main", "state": "OPEN", "url": "https://github.com/bmreyes25/ClarityLink/pull/7"}
        response = subprocess.CompletedProcess([], 0, json.dumps(stale), "")
        with patch.object(publisher.subprocess, "run", return_value=response) as run, \
             patch.object(publisher.time, "sleep") as sleep:
            with self.assertRaisesRegex(publisher.Failure, "after 5 reads"):
                publisher.verify_pr_checkpoint(["gh", "pr", "view", "7"], "feature/synthetic", "abc123", label="test PR")
        self.assertEqual(run.call_count, 5)
        self.assertEqual(sleep.call_count, 4)

    def test_pr_checkpoint_retries_cli_timeout(self):
        import json
        expected = {"headRefName": "feature/synthetic", "headRefOid": "abc123",
                    "baseRefName": "main", "state": "OPEN", "url": "https://github.com/bmreyes25/ClarityLink/pull/7"}
        response = subprocess.CompletedProcess([], 0, json.dumps(expected), "")
        timeout = subprocess.TimeoutExpired(["gh", "pr", "view", "7"], 10)
        with patch.object(publisher.subprocess, "run", side_effect=[timeout, response]) as run, \
             patch.object(publisher.time, "sleep") as sleep:
            actual = publisher.verify_pr_checkpoint(["gh", "pr", "view", "7"], "feature/synthetic", "abc123", label="test PR")
        self.assertEqual(actual, expected)
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 10)
        sleep.assert_called_once_with(1)

    def test_pr_checkpoint_retries_malformed_and_non_object_responses(self):
        import json
        expected = {"headRefName": "feature/synthetic", "headRefOid": "abc123",
                    "baseRefName": "main", "state": "OPEN", "url": "https://github.com/bmreyes25/ClarityLink/pull/7"}
        responses = [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess([], 0, "[]", ""),
            subprocess.CompletedProcess([], 0, json.dumps(expected), ""),
        ]
        with patch.object(publisher.subprocess, "run", side_effect=responses), \
             patch.object(publisher.time, "sleep") as sleep:
            actual = publisher.verify_pr_checkpoint(["gh", "pr", "view", "7"], "feature/synthetic", "abc123", label="test PR")
        self.assertEqual(actual, expected)
        self.assertEqual(sleep.call_count, 2)

    def test_pr_checkpoint_rejects_missing_or_null_url_after_bounded_reads(self):
        import json
        valid = {"headRefName": "feature/synthetic", "headRefOid": "abc123",
                 "baseRefName": "main", "state": "OPEN", "url": "https://github.com/bmreyes25/ClarityLink/pull/7"}
        malformed = [
            {key: value for key, value in valid.items() if key != "url"},
            {**valid, "url": None},
            {**valid, "url": "https://example.invalid/pull/7"},
        ]
        for payload in malformed:
            response = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
            with self.subTest(payload=payload), \
                 patch.object(publisher.subprocess, "run", return_value=response) as run, \
                 patch.object(publisher.time, "sleep") as sleep:
                with self.assertRaisesRegex(publisher.Failure, "after 5 reads"):
                    publisher.verify_pr_checkpoint(["gh", "pr", "view", "7"], "feature/synthetic", "abc123", label="test PR")
            self.assertEqual(run.call_count, 5)
            self.assertEqual(sleep.call_count, 4)

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
            (root / "research" / "vehicle").mkdir(parents=True)
            (root / "research" / "vehicle" / "note.md").write_text("restricted vehicle research")
            (root / "research" / "honda").mkdir(parents=True)
            (root / "research" / "honda" / "note.md").write_text("restricted Honda research")
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(root, ["sub"])
            with self.assertRaises(publisher.Failure):
                publisher.safe_scope(root, ["build.apk"])
            with self.assertRaises(publisher.UnsafeContent):
                publisher.safe_scope(root, ["evidence/note.md"])
            for value in ("research/vehicle/note.md", "research/honda/note.md"):
                with self.assertRaises(publisher.UnsafeContent):
                    publisher.safe_scope(root, [value])

    def test_tracked_file_ignored_by_rule_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Synthetic Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            (root / ".gitignore").write_text("ignored.md\n")
            (root / "ignored.md").write_text("tracked but ignored by policy")
            subprocess.run(["git", "-C", str(root), "add", "-f", ".gitignore", "ignored.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
            with self.assertRaises(publisher.UnsafeContent):
                publisher.safe_scope(root, ["ignored.md"])

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

    def test_staged_token_after_two_megabytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "note.md").write_text("x" * 2_000_100 + "token=ghp_" + "A" * 30)
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            with self.assertRaises(publisher.Failure):
                publisher.scan_staged(root)

    def test_binary_marker_after_first_eight_kilobytes_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "note.md").write_bytes(b"x" * 9000 + b"\0")
            subprocess.run(["git", "-C", str(root), "add", "note.md"], check=True)
            with self.assertRaises(publisher.UnsafeContent):
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

    def test_pr_must_be_open_on_main_and_match_remote_sha(self):
        payload = {"url": "https://github.com/bmreyes25/ClarityLink/pull/7", "headRefName": "feature/synthetic",
                   "headRefOid": "abc123", "baseRefName": "main", "state": "OPEN"}
        for mutation in ({}, {"headRefOid": "def456"}, {"baseRefName": "release"}, {"state": "CLOSED"}):
            data = {**payload, **mutation}
            result = subprocess.CompletedProcess([], 0, __import__("json").dumps(data), "")
            with patch.object(verifier, "git", side_effect=self.git_result), \
                 patch.object(verifier.subprocess, "run", return_value=result):
                actual = verifier.run(self.root, pr=7)
            if data == payload:
                self.assertEqual(actual["result"], "REMOTE_VERIFIED")
            else:
                self.assertEqual(actual["result"], "REMOTE_SHA_MISMATCH")

    def test_unpushed_commit_is_detected_even_with_stale_tracking_metadata(self):
        self.remote_out = "def456\trefs/heads/feature/synthetic\n"
        self.ancestor_result = 0
        with patch.object(verifier, "git", side_effect=self.git_result):
            result = verifier.run(self.root)
            self.assertEqual(result["result"], "UNPUSHED_COMMITS")
            self.assertEqual(result["unpushed_commit_count"], 2)

if __name__ == "__main__":
    unittest.main()
