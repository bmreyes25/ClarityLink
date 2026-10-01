import importlib.util
from pathlib import Path
import sys
import threading
import unittest

MODULE_PATH = Path(__file__).resolve().parents[2] / "src" / "carplay-session-model" / "project_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("claritylink_project_lifecycle", MODULE_PATH)
model = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = model
SPEC.loader.exec_module(model)


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.released = []
        self.registry = model.ProjectSessionRegistry(self.released.append)
        self.child = model.ChildState(1, ["listener", "socket", "crypto", "parser"])
        self.registry.register(0x1000, 1, self.child)
        self.calls = []

    def stock(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return 37

    def control(self, request, command="tearDownStreams"):
        original = repr(request)
        result = self.registry.platform_control(0x1000, 1, command, request,
                                                self.stock, flags=1)
        self.assertEqual(repr(request), original)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][0], (0x1000, command, request))
        self.assertEqual(self.calls[0][1], {"flags": 1})
        self.assertEqual(result, 37)

    def test_type110_only_preserves_project_child(self):
        self.control({"streams": [{"type": 110}]})
        self.assertFalse(self.child.stopped)
        self.assertEqual(self.released, [])

    def test_type111_only_stops_child(self):
        self.control({"streams": [{"type": 111}]})
        self.assertEqual(len(self.released), 4)

    def test_combined_110_111_stops_project_child(self):
        self.control({"streams": [{"type": 110}, {"type": 111}]})
        self.assertEqual(len(self.released), 4)

    def test_duplicate_type111_is_idempotent(self):
        for _ in range(2):
            self.registry.platform_control(0x1000, 1, "tearDownStreams",
                                           {"streams": [{"type": 111}]}, self.stock)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.released), 4)

    def test_finalize_racing_type111_releases_once(self):
        barrier = threading.Barrier(2)
        threads = [
            threading.Thread(target=lambda: (barrier.wait(), self.registry.platform_control(
                0x1000, 1, "tearDownStreams", {"streams": [{"type": 111}]}, self.stock))),
            threading.Thread(target=lambda: (barrier.wait(), self.registry.platform_finalize(
                0x1000, 1, self.stock))),
        ]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(self.released), 4)

    def test_finalize_without_teardown_and_without_child(self):
        self.assertEqual(self.registry.platform_finalize(0x1000, 1, self.stock), 37)
        self.assertEqual(len(self.released), 4)
        self.calls.clear()
        self.assertEqual(self.registry.platform_finalize(0x2000, 1, self.stock), 37)
        self.assertEqual(len(self.calls), 1)

    def test_cleanup_exception_does_not_prevent_stock(self):
        registry = model.ProjectSessionRegistry(lambda _: (_ for _ in ()).throw(RuntimeError()))
        registry.register(5, 2, model.ChildState(2, ["resource"]))
        self.assertEqual(registry.platform_finalize(5, 2, lambda _: 9), 9)

    def test_unknown_command_malformed_array_unknown_type_and_ui_preserve_child(self):
        for command, request in [
            ("custom", {"streams": [{"type": 111}]}),
            ("tearDownStreams", {"streams": "bad"}),
            ("tearDownStreams", {"streams": [{"type": 999}]}),
            ("modesChanged", {}),
        ]:
            self.registry.platform_control(0x1000, 1, command, request, self.stock)
            self.assertFalse(self.child.stopped)
        self.assertEqual(len(self.calls), 4)

    def test_stock_exception_is_propagated_after_one_call(self):
        def fail(*args, **kwargs):
            self.calls.append((args, kwargs))
            raise RuntimeError("stock")
        with self.assertRaisesRegex(RuntimeError, "stock"):
            self.registry.platform_control(0x1000, 1, "tearDownStreams",
                                           {"streams": [{"type": 111}]}, fail)
        self.assertEqual(len(self.calls), 1)

    def test_stopped_child_and_pointer_generation_reuse(self):
        self.registry.child_stop(0x1000, 1)
        self.registry.register(0x1000, 2, model.ChildState(2, ["new-generation"]))
        self.registry.child_stop(0x1000, 1)
        self.assertEqual(self.released, ["listener", "socket", "crypto", "parser"])
        self.registry.child_stop(0x1000, 2)
        self.assertEqual(self.released[-1], "new-generation")


if __name__ == "__main__":
    unittest.main()
