import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import subprocess
import threading
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "task_worktree_guard.py"
SPEC = importlib.util.spec_from_file_location("task_worktree_guard", MODULE_PATH)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class ScopeReservationTests(unittest.TestCase):
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
