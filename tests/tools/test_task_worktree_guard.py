import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import subprocess
import threading
from contextlib import nullcontext
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "task_worktree_guard.py"
SPEC = importlib.util.spec_from_file_location("task_worktree_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class ScopeReservationTests(unittest.TestCase):
    def test_recovery_audit_refuses_hard_link_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "private-target"
            target.write_text("preserve\n")
            audit = root / "claritylink-task-recovery.jsonl"
            audit.hardlink_to(target)
            with self.assertRaisesRegex(guard.GuardError, "singly linked"):
                guard.append_recovery_audit(audit, {"event": "test"})
            self.assertEqual(target.read_text(), "preserve\n")

    def test_guard_run_converts_timeout_to_actionable_guard_error(self):
        with patch.object(guard.subprocess, "run", side_effect=subprocess.TimeoutExpired(["gh"], 15)):
            with self.assertRaisesRegex(guard.GuardError, "timed out after 15 seconds"):
                guard.guard_run(["gh", "pr", "view", "140"])

    def test_bind_pr_binds_existing_remote_head_to_verified_stacked_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            manifest.write_text("{}\n")
            data = {"task_id": "stage-a", "branch": "codex/stage-a",
                    "base": "codex/stage-a", "starting_sha": "abc123",
                    "worktree": str(root), "files": ["tools/a.py"]}
            responses = [
                subprocess.CompletedProcess([], 0, "", ""),  # ref format
                subprocess.CompletedProcess([], 0, "abc123\trefs/heads/codex/stage-a\n", ""),
                subprocess.CompletedProcess([], 0, json.dumps({
                    "headRefName": "codex/stage-a", "headRefOid": "abc123",
                    "baseRefName": "codex/cycle12", "state": "OPEN",
                    "isCrossRepository": False}), ""),
                subprocess.CompletedProcess([], 0, json.dumps([{"headRefName": "codex/cycle12",
                                                                   "isCrossRepository": False}]), ""),
                subprocess.CompletedProcess([], 0, "", ""),  # ancestor
            ]
            captured = {}
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)), \
                 patch.object(guard, "changed_paths", return_value={"tools/a.py"}), \
                 patch.object(guard, "git", side_effect=["abc123", ""]) as git, \
                 patch.object(guard.subprocess, "run", side_effect=responses) as run, \
                 patch.object(guard, "atomic_manifest_write", side_effect=lambda _path, value: captured.update(value)):
                result = guard.bind_pull_request(root, 140, "codex/cycle12")
            self.assertEqual(result["base"], "codex/cycle12")
            self.assertEqual(result["pull_request"], 140)
            self.assertEqual(captured["starting_sha"], "abc123")
            self.assertEqual(run.call_args_list[2].args[0][0:4],
                             ["gh", "pr", "view", "140"])
            git.assert_any_call(root, "fetch", "--quiet", "origin", "codex/cycle12")

    def test_bind_pr_rejects_a_base_that_is_not_an_open_pr_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            data = {"task_id": "stage-a", "branch": "codex/stage-a",
                    "base": "codex/stage-a", "starting_sha": "abc123",
                    "worktree": str(root), "files": []}
            responses = [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "abc123\trefs/heads/codex/stage-a\n", ""),
                subprocess.CompletedProcess([], 0, json.dumps({
                    "headRefName": "codex/stage-a", "headRefOid": "abc123",
                    "baseRefName": "codex/cycle12", "state": "OPEN",
                    "isCrossRepository": False}), ""),
                subprocess.CompletedProcess([], 0, "[]", ""),
            ]
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)), \
                 patch.object(guard, "changed_paths", return_value=set()), \
                 patch.object(guard, "git", return_value="abc123"), \
                 patch.object(guard.subprocess, "run", side_effect=responses):
                with self.assertRaisesRegex(guard.GuardError, "head of an open PR"):
                    guard.bind_pull_request(root, 140, "codex/cycle12")

    def test_finish_verifies_a_stacked_pr_against_its_exact_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            manifest.write_text("{}\n")
            data = {"task_id": "stage-a", "branch": "codex/stage-a", "base": "codex/cycle12", "files": []}
            response = subprocess.CompletedProcess([], 0,
                json.dumps({"result": "REMOTE_VERIFIED", "head": "abc123", "pr": {"url": "https://github.com/bmreyes25/ClarityLink/pull/140"}}), "")
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)), \
                 patch.object(guard, "classify", return_value={"status": []}), \
                 patch.object(guard.subprocess, "run", return_value=response) as run, \
                 patch.object(guard, "release_reservations"):
                result = guard.finish(root, 140, "codex/cycle12")
            self.assertEqual(result["result"], "TASK_COMPLETE")
            self.assertIn("--base", run.call_args.args[0])
            self.assertEqual(run.call_args.args[0][-1], "codex/cycle12")

    def test_finish_rejects_a_base_that_differs_from_task_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            manifest.write_text("{}\n")
            data = {"task_id": "stage-a", "branch": "codex/stage-a", "base": "codex/cycle12", "files": []}
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)):
                with self.assertRaisesRegex(guard.GuardError, "differs from task manifest base"):
                    guard.finish(root, 140, "main")

    def test_reservation_blocks_a_second_worktree_from_claiming_same_file(self):
        with tempfile.TemporaryDirectory() as directory:
            locks = Path(directory)
            owner = {"task_id": "first", "branch": "codex/first", "worktree": "/tmp/first"}
            guard.reserve(locks, ["src/component.py"], owner)
            with self.assertRaisesRegex(guard.GuardError, "already held"):
                guard.reserve(locks, ["src/component.py"], {**owner, "task_id": "second"})

    def test_reservations_allow_nonoverlapping_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            locks = Path(directory)
            guard.reserve(locks, ["src/one.py"], {"task_id": "one"})
            guard.reserve(locks, ["src/two.py"], {"task_id": "two"})
            self.assertEqual(len([path for path in locks.iterdir() if not path.name.startswith(".")]), 2)

    def test_scope_transactions_serialize_competing_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            locks = Path(directory)
            entered = threading.Event()
            released = threading.Event()

            def first():
                with guard.scope_transaction(locks):
                    entered.set()
                    released.wait(timeout=2)

            worker = threading.Thread(target=first)
            worker.start()
            self.assertTrue(entered.wait(timeout=1))
            acquired = threading.Event()

            def second():
                with guard.scope_transaction(locks):
                    acquired.set()

            contender = threading.Thread(target=second)
            contender.start()
            self.assertFalse(acquired.wait(timeout=0.05))
            released.set()
            worker.join(timeout=1)
            contender.join(timeout=1)
            self.assertTrue(acquired.is_set())

    def test_begin_records_start_sha_and_reserves_reviewed_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            locks = root / "locks"
            with patch.object(guard, "git", side_effect=[str(root), "", "abc123", "abc123"]), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "layout", return_value=(manifest, locks)), \
                 patch.object(guard, "validate_paths", return_value=["src/owned.py"]):
                data = guard.begin(root, "task-42", ["src/owned.py"])
            self.assertEqual(data["starting_sha"], "abc123")
            self.assertEqual(data["files"], ["src/owned.py"])
            self.assertEqual(json.loads(manifest.read_text())["task_id"], "task-42")
            self.assertEqual(len([path for path in locks.iterdir() if not path.name.startswith(".")]), 1)

    def test_begin_can_bind_a_stacked_task_to_exact_pr_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            locks = root / "locks"
            with patch.object(guard, "git", side_effect=[str(root), "", "abc123", "abc123"]) as git, \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "layout", return_value=(manifest, locks)), \
                 patch.object(guard, "validate_paths", return_value=["src/owned.py"]):
                data = guard.begin(root, "task-43", ["src/owned.py"], "codex/cycle12")
            self.assertEqual(data["base"], "codex/cycle12")
            self.assertEqual(git.call_args_list[1].args[1:], ("fetch", "--quiet", "origin", "codex/cycle12"))
            self.assertEqual(git.call_args_list[3].args[1:], ("rev-parse", "refs/remotes/origin/codex/cycle12"))

    def test_paths_reject_globs_traversal_and_restricted_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(guard.GuardError, "invalid scoped path"):
                guard.validate_paths(root, ["src/*.py"])
            with self.assertRaisesRegex(guard.GuardError, "invalid scoped path"):
                guard.validate_paths(root, ["../outside.py"])
            with self.assertRaisesRegex(guard.GuardError, "restricted path"):
                guard.validate_paths(root, ["research/captures/frame.md"])
            for path in ("research/handoff/private.md", ".local-backups/notes.md",
                         ".local-artifacts/capture.txt", "firmware/jmcs.elf"):
                with self.subTest(path=path), self.assertRaisesRegex(guard.GuardError, "restricted path"):
                    guard.validate_paths(root, [path])

    def test_symlink_cannot_redirect_a_public_scope_into_private_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            private = root / ".local-artifacts"
            private.mkdir()
            (private / "capture.txt").write_text("private marker\n")
            (root / "public-notes.txt").symlink_to(private / "capture.txt")
            with self.assertRaisesRegex(guard.GuardError, "symlink"):
                guard.validate_paths(root, ["public-notes.txt"])

    def test_release_preserves_reservation_owned_by_another_task(self):
        with tempfile.TemporaryDirectory() as directory:
            locks = Path(directory)
            data = {"task_id": "mine", "branch": "codex/mine", "worktree": "/tmp/mine",
                    "files": ["src/file.py"]}
            lock = locks / guard.path_key("src/file.py")
            lock.write_text(json.dumps({"task_id": "other", "branch": "codex/other",
                                        "worktree": "/tmp/other", "path": "src/file.py"}))
            with self.assertRaisesRegex(guard.GuardError, "ownership mismatch"):
                guard.release_reservations(locks, data)
            self.assertTrue(lock.exists())

    def test_status_classification_preserves_paths_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "owned file.py").write_text("owned\n")
            (root / "unknown file.txt").write_text("unknown\n")
            self.assertEqual(guard.changed_paths(root), {"owned file.py", "unknown file.txt"})

    def test_recover_self_base_requires_exact_remote_publication_then_uses_finish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            lock_dir = root / "locks"
            branch = "codex/task"
            base = "codex/base"
            start = "1" * 40
            head = "2" * 40
            data = {"task_id": "task-42", "branch": branch, "base": branch,
                    "starting_sha": start, "worktree": str(root),
                    "files": ["src/owned.py"]}
            pr = {"headRefName": branch, "headRefOid": head, "baseRefName": base,
                  "state": "OPEN", "isCrossRepository": False}
            responses = [
                subprocess.CompletedProcess([], 0, f"{head}\trefs/heads/{branch}\n", ""),
                subprocess.CompletedProcess([], 0, json.dumps(pr), ""),
                subprocess.CompletedProcess([], 0, json.dumps([{"headRefName": base,
                                                                  "isCrossRepository": False}]), ""),
                subprocess.CompletedProcess([], 0, "", ""),  # verified base ancestor
                subprocess.CompletedProcess([], 0, "src/owned.py\0", ""),  # every committed path
                subprocess.CompletedProcess([], 0, json.dumps({"result": "REMOTE_VERIFIED",
                                                                  "remote_sha": head}), ""),
            ]
            finish_result = {"result": "TASK_COMPLETE", "task_id": "task-42",
                             "branch": branch, "head": head, "pr": pr}
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, lock_dir, data)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value=branch), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "verify_reservation_ownership", return_value=[]), \
                 patch.object(guard, "git", side_effect=[head, "", start, ""]) as git, \
                 patch.object(guard, "guard_run", side_effect=responses), \
                 patch.object(guard, "finish", return_value=finish_result) as finish:
                result = guard.recover_self_base_and_finish(root, 140)

            self.assertEqual(result["result"], "TASK_RECOVERY_COMPLETE")
            self.assertEqual(result["base"], base)
            self.assertEqual(result["head"], head)
            self.assertEqual(finish.call_args.args, (root, 140, base))
            git.assert_any_call(root, "fetch", "--quiet", "origin", base)
            updated = json.loads(manifest.read_text())
            self.assertEqual(updated["base"], base)
            self.assertEqual(updated["pull_request"], 140)
            audit = json.loads((root / "claritylink-task-recovery.jsonl").read_text())
            self.assertEqual(audit["event"], "self_base_manifest_repair")
            self.assertEqual(audit["starting_sha"], start)
            self.assertEqual(audit["head"], head)

    def test_recover_self_base_refuses_out_of_scope_committed_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            data = {"task_id": "task-42", "branch": "codex/task", "base": "codex/task",
                    "starting_sha": "1" * 40, "worktree": str(root),
                    "files": ["src/owned.py"]}
            responses = [
                subprocess.CompletedProcess([], 0, f"{'2' * 40}\trefs/heads/codex/task\n", ""),
                subprocess.CompletedProcess([], 0, json.dumps({"headRefName": "codex/task",
                    "headRefOid": "2" * 40, "baseRefName": "codex/base", "state": "OPEN",
                    "isCrossRepository": False}), ""),
                subprocess.CompletedProcess([], 0, json.dumps([{"headRefName": "codex/base",
                    "isCrossRepository": False}]), ""),
                subprocess.CompletedProcess([], 0, "", ""),
                # With rename detection disabled, an out-of-scope rename reports
                # both its deleted source and reserved destination.
                subprocess.CompletedProcess([], 0, "private/source.txt\0src/owned.py\0", ""),
            ]
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "verify_reservation_ownership", return_value=[]), \
                 patch.object(guard, "git", side_effect=["2" * 40, "", "1" * 40, ""]), \
                 patch.object(guard, "guard_run", side_effect=responses), \
                 patch.object(guard, "finish") as finish:
                with self.assertRaisesRegex(guard.GuardError, "private/source.txt"):
                    guard.recover_self_base_and_finish(root, 140)
            finish.assert_not_called()
            self.assertFalse((root / "claritylink-task-recovery.jsonl").exists())

    def test_recover_self_base_refuses_unpublished_or_mismatched_remote_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = {"task_id": "task-42", "branch": "codex/task", "base": "codex/task",
                    "starting_sha": "1" * 40, "worktree": str(root),
                    "files": ["src/owned.py"]}
            responses = [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "src/owned.py\0", ""),
                subprocess.CompletedProcess([], 0, f"{'3' * 40}\trefs/heads/codex/task\n", ""),
            ]
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(root / "task.json", root / "locks", data)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "verify_reservation_ownership", return_value=[]), \
                 patch.object(guard, "git", return_value="2" * 40), \
                 patch.object(guard, "guard_run", side_effect=responses), \
                 patch.object(guard, "finish") as finish:
                with self.assertRaisesRegex(guard.GuardError, "remote task branch does not match"):
                    guard.recover_self_base_and_finish(root, 140)
            finish.assert_not_called()

    def test_recover_self_base_preserves_task_on_reservation_ownership_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            manifest.write_text('{"sentinel":"preserve"}\n')
            original_manifest = manifest.read_bytes()
            lock_dir = root / "locks"
            lock_dir.mkdir()
            lock_file = lock_dir / guard.path_key("src/owned.py")
            lock_file.write_text('{"task_id":"somebody-else"}\n')
            data = {"task_id": "task-42", "branch": "codex/task", "base": "codex/task",
                    "starting_sha": "1" * 40, "worktree": str(root), "files": ["src/owned.py"]}
            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, lock_dir, data)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "verify_reservation_ownership",
                              side_effect=guard.GuardError("scope owner changed")), \
                 patch.object(guard, "finish") as finish:
                with self.assertRaisesRegex(guard.GuardError, "scope owner changed"):
                    guard.recover_self_base_and_finish(root, 140)
            finish.assert_not_called()
            self.assertEqual(manifest.read_bytes(), original_manifest)
            self.assertTrue(lock_file.exists())


if __name__ == "__main__":
    unittest.main()
