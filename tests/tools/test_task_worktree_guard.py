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
    def test_recovered_finish_records_exact_publication_before_scope_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            common = Path(guard.git(root, "rev-parse", "--git-common-dir"))
            if not common.is_absolute():
                common = (root / common).resolve()
            txid = "6f5ac5e0-3312-4acd-b187-06f28ea6d3b1"
            transaction = common / "claritylink-legacy-recovery" / txid
            transaction.mkdir(parents=True, mode=0o700)
            transaction.parent.chmod(0o700)
            receipt_data = {"transaction_id": txid, "target_task_id": "continued",
                            "target_branch": "codex/continued", "target_worktree": str(root.resolve())}
            receipt_bytes = json.dumps(receipt_data, sort_keys=True).encode()
            receipt_path = transaction / "receipt.json"
            receipt_path.write_bytes(receipt_bytes)
            receipt_path.chmod(0o400)
            state_path = transaction / "state.json"
            state_path.write_text(json.dumps({"state": "TRANSFERRED",
                                              "receipt_sha256": guard.hashlib.sha256(receipt_bytes).hexdigest()}))
            state_path.chmod(0o600)
            stale_temp = transaction / "state.json.finish.interrupted.tmp"
            stale_temp.write_text("interrupted atomic-write residue")
            stale_temp.chmod(0o600)
            data = {"task_id": "continued", "branch": "codex/continued", "base": "codex/base",
                    "recovered_from": {"transaction_id": txid}}
            published = {"head": "abc123", "remote_sha": "abc123", "branch": "codex/continued",
                         "pr": {"url": "https://github.com/bmreyes25/ClarityLink/pull/201",
                                "baseRefName": "codex/base"}}
            guard.finalize_recovery(root, data, data["recovered_from"], published, 201)
            state = json.loads(state_path.read_text())
            self.assertEqual(state["state"], "PUBLICATION_VERIFIED")
            self.assertEqual(state["published_head"], "abc123")
            self.assertEqual(state["pull_request_number"], 201)

    def test_recovered_finish_refuses_mismatched_remote_sha(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            common = Path(guard.git(root, "rev-parse", "--git-common-dir"))
            if not common.is_absolute():
                common = (root / common).resolve()
            txid = "6f5ac5e0-3312-4acd-b187-06f28ea6d3b1"
            transaction = common / "claritylink-legacy-recovery" / txid
            transaction.mkdir(parents=True, mode=0o700)
            transaction.parent.chmod(0o700)
            receipt_data = {"transaction_id": txid, "target_task_id": "continued",
                            "target_branch": "codex/continued", "target_worktree": str(root.resolve())}
            receipt_bytes = json.dumps(receipt_data, sort_keys=True).encode()
            (transaction / "receipt.json").write_bytes(receipt_bytes)
            (transaction / "receipt.json").chmod(0o400)
            (transaction / "state.json").write_text(json.dumps({"state": "TRANSFERRED",
                "receipt_sha256": guard.hashlib.sha256(receipt_bytes).hexdigest()}))
            (transaction / "state.json").chmod(0o600)
            data = {"task_id": "continued", "branch": "codex/continued", "base": "codex/base",
                    "recovered_from": {"transaction_id": txid}}
            published = {"head": "abc123", "remote_sha": "different", "branch": "codex/continued",
                         "pr": {"url": "https://github.com/bmreyes25/ClarityLink/pull/201",
                                "baseRefName": "codex/base"}}
            with self.assertRaisesRegex(guard.GuardError, "exact prepared transaction"):
                guard.finalize_recovery(root, data, data["recovered_from"], published, 201)

    def test_recovered_finish_rejects_recovery_store_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            common = Path(guard.git(root, "rev-parse", "--git-common-dir"))
            if not common.is_absolute():
                common = (root / common).resolve()
            external = Path(directory) / "external-store"
            external.mkdir(mode=0o700)
            (common / "claritylink-legacy-recovery").symlink_to(external)
            data = {"task_id": "continued", "branch": "codex/continued", "base": "codex/base"}
            recovered = {"transaction_id": "6f5ac5e0-3312-4acd-b187-06f28ea6d3b1"}
            with self.assertRaisesRegex(guard.GuardError, "private owned directory"):
                guard.finalize_recovery(root, data, recovered,
                                        {"head": "abc", "remote_sha": "abc", "branch": "codex/continued",
                                         "pr": {"url": "https://github.com/bmreyes25/ClarityLink/pull/201",
                                                "baseRefName": "codex/base"}}, 201)

    def test_recovered_finish_resumes_after_interruption_before_reservation_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            manifest = root / "task.json"
            manifest.write_text("{}\n")
            common = Path(guard.git(root, "rev-parse", "--git-common-dir"))
            if not common.is_absolute():
                common = (root / common).resolve()
            txid = "6f5ac5e0-3312-4acd-b187-06f28ea6d3b1"
            transaction = common / "claritylink-legacy-recovery" / txid
            transaction.mkdir(parents=True, mode=0o700)
            transaction.parent.chmod(0o700)
            receipt_data = {"transaction_id": txid, "target_task_id": "continued",
                            "target_branch": "codex/continued", "target_worktree": str(root.resolve())}
            receipt_bytes = json.dumps(receipt_data, sort_keys=True).encode()
            (transaction / "receipt.json").write_bytes(receipt_bytes)
            (transaction / "receipt.json").chmod(0o400)
            state_path = transaction / "state.json"
            state_path.write_text(json.dumps({"state": "TRANSFERRED",
                "receipt_sha256": guard.hashlib.sha256(receipt_bytes).hexdigest()}))
            state_path.chmod(0o600)
            data = {"task_id": "continued", "branch": "codex/continued", "base": "codex/base",
                    "worktree": str(root.resolve()), "files": [],
                    "recovered_from": {"transaction_id": txid}}
            publication = {"result": "REMOTE_VERIFIED", "head": "abc123", "remote_sha": "abc123",
                          "branch": "codex/continued", "pr": {"url": "https://github.com/bmreyes25/ClarityLink/pull/201",
                              "baseRefName": "codex/base"}}
            verify = subprocess.CompletedProcess([], 0, json.dumps(publication), "")
            real_run = subprocess.run

            def verify_or_git(command, *args, **kwargs):
                if isinstance(command, list) and Path(str(command[0])).name.startswith("python"):
                    return verify
                return real_run(command, *args, **kwargs)

            outcomes = [guard.GuardError("injected interruption"), None]

            def fail_once(*_args, **_kwargs):
                outcome = outcomes.pop(0)
                if outcome:
                    raise outcome

            with patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "manifest", return_value=(manifest, common / "locks", data)), \
                 patch.object(guard, "classify", return_value={"status": []}), \
                 patch.object(guard.subprocess, "run", side_effect=verify_or_git), \
                 patch.object(guard, "release_reservations", side_effect=fail_once):
                with self.assertRaisesRegex(guard.GuardError, "injected interruption"):
                    guard.finish(root, 201, "codex/base")
                self.assertEqual(json.loads(state_path.read_text())["state"], "PUBLICATION_VERIFIED")
                result = guard.finish(root, 201, "codex/base")
            self.assertEqual(result["result"], "TASK_COMPLETE")
            self.assertFalse(manifest.exists())

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

    def test_finish_preserves_reservations_when_exact_remote_publication_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "task.json"
            data = {"task_id": "stage-a", "branch": "codex/stage-a", "base": "main",
                    "files": ["src/a.py"], "worktree": str(root)}
            response = subprocess.CompletedProcess([], 1,
                json.dumps({"result": "REMOTE_SHA_MISMATCH", "reason": "remote head differs"}), "")
            real_run = subprocess.run

            def verify_only(command, *args, **kwargs):
                if isinstance(command, list) and Path(str(command[0])).name.startswith("python"):
                    return response
                return real_run(command, *args, **kwargs)

            with patch.object(guard, "manifest", return_value=(manifest, root / "locks", data)), \
                 patch.object(guard, "manifest_transaction", return_value=nullcontext()), \
                 patch.object(guard, "classify", return_value={"status": [], "outside_scope": []}), \
                 patch.object(guard.subprocess, "run", side_effect=verify_only), \
                 patch.object(guard, "release_reservations") as release:
                with self.assertRaisesRegex(guard.GuardError, "scope remains reserved"):
                    guard.finish(root, 140)
            release.assert_not_called()

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
            with patch.object(guard, "git", return_value=str(root)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "publication_preflight", return_value={"starting_sha": "abc123"}), \
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
            with patch.object(guard, "git", return_value=str(root)), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/task"), \
                 patch.object(guard, "porcelain", return_value=[]), \
                 patch.object(guard, "publication_preflight", return_value={"starting_sha": "abc123"}) as preflight, \
                 patch.object(guard, "layout", return_value=(manifest, locks)), \
                 patch.object(guard, "validate_paths", return_value=["src/owned.py"]):
                data = guard.begin(root, "task-43", ["src/owned.py"], "codex/cycle12")
            self.assertEqual(data["base"], "codex/cycle12")
            preflight.assert_called_once_with(root.resolve(), "codex/cycle12")

    def test_publication_preflight_rejects_historical_head_before_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(guard, "git", side_effect=[str(root), "", "historical", "remote-main"]), \
                 patch.object(guard, "canonical_origin"), \
                 patch.object(guard, "branch_and_owner", return_value="codex/old-task"), \
                 patch.object(guard, "porcelain", return_value=[]):
                with self.assertRaisesRegex(guard.GuardError, "not the fetched origin/main"):
                    guard.publication_preflight(root, "main")

    def test_stacked_preflight_requires_exact_open_same_repository_pr_head(self):
        with patch.object(guard, "guard_run", return_value=subprocess.CompletedProcess(
                [], 0, json.dumps([{"headRefName": "codex/base", "headRefOid": "a" * 40,
                                    "isCrossRepository": False}]), "")) as run:
            guard.verify_publishable_base(Path("/tmp/repo"), "codex/task", "codex/base", "a" * 40)
        self.assertIn("--head", run.call_args.args[0])
        with patch.object(guard, "guard_run", return_value=subprocess.CompletedProcess(
                [], 0, json.dumps([{"headRefName": "codex/base", "headRefOid": "b" * 40,
                                    "isCrossRepository": False}]), "")):
            with self.assertRaisesRegex(guard.GuardError, "exact head of an open same-repository PR"):
                guard.verify_publishable_base(Path("/tmp/repo"), "codex/task", "codex/base", "a" * 40)

    def test_self_referential_task_base_is_rejected_before_begin(self):
        with self.assertRaisesRegex(guard.GuardError, "task base is the task branch itself"):
            guard.verify_publishable_base(Path("/tmp/repo"), "codex/task", "codex/task", "a" * 40)

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


if __name__ == "__main__":
    unittest.main()
