import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

TOOL = Path(__file__).resolve().parents[2] / "tools" / "recover_legacy_task.py"
SPEC = importlib.util.spec_from_file_location("recover_legacy_task", TOOL)
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)
guard = recovery.guard


def run(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], text=True,
                            capture_output=True, timeout=15)
    if check and result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


class LegacyRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.scope = ["src/one.txt", "src/two.txt", "src/committed-mode.txt", "src/pending-mode.txt"]
        run(self.root, "init", "--bare", str(self.remote))
        run(self.root, "init", str(self.repo))
        run(self.repo, "config", "user.name", "Test Owner")
        run(self.repo, "config", "user.email", "test@example.invalid")
        run(self.repo, "checkout", "-b", "main")
        (self.repo / "src").mkdir()
        (self.repo / self.scope[0]).write_text("base-one\nline-2\nline-3\nline-4\nline-5\nkeep-one\n")
        (self.repo / self.scope[1]).write_text("base-two\nkeep-two\n")
        (self.repo / self.scope[2]).write_text("mode-committed\n")
        (self.repo / self.scope[3]).write_text("mode-pending\n")
        run(self.repo, "add", *self.scope)
        run(self.repo, "commit", "-m", "base")
        self.start = run(self.repo, "rev-parse", "HEAD")
        run(self.repo, "remote", "add", "origin", str(self.remote))
        run(self.repo, "push", "-u", "origin", "main")
        run(self.repo, "worktree", "add", "-b", "claude/legacy", str(self.source), self.start)
        run(self.source, "config", "user.name", "Test Owner")
        run(self.source, "config", "user.email", "test@example.invalid")
        run(self.source, "worktree", "add", "-b", "codex/target", str(self.target), self.start)
        self._write_source_task()
        self._add_owner_commit_and_dirty_change()

    def tearDown(self):
        self.temp.cleanup()

    def _write_source_task(self):
        manifest, locks = guard.layout(self.source)
        data = {"task_id": "legacy-task", "branch": "claude/legacy",
                "worktree": str(self.source.resolve()), "starting_sha": self.start,
                "base": "main", "started_at": 100, "files": self.scope}
        guard.atomic_manifest_write(manifest, data)
        guard.reserve(locks, self.scope, {key: data[key] for key in
                                          ("task_id", "branch", "worktree", "started_at")})

    def _add_owner_commit_and_dirty_change(self):
        (self.source / self.scope[0]).write_text("owner-commit\nline-2\nline-3\nline-4\nline-5\nkeep-one\n")
        (self.source / self.scope[1]).write_text("base-two\nowner-commit\n")
        run(self.source, "add", *self.scope)
        run(self.source, "commit", "-m", "legacy scoped change")
        (self.source / self.scope[0]).write_text("owner-final\nline-2\nline-3\nline-4\nline-5\nkeep-one\n")
        (self.source / self.scope[1]).write_text("base-two\nowner-final\n")

    def _prepare(self):
        with patch.object(guard, "canonical_origin"):
            result = recovery.prepare(self.source, self.target, "continued-task", "main")
        return result

    def _commit(self, result, auth=None):
        auth = auth or result["owner_authorization"]
        with patch.object(guard, "canonical_origin"):
            return recovery.commit(self.target, result["transaction_id"], auth)

    def test_prepare_records_commits_working_changes_and_clean_overlap_plan(self):
        result = self._prepare()
        self.assertEqual(result["result"], "RECOVERY_PREPARED")
        self.assertEqual(result["paths"], self.scope[:2])
        self.assertEqual(result["overlap_paths"], [])
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertEqual(receipt["source_head"], run(self.source, "rev-parse", "HEAD"))
        self.assertEqual(receipt["source_starting_sha"], self.start)
        self.assertEqual(receipt["source_paths"], self.scope[:2])
        self.assertEqual(json.loads((Path(result["receipt"]).parent / "state.json").read_text())["state"],
                         "PREPARED")
        self.assertEqual(guard.changed_paths(self.source), set(self.scope[:2]))

    def test_missing_owner_authorization_leaves_source_and_target_unchanged(self):
        result = self._prepare()
        with self.assertRaisesRegex(guard.GuardError, "owner authorization missing"):
            self._commit(result, "yes")
        self.assertEqual(guard.changed_paths(self.target), set())
        self.assertEqual(guard.changed_paths(self.source), set(self.scope[:2]))
        _, locks = guard.layout(self.source)
        for path in self.scope:
            self.assertEqual(json.loads((locks / guard.path_key(path)).read_text())["task_id"], "legacy-task")

    def test_authorization_from_another_prepared_target_is_rejected(self):
        first = self._prepare()
        alternate = self.root / "target-alt"
        run(self.repo, "worktree", "add", "-b", "codex/target-alt", str(alternate), self.start)
        with patch.object(guard, "canonical_origin"):
            second = recovery.prepare(self.source, alternate, "continued-task", "main")
            with self.assertRaisesRegex(guard.GuardError, "owner authorization missing"):
                recovery.commit(self.target, first["transaction_id"], second["owner_authorization"])
        self.assertEqual(guard.changed_paths(self.target), set())
        self.assertEqual(guard.changed_paths(self.source), set(self.scope[:2]))

    def test_transaction_id_path_traversal_is_rejected(self):
        with self.assertRaisesRegex(guard.GuardError, "invalid recovery transaction ID"):
            recovery.commit(self.target, "../../outside", "anything")

    def test_success_transfers_exact_reservations_and_is_idempotent(self):
        result = self._prepare()
        committed = self._commit(result)
        self.assertEqual(committed["result"], "RECOVERY_TRANSFERRED")
        source_manifest, source_locks = guard.layout(self.source)
        target_manifest, target_locks = guard.layout(self.target)
        source_data = json.loads(source_manifest.read_text())
        target_data = json.loads(target_manifest.read_text())
        self.assertEqual(source_data["transfer_status"], "TRANSFERRED")
        self.assertEqual(target_data["recovered_from"]["task_id"], "legacy-task")
        self.assertEqual(guard.changed_paths(self.source), set(self.scope[:2]))
        self.assertEqual(guard.changed_paths(self.target), set(self.scope[:2]))
        for path in self.scope:
            lock = target_locks / guard.path_key(path)
            owner = json.loads(lock.read_text())
            self.assertEqual(owner["task_id"], "continued-task")
        repeated = self._commit(result)
        self.assertTrue(repeated["idempotent"])

    def test_interrupted_lock_transfer_resumes_without_conflicting_owners(self):
        result = self._prepare()
        real_write = guard.atomic_manifest_write
        count = {"locks": 0, "target_manifest": 0}

        def interrupt_once(path, data):
            path = Path(path)
            if path.name == "claritylink-task.json" and str(path).startswith(str(guard.layout(self.target)[0].parent)):
                count["target_manifest"] += 1
            elif path.name != "claritylink-task.json":
                count["locks"] += 1
                if count["locks"] == 2:
                    raise OSError("injected interrupted transfer")
            return real_write(path, data)

        with patch.object(guard, "canonical_origin"), patch.object(guard, "atomic_manifest_write",
                                                                   side_effect=interrupt_once):
            with self.assertRaisesRegex(OSError, "injected interrupted transfer"):
                recovery.commit(self.target, result["transaction_id"],
                                result["owner_authorization"])
        _, locks = guard.layout(self.source)
        owners = [json.loads((locks / guard.path_key(path)).read_text())["task_id"] for path in self.scope]
        self.assertIn("legacy-task", owners)
        self.assertIn("continued-task", owners)
        resumed = self._commit(result)
        self.assertEqual(resumed["result"], "RECOVERY_TRANSFERRED")
        owners = [json.loads((locks / guard.path_key(path)).read_text())["task_id"] for path in self.scope]
        self.assertEqual(owners, ["continued-task"] * len(self.scope))

    def test_interrupted_apply_rejects_independent_executable_mode_change(self):
        result = self._prepare()
        real_apply = recovery.apply_merged_files

        def apply_one_then_interrupt(root, merged):
            path = self.scope[0]
            real_apply(root, {path: merged[path]})
            raise OSError("injected interrupted file application")

        with patch.object(guard, "canonical_origin"), patch.object(
                recovery, "apply_merged_files", side_effect=apply_one_then_interrupt):
            with self.assertRaisesRegex(OSError, "injected interrupted file application"):
                recovery.commit(self.target, result["transaction_id"], result["owner_authorization"])

        recovered_path = self.target / self.scope[0]
        self.assertEqual(recovered_path.read_text(), (self.source / self.scope[0]).read_text())
        recovered_path.chmod(0o755)
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "content or mode"):
                recovery.commit(self.target, result["transaction_id"], result["owner_authorization"])

        source_manifest, source_locks = guard.layout(self.source)
        self.assertNotEqual(json.loads(source_manifest.read_text()).get("transfer_status"), "TRANSFERRED")
        self.assertEqual(json.loads((source_locks / guard.path_key(self.scope[0])).read_text())["task_id"],
                         "legacy-task")

    def test_source_scope_collision_blocks_prepare(self):
        _, locks = guard.layout(self.source)
        lock = locks / guard.path_key(self.scope[0])
        lock.write_text(json.dumps({"task_id": "other", "branch": "codex/other",
                                    "worktree": "/other", "started_at": 2,
                                    "path": self.scope[0]}))
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "ownership mismatch"):
                recovery.prepare(self.source, self.target, "continued-task", "main")

    def test_self_referential_recovery_base_is_rejected(self):
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "invalid or self-referential"):
                recovery.prepare(self.source, self.target, "continued-task", "codex/target")

    def test_fifty_eight_commit_base_advance_is_rejected_before_transfer(self):
        run(self.repo, "checkout", "main")
        history = self.repo / "history.txt"
        for number in range(58):
            with history.open("a") as stream:
                stream.write(f"{number}\n")
            run(self.repo, "add", "history.txt")
            run(self.repo, "commit", "-m", f"advance {number}")
        run(self.repo, "push", "origin", "main")
        self.assertEqual(int(run(self.repo, "rev-list", "--count", f"{self.start}..main")), 58)
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "target must start at exact fetched origin/main"):
                recovery.prepare(self.source, self.target, "continued-task", "main")

    def test_cleanly_overlapping_target_path_is_recorded_for_review(self):
        run(self.repo, "checkout", "main")
        (self.repo / self.scope[0]).write_text("base-one\nline-2\nline-3\nline-4\nline-5\ntarget-keep\n")
        run(self.repo, "add", self.scope[0])
        run(self.repo, "commit", "-m", "target changes adjacent line")
        run(self.repo, "push", "origin", "main")
        run(self.repo, "worktree", "remove", "--force", str(self.target))
        self.target = self.root / "target-new"
        run(self.repo, "worktree", "add", "-b", "codex/target-new", str(self.target), "origin/main")
        with patch.object(guard, "canonical_origin"):
            result = recovery.prepare(self.source, self.target, "continued-task", "main")
        self.assertEqual(result["overlap_paths"], [self.scope[0]])

    def test_conflicting_overlap_is_refused_without_source_transfer(self):
        run(self.repo, "checkout", "main")
        (self.repo / self.scope[0]).write_text("target-conflict\nline-2\nline-3\nline-4\nline-5\nkeep-one\n")
        run(self.repo, "add", self.scope[0])
        run(self.repo, "commit", "-m", "target conflicting change")
        run(self.repo, "push", "origin", "main")
        run(self.repo, "worktree", "remove", "--force", str(self.target))
        self.target = self.root / "target-new"
        run(self.repo, "worktree", "add", "-b", "codex/target-new", str(self.target), "origin/main")
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "semantic conflict resolution"):
                recovery.prepare(self.source, self.target, "continued-task", "main")
        self.assertEqual(guard.changed_paths(self.source), set(self.scope[:2]))

    def test_out_of_scope_historical_commit_is_rejected(self):
        (self.source / "outside.txt").write_text("unrelated\n")
        run(self.source, "add", "outside.txt")
        run(self.source, "commit", "-m", "unrelated path")
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "outside its recorded reservations"):
                recovery.prepare(self.source, self.target, "continued-task", "main")

    def test_target_base_moving_after_prepare_preserves_owner_reservations(self):
        result = self._prepare()
        (self.repo / "advanced.txt").write_text("new base\n")
        run(self.repo, "add", "advanced.txt")
        run(self.repo, "commit", "-m", "advance remote base")
        run(self.repo, "push", "origin", "main")
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "base advanced after preparation"):
                recovery.commit(self.target, result["transaction_id"],
                                result["owner_authorization"])
        _, locks = guard.layout(self.source)
        for path in self.scope:
            self.assertEqual(json.loads((locks / guard.path_key(path)).read_text())["task_id"], "legacy-task")

    def test_two_concurrent_transfer_attempts_are_serialized_and_idempotent(self):
        result = self._prepare()
        auth = result["owner_authorization"]
        outcomes = []
        failures = []

        def transfer():
            try:
                with patch.object(guard, "canonical_origin"):
                    outcomes.append(recovery.commit(self.target, result["transaction_id"], auth))
            except Exception as exc:  # the test reports the exact concurrent failure
                failures.append(exc)

        threads = [threading.Thread(target=transfer) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(failures, failures)
        self.assertEqual(len(outcomes), 2)
        self.assertTrue(all(row["result"] == "RECOVERY_TRANSFERRED" for row in outcomes))

    def test_stale_source_start_is_rejected(self):
        manifest, _locks = guard.layout(self.source)
        data = json.loads(manifest.read_text())
        data["starting_sha"] = "0" * 40
        guard.atomic_manifest_write(manifest, data)
        with patch.object(guard, "canonical_origin"):
            with self.assertRaisesRegex(guard.GuardError, "not a local commit"):
                recovery.prepare(self.source, self.target, "continued-task", "main")

    def test_committed_and_uncommitted_mode_only_changes_are_transferred(self):
        committed = self.source / self.scope[2]
        pending = self.source / self.scope[3]
        committed.chmod(0o755)
        run(self.source, "add", self.scope[2])
        run(self.source, "commit", "-m", "legacy executable mode change")
        pending.chmod(0o755)
        result = self._prepare()
        receipt = json.loads(Path(result["receipt"]).read_text())
        self.assertIn(self.scope[2], receipt["merged_path_hashes"])
        self.assertIn(self.scope[3], receipt["merged_path_hashes"])
        self._commit(result)
        self.assertTrue((self.target / self.scope[2]).stat().st_mode & 0o111)
        self.assertTrue((self.target / self.scope[3]).stat().st_mode & 0o111)


if __name__ == "__main__":
    unittest.main()
