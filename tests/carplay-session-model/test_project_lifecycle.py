"""Synthetic lifecycle tests: these do not execute or prove Honda behavior."""

import importlib.util
from itertools import product
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


class Resource:
    def __init__(self, name, closed=None, fail=False, entered=None, release=None):
        self.name = name
        self.closed = closed if closed is not None else []
        self.fail = fail
        self.entered = entered
        self.release = release

    def close(self):
        self.closed.append(self.name)
        if self.entered:
            self.entered.set()
            self.release.wait()
        if self.fail:
            raise OSError("synthetic close error")


class ProjectLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.registry = model.ProjectSessionRegistry()
        self.identity = object()  # opaque token; never dereferenced
        self.key = self.registry.next_key(self.identity)
        self.closed = []
        self.resources = [Resource(n, self.closed) for n in (
            "listener", "accepted_socket", "crypto", "parser", "decoder", "renderer")]
        self.tx = self.registry.prepare_child(self.key, lambda: iter(self.resources))

    def stock(self, result=31, calls=None, *, mutate=False, raises=None):
        calls = calls if calls is not None else []
        def invoke(command, params):
            calls.append((command, params))
            if mutate and isinstance(params, dict):
                params["stock_mutation"] = True
            if raises:
                raise raises
            return result
        return invoke

    def active(self):
        self.tx.mark_response_ready()
        self.assertTrue(self.tx.commit_after_response_commit())

    def test_prepare_resources_are_project_owned_and_not_active(self):
        child = self.registry.child(self.key)
        self.assertEqual(child.phase, model.ChildPhase.PREPARED)
        self.assertEqual(child.resource_owner, model.ResourceOwner.PREPARE_TRANSACTION)
        self.assertFalse(child.cleanup_started)
        self.assertFalse(self.closed)
        self.assertIsNone(self.registry.active_key(self.identity))

    def test_prepare_allocation_failure_rolls_back_partial_resources(self):
        registry = model.ProjectSessionRegistry()
        key = registry.next_key("allocation-failure")
        closed = []
        def resources():
            yield Resource("partial-listener", closed)
            raise MemoryError("synthetic allocation failure")
        with self.assertRaises(MemoryError):
            registry.prepare_child(key, resources)
        self.assertEqual(closed, ["partial-listener"])
        self.assertIsNone(registry.child(key))

    def test_rollback_releases_prepared_resources_once(self):
        self.tx.rollback_before_response_commit()
        self.tx.rollback_before_response_commit()
        self.assertEqual(self.closed, ["renderer", "decoder", "parser", "crypto", "accepted_socket", "listener"])
        self.assertEqual(self.registry.child(self.key), None)

    def test_commit_requires_response_ready_and_duplicate_commit_fails(self):
        with self.assertRaisesRegex(RuntimeError, "response transaction"):
            self.tx.commit_after_response_commit()
        self.active()
        with self.assertRaisesRegex(RuntimeError, "response transaction"):
            self.tx.commit_after_response_commit()
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)
        self.assertEqual(self.registry.child(self.key).resource_owner, model.ResourceOwner.REGISTRY)

    def test_finalize_before_commit_prevents_late_activation(self):
        self.registry.platform_finalize(self.key, lambda: 0)
        with self.assertRaisesRegex(RuntimeError, "no longer prepared"):
            self.tx.mark_response_ready()
        self.assertEqual(len(self.closed), 6)

    def test_response_serialization_failure_rolls_back_prepared_generation(self):
        self.tx.mark_response_ready()  # response candidate was built
        self.tx.rollback_before_response_commit()  # serializer did not commit
        self.assertEqual(len(self.closed), 6)
        self.assertIsNone(self.registry.child(self.key))
        self.assertIsNone(self.registry.active_key(self.identity))

    def test_type110_only_preserves_child_and_every_project_resource(self):
        self.active()
        type110_crypto = object()
        audio_state = {"volume": 0.6, "active": True}
        stock_state = {"type110_crypto": type110_crypto, "audio": audio_state}
        original_stock_state = dict(stock_state)
        request = {"streams": [{"type": 110}]}
        calls = []
        result = self.registry.platform_control(self.key, "tearDownStreams", request, self.stock(0, calls))
        self.assertEqual(result, 0)
        self.assertEqual(calls, [("tearDownStreams", request)])
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)
        self.assertEqual(self.closed, [])
        self.assertEqual(self.registry.observations[-1].unchanged_after_stock, True)
        self.assertIs(stock_state["type110_crypto"], original_stock_state["type110_crypto"])
        self.assertIs(stock_state["audio"], audio_state)
        self.assertEqual(audio_state, {"volume": 0.6, "active": True})
        self.assertFalse(any(value is type110_crypto or value is audio_state for value in self.registry.child(self.key).__dict__.values()))

    def test_type111_and_combined_teardown_cleanup_only_project_resources(self):
        self.active()
        request = {"streams": [{"type": 110}, {"type": 111}]}
        calls = []
        self.assertEqual(self.registry.platform_control(self.key, "tearDownStreams", request, self.stock(-7, calls)), -7)
        self.assertEqual(calls, [("tearDownStreams", request)])
        self.assertEqual(len(self.closed), 6)
        self.assertIsNone(self.registry.child(self.key))
        self.assertEqual(self.registry.observations[-1].stream_types, frozenset({110, 111}))

    def test_unknown_stream_type_and_empty_array_do_not_stop_child(self):
        self.active()
        for request in ({"streams": [{"type": 987}]}, {"streams": []}):
            self.registry.platform_control(self.key, "tearDownStreams", request, self.stock())
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)
        self.assertFalse(self.closed)

    def test_missing_stream_list_is_conditional_and_finalizer_is_safety_net(self):
        self.active()
        calls = []
        self.registry.platform_control(self.key, "tearDownStreams", None, self.stock(4, calls))
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)
        self.assertIsNone(self.registry.observations[-1].stream_types)
        self.registry.platform_finalize(self.key, lambda: calls.append(("finalize", None)) or 0)
        self.assertEqual(len(self.closed), 6)

    def test_malformed_request_fails_open_to_stock(self):
        self.active()
        calls = []
        malformed = {"streams": "not-a-list"}
        self.assertEqual(self.registry.platform_control(self.key, "tearDownStreams", malformed, self.stock(12, calls)), 12)
        self.assertEqual(calls, [("tearDownStreams", malformed)])
        self.assertTrue(self.registry.observations[-1].malformed)
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)

    def test_stock_called_once_request_same_object_and_result_preserved(self):
        self.active()
        calls = []
        request = {"streams": [{"type": 111}]}
        before = {"streams": [{"type": 111}]}
        self.assertEqual(self.registry.platform_control(self.key, "tearDownStreams", request, self.stock(-123, calls)), -123)
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0][1], request)
        self.assertEqual(request, before)
        self.assertTrue(self.registry.observations[-1].unchanged_after_stock)

    def test_stock_side_mutation_is_detected_without_adapter_rewrite(self):
        self.active()
        request = {"streams": [{"type": 110}]}
        calls = []
        result = self.registry.platform_control(self.key, "tearDownStreams", request,
            self.stock(18, calls, mutate=True))
        self.assertEqual(result, 18)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], request)
        self.assertFalse(self.registry.observations[-1].unchanged_after_stock)
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)

    def test_stock_platformcontrol_error_propagates_but_cleanup_runs(self):
        self.active()
        calls = []
        with self.assertRaisesRegex(RuntimeError, "stock failure"):
            self.registry.platform_control(self.key, "tearDownStreams", {"streams": [{"type": 111}]},
                                           self.stock(calls=calls, raises=RuntimeError("stock failure")))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(self.closed), 6)

    def test_project_cleanup_failure_does_not_replace_stock_result(self):
        registry = model.ProjectSessionRegistry()
        key = registry.next_key("cleanup-failure")
        bad = Resource("bad-close", fail=True)
        tx = registry.prepare_child(key, lambda: [bad])
        tx.mark_response_ready(); tx.commit_after_response_commit()
        calls = []
        result = registry.platform_control(key, "tearDownStreams", {"streams": [{"type": 111}]}, self.stock(73, calls))
        self.assertEqual(result, 73)
        self.assertEqual(len(calls), 1)
        self.assertTrue(registry.diagnostics)

    def test_finalize_active_prepared_stopped_absent_and_repeated(self):
        self.active()
        stock_calls = []
        for _ in range(2):
            self.assertEqual(self.registry.platform_finalize(self.key, lambda: stock_calls.append("stock") or 5), 5)
        self.assertEqual(stock_calls, ["stock", "stock"])
        self.assertEqual(len(self.closed), 6)
        self.assertIsNone(self.registry.active_key(self.identity))

        prepared_registry = model.ProjectSessionRegistry()
        key = prepared_registry.next_key("prepared-finalize")
        closed = []
        prepared_registry.prepare_child(key, lambda: [Resource("prepared", closed)])
        prepared_registry.platform_finalize(key, lambda: 0)
        self.assertEqual(closed, ["prepared"])
        self.assertEqual(prepared_registry.platform_finalize(key, lambda: 8), 8)
        self.assertEqual(prepared_registry.platform_finalize(key, lambda: 9), 9)

    def test_finalize_stock_runs_if_project_cleanup_callback_fails(self):
        registry = model.ProjectSessionRegistry()
        key = registry.next_key("finalize-error")
        registry.prepare_child(key, lambda: [Resource("bad", fail=True)])
        calls = []
        self.assertEqual(registry.platform_finalize(key, lambda: calls.append(1) or -9), -9)
        self.assertEqual(calls, [1])

    def test_generation_protects_pointer_reuse_and_stale_cleanup(self):
        identity = "synthetic-pointer-0x1234"
        old_key = self.registry.next_key(identity)
        old_closed = []
        old = self.registry.prepare_child(old_key, lambda: [Resource("old", old_closed)])
        old.mark_response_ready(); old.commit_after_response_commit()
        self.registry.platform_finalize(old_key, lambda: 0)
        new_key = self.registry.next_key(identity)
        new_closed = []
        new = self.registry.prepare_child(new_key, lambda: [Resource("new", new_closed)])
        new.mark_response_ready(); new.commit_after_response_commit()
        self.registry.project_transport_failed(old_key, "delayed old EOF")
        self.assertEqual(self.registry.active_key(identity), new_key)
        self.assertEqual(self.registry.child(new_key).phase, model.ChildPhase.ACTIVE)
        self.assertEqual(old_closed, ["old"])
        self.assertEqual(new_closed, [])

    def test_same_generation_cannot_be_registered_twice(self):
        with self.assertRaisesRegex(ValueError, "already used"):
            self.registry.prepare_child(self.key, lambda: [])

    def test_eof_and_ui_events_are_project_only_and_ui_keeps_transport(self):
        self.active()
        for command in ("suggestUI", "showUI", "stopUI", "modesChanged", "requestUI"):
            self.assertTrue(self.registry.record_ui_event(self.key, command))
        self.assertEqual(self.registry.child(self.key).phase, model.ChildPhase.ACTIVE)
        self.registry.project_transport_failed(self.key, "peer EOF")
        self.assertEqual(len(self.closed), 6)
        self.assertIsNone(self.registry.child(self.key))

    def test_type111_teardown_vs_finalize_race_releases_each_resource_once(self):
        self.active()
        barrier = threading.Barrier(3)
        errors = []
        def run(fn):
            try:
                barrier.wait()
                fn()
            except Exception as exc:
                errors.append(exc)
        a = threading.Thread(target=run, args=(lambda: self.registry.platform_control(
            self.key, "tearDownStreams", {"streams": [{"type": 111}]}, self.stock()),))
        b = threading.Thread(target=run, args=(lambda: self.registry.platform_finalize(self.key, lambda: 0),))
        a.start(); b.start(); barrier.wait(); a.join(); b.join()
        self.assertEqual(errors, [])
        self.assertCountEqual(self.closed, [r.name for r in self.resources])
        self.assertEqual(len(self.closed), len(set(self.closed)))

    def test_rollback_vs_finalize_race_releases_once(self):
        barrier = threading.Barrier(3)
        errors = []
        def rollback():
            try: barrier.wait(); self.tx.rollback_before_response_commit()
            except Exception as exc: errors.append(exc)
        def finalize():
            try: barrier.wait(); self.registry.platform_finalize(self.key, lambda: 0)
            except Exception as exc: errors.append(exc)
        a=threading.Thread(target=rollback); b=threading.Thread(target=finalize)
        a.start(); b.start(); barrier.wait(); a.join(); b.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(self.closed), 6)
        self.assertEqual(len(set(self.closed)), 6)

    def test_finalize_during_resource_preparation_closes_late_resources(self):
        registry = model.ProjectSessionRegistry()
        key = registry.next_key("prepare-finalize-race")
        first_closed, late_closed = [], []
        yielded = threading.Event()
        continue_factory = threading.Event()
        errors = []
        def factory():
            yield Resource("early", first_closed)
            yielded.set()
            continue_factory.wait()
            yield Resource("late", late_closed)
        def prepare():
            try: registry.prepare_after_stock_setup(key, factory)
            except Exception as exc: errors.append(exc)
        thread = threading.Thread(target=prepare)
        thread.start()
        yielded.wait()
        stock_calls = []
        self.assertEqual(registry.platform_finalize(key, lambda: stock_calls.append(1) or 0), 0)
        continue_factory.set()
        thread.join()
        self.assertEqual(len(errors), 1)
        self.assertEqual(first_closed, ["early"])
        self.assertEqual(late_closed, ["late"])
        self.assertEqual(stock_calls, [1])
        self.assertIsNone(registry.child(key))

    def test_socket_eof_vs_type111_teardown_releases_once(self):
        barrier = threading.Barrier(3)
        def eof():
            barrier.wait(); self.registry.project_transport_failed(self.key, "EOF")
        def teardown():
            barrier.wait(); self.registry.platform_control(self.key, "tearDownStreams",
                {"streams": [{"type": 111}]}, self.stock())
        a=threading.Thread(target=eof); b=threading.Thread(target=teardown)
        a.start(); b.start(); barrier.wait(); a.join(); b.join()
        self.assertEqual(len(self.closed), 6)
        self.assertEqual(len(set(self.closed)), 6)

    def test_sequence_enumeration_preserves_exactly_once_invariant(self):
        events = ("commit", "teardown", "eof", "finalize")
        for sequence in product(events, repeat=4):
            registry = model.ProjectSessionRegistry()
            key = registry.next_key(("sequence", sequence))
            closed = []
            tx = registry.prepare_child(key, lambda: [Resource(str(i), closed) for i in range(3)])
            for event in sequence:
                if event == "commit":
                    try:
                        tx.mark_response_ready()
                        tx.commit_after_response_commit()
                    except RuntimeError:
                        pass
                elif event == "teardown":
                    registry.platform_control(key, "tearDownStreams", {"streams": [{"type": 111}]}, lambda *_: 0)
                elif event == "eof":
                    registry.project_transport_failed(key, "enumerated EOF")
                else:
                    registry.platform_finalize(key, lambda: 0)
            registry.platform_finalize(key, lambda: 0)
            self.assertEqual(len(closed), 3, sequence)
            self.assertEqual(len(set(closed)), 3, sequence)


if __name__ == "__main__":
    unittest.main()
