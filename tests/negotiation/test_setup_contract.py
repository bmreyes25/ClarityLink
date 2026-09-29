import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-negotiation"))

from lifecycle import State, Type111Lifecycle
from screen_kdf import derive_honda_type110_screen_key_iv
from setup_augmentor import SetupAugmentationError, augment_setup_response
from setup_transaction import run_stock_first_setup


class SetupAugmentorTests(unittest.TestCase):
    def setUp(self):
        self.request = {
            "sessionTag": "opaque-root",
            "streams": [
                {"type": 100, "audioFormat": 7, "peerOpaque": {"x": 1}},
                {"type": 110, "streamConnectionID": 11, "peerOpaque": "main"},
                {"type": 111, "streamConnectionID": 22, "peerOpaque": [1, 2]},
            ],
        }
        self.stock = {"streams": [{"type": 100, "dataPort": 5001}, {"type": 110, "dataPort": 5002}], "opaque": 9}

    def test_stock_only_request_returns_exact_copy(self):
        request = {"streams": [{"type": 100}, {"type": 110}]}
        original = copy.deepcopy(self.stock)
        result = augment_setup_response(request, self.stock, 6100)
        self.assertFalse(result.augmented)
        self.assertEqual(result.response, original)
        self.assertIsNot(result.response, self.stock)

    def test_mixed_stream_preserves_stock_entries_and_unknown_fields(self):
        req_before, stock_before = copy.deepcopy(self.request), copy.deepcopy(self.stock)
        result = augment_setup_response(self.request, self.stock, 6101)
        self.assertTrue(result.augmented)
        self.assertEqual(result.stream_connection_id, 22)
        self.assertEqual(result.response["streams"][:2], stock_before["streams"])
        self.assertEqual(result.response["streams"][2], {
            "type": 111, "streamConnectionID": 22, "peerOpaque": [1, 2],
            "dataPort": 6101, "streamID": 111,
        })
        self.assertEqual(self.request, req_before)
        self.assertEqual(self.stock, stock_before)

    def test_111_first_last_only_and_multiple_stock_entries(self):
        for streams in (
            [{"type": 111, "streamConnectionID": 2}, {"type": 100}, {"type": 110}],
            [{"type": 100}, {"type": 110}, {"type": 111, "streamConnectionID": 2}],
            [{"type": 111, "streamConnectionID": 2}],
        ):
            with self.subTest(streams=streams):
                out = augment_setup_response({"streams": streams}, {"streams": [{"type": 100, "dataPort": 8}]}, 6123)
                self.assertEqual(out.response["streams"][0], {"type": 100, "dataPort": 8})
                self.assertEqual(out.response["streams"][-1]["streamID"], 111)

    def test_all_stock_types_100_101_110_and_order_are_preserved(self):
        stock_streams = [
            {"type": 100, "dataPort": 7100, "opaque": "audio"},
            {"type": 101, "dataPort": 7101, "opaque": "audio-alt"},
            {"type": 110, "dataPort": 7110, "opaque": "screen"},
        ]
        result = augment_setup_response(
            {"streams": [{"type": 100}, {"type": 101}, {"type": 110}, {"type": 111, "streamConnectionID": 99}]},
            {"streams": copy.deepcopy(stock_streams)},
            7199,
        )
        self.assertEqual(result.response["streams"][:3], stock_streams)
        self.assertEqual([e["type"] for e in result.response["streams"]], [100, 101, 110, 111])

    def test_no_stock_screen_or_empty_response_array_is_preserved_and_appendable(self):
        out = augment_setup_response({"streams": [{"type": 111, "streamConnectionID": 8}]}, {"opaque": True}, 6200)
        self.assertEqual(out.response, {"opaque": True, "streams": [{"type": 111, "streamConnectionID": 8, "dataPort": 6200, "streamID": 111}]})

    def test_duplicate_unknown_missing_and_bad_connection_ids_fail_closed(self):
        bad_requests = [
            {"streams": [{"type": 111, "streamConnectionID": 1}, {"type": 111, "streamConnectionID": 2}]},
            {"streams": [{"type": 999}, {"type": 111}]},
            {"streams": [{"type": 111, "streamConnectionID": True}]},
            {"streams": [{"type": 111, "streamConnectionID": 0}]},
            {"streams": [{"type": 111, "streamConnectionID": 1 << 64}]},
        ]
        for request in bad_requests:
            with self.subTest(request=request), self.assertRaises(SetupAugmentationError):
                augment_setup_response(request, self.stock, 6000)

    def test_malformed_containers_and_port_rejected_without_mutating_inputs(self):
        original = {"streams": [{"type": 111, "streamConnectionID": 4}]}
        before = copy.deepcopy(original)
        for response, port in (({"streams": None}, 6000), (self.stock, 0), (self.stock, True), (self.stock, 65536)):
            with self.subTest(response=response, port=port), self.assertRaises(SetupAugmentationError):
                augment_setup_response(original, response, port)
        self.assertEqual(original, before)

    def test_response_merge_failure_is_atomic(self):
        request = {"streams": [{"type": 111, "streamConnectionID": 5}]}
        stock = {"streams": "not-an-array"}
        with self.assertRaises(SetupAugmentationError):
            augment_setup_response(request, stock, 6000)
        self.assertEqual(stock, {"streams": "not-an-array"})


class StockFirstTransactionTests(unittest.TestCase):
    def test_stock_failure_never_prepares_project(self):
        calls = []
        result = run_stock_first_setup(
            {"streams": [{"type": 111, "streamConnectionID": 3}]},
            lambda req: (17, {"stock": "error"}),
            lambda cid: calls.append(("prepare", cid)) or 6000,
            lambda: calls.append(("rollback",)),
        )
        self.assertEqual(result.status, 17)
        self.assertEqual(calls, [])

    def test_success_calls_stock_first_then_appends_type111(self):
        calls = []
        request = {"streams": [{"type": 100}, {"type": 111, "streamConnectionID": 41, "opaque": "kept"}]}
        stock = {"streams": [{"type": 100, "dataPort": 7001}]}
        result = run_stock_first_setup(
            request,
            lambda req: calls.append(("stock", req is request)) or (0, stock),
            lambda cid: calls.append(("prepare", cid)) or 7002,
            lambda: calls.append(("rollback",)),
        )
        self.assertEqual(calls, [("stock", True), ("prepare", 41)])
        self.assertTrue(result.augmented)
        self.assertEqual(result.response["streams"][0], stock["streams"][0])
        self.assertEqual(result.response["streams"][1]["opaque"], "kept")

    def test_descriptor_without_type_is_ignored_as_non_type111(self):
        response = {"streams": [{"type": 100, "dataPort": 9}]}
        result = run_stock_first_setup(
            {"streams": [{"streamConnectionID": 5}]},
            lambda req: (0, response),
            lambda cid: self.fail("descriptor has no Type111 type"),
            lambda: self.fail("no project setup was started"),
        )
        self.assertEqual(result.response, response)
        self.assertFalse(result.augmented)

    def test_project_prepare_failure_returns_stock_response_unchanged(self):
        stock = {"streams": [{"type": 100, "dataPort": 71}]}
        calls = []
        result = run_stock_first_setup(
            {"streams": [{"type": 100}, {"type": 111, "streamConnectionID": 4}]},
            lambda req: (0, stock),
            lambda cid: (_ for _ in ()).throw(RuntimeError("synthetic setup failure")),
            lambda: calls.append("rollback"),
        )
        self.assertEqual(result.response, stock)
        self.assertFalse(result.augmented)
        self.assertEqual(calls, ["rollback"])

    def test_merge_failure_rolls_project_back(self):
        stock = {"streams": None}
        calls = []
        result = run_stock_first_setup(
            {"streams": [{"type": 111, "streamConnectionID": 9}]},
            lambda req: (0, stock), lambda cid: 6000, lambda: calls.append("rollback"),
        )
        self.assertEqual(result.response, stock)
        self.assertFalse(result.augmented)
        self.assertEqual(calls, ["rollback"])

    def test_unknown_stream_types_do_not_change_stock_only_response(self):
        response = {"streams": [{"type": 100, "dataPort": 1}]}
        result = run_stock_first_setup(
            {"streams": [{"type": 999}, {"type": 100}]},
            lambda req: (0, response), lambda cid: self.fail("no Type111 expected"), lambda: self.fail("no rollback expected"),
        )
        self.assertEqual(result.response, response)
        self.assertFalse(result.augmented)


class ScreenKDFTests(unittest.TestCase):
    def test_synthetic_derivation_matches_sha512_decimal_salt_contract(self):
        key, iv = derive_honda_type110_screen_key_iv(bytes(range(16)), 0x0102030405060708)
        self.assertEqual(key.hex(), "78056088f00400dd1b04ab5f436d4a22")
        self.assertEqual(iv.hex(), "e42baa157306a3b7435192ed159c80fc")

    def test_rejects_wrong_master_length_and_invalid_ids(self):
        for material, cid in ((b"short", 1), (bytes(16), 0), (bytes(16), -1), (bytes(16), 1 << 64), (bytes(16), True)):
            with self.subTest(material=material, cid=cid), self.assertRaises(ValueError):
                derive_honda_type110_screen_key_iv(material, cid)


class LifecycleTests(unittest.TestCase):
    def test_generation_replacement_and_teardown_are_deterministic(self):
        state = Type111Lifecycle()
        self.assertEqual(state.prepare(12, 6001), 1)
        state.mark_advertised()
        state.mark_active()
        self.assertEqual(state.state, State.ACTIVE)
        self.assertEqual(state.prepare(13, 6002), 2)
        self.assertEqual((state.stream_connection_id, state.data_port, state.state), (13, 6002, State.PREPARED))
        state.rollback()
        self.assertEqual((state.stream_connection_id, state.data_port, state.state), (None, None, State.IDLE))
        state.prepare(14, 6003)
        state.teardown()
        self.assertEqual((state.stream_connection_id, state.data_port, state.state), (None, None, State.CLOSED))

    def test_lifecycle_rejects_bad_identifiers_ports_and_transitions(self):
        state = Type111Lifecycle()
        for args in ((0, 1), (True, 1), (1, 0), (1, 65536)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                state.prepare(*args)
        with self.assertRaises(RuntimeError):
            state.mark_active()


if __name__ == "__main__":
    unittest.main()
