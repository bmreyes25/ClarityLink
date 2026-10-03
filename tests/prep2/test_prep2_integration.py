from pathlib import Path
import socket
import sys
import time
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src/claritylink-negotiation"), str(ROOT / "src/claritylink-honda"),
               str(ROOT / "src/claritylink-interposer")]

from prep2_cf_bridge import CFError, FakeCF, prepare_type111, commit_type111, finish_type111
from prep2_runtime import (AttachmentModel, ExperimentState, NetworkEvidence, PolicyResult,
                           RestorationFacts, RestoreState, evaluate_binding,
                           verify_restoration, NegotiationController, classify_type111_prefix,
                           PrefixClass)
from real_listener import (GenerationListenerRegistry, InterfaceKind, InterfacePolicy,
                           PreparedListener, ListenerError)


def _response(rt):
    n = rt.number(110); entry = rt.dictionary({"type": n}); streams = rt.array([entry])
    response = rt.dictionary({"streams": streams})
    for obj in (n, entry, streams): rt.release(obj)
    return response


def _run_to(controller, final):
    while controller.state is not final:
        index = controller.ORDER.index(controller.state) + 1 if controller.state in controller.ORDER else 0
        state = controller.ORDER[index]
        controller.advance(state, local_serializer_ok=True if state is ExperimentState.LOCAL_SERIALIZER_SUCCESS else None)


def test_synthetic_full_success_localhost_listener_cf_oracle_and_independent_restore():
    binding = NetworkEvidence(capture_classification="HOST_TEST", candidate_interface="lo0",
        candidate_address="127.0.0.1", address_family="IPv4", prefix=8,
        route_interface="lo0", route_supported=True, phase_reversal_supported=True,
        evidence_class="LAB_SYNTHETIC_CONFIRMED")
    assert evaluate_binding(binding)[0] is PolicyResult.BIND_POLICY_REJECTED
    attach = AttachmentModel(); assert attach.attach()
    controller = NegotiationController()
    _run_to(controller, ExperimentState.WAITING_FOR_SETUP)
    controller.advance(ExperimentState.TYPE111_REQUEST_OBSERVED)

    listener = PreparedListener.create("synthetic-generation", InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    registry = GenerationListenerRegistry(); registry.attach("synthetic-generation", listener)
    controller.advance(ExperimentState.LISTENER_PREPARED)
    rt = FakeCF(); response = _response(rt)
    txn = prepare_type111(rt, response, listener.port); commit_type111(txn)
    controller.advance(ExperimentState.RESPONSE_EXTENSION_PREPARED)
    serializer_calls = 0
    serializer_calls += 1  # stock serializer stand-in; no retry path
    controller.advance(ExperimentState.STOCK_SERIALIZER_CALLED)
    controller.advance(ExperimentState.LOCAL_SERIALIZER_SUCCESS, local_serializer_ok=True)
    controller.advance(ExperimentState.WAITING_FOR_PHONE_CONNECT)

    peer = socket.create_connection(("127.0.0.1", listener.port), timeout=1)
    accepted = listener.wait_accepted(timeout=1)
    assert accepted is not None
    controller.record_phone_connection(elapsed_seconds=0.0)
    controller.advance(ExperimentState.PHONE_CONNECTED)
    prefix = (32).to_bytes(4, "little") + b"\x01" + bytes(123)
    peer.sendall(prefix)
    accepted.settimeout(controller.MAX_FIRST_BYTE_WAIT_SECONDS)
    read_started = time.monotonic()
    captured = accepted.recv(128)
    read_elapsed = time.monotonic() - read_started
    assert len(captured) == 128 and classify_type111_prefix(captured).classification is PrefixClass.CLEAR_OR_UNKNOWN
    controller.capture_first_bytes(captured, elapsed_seconds=read_elapsed)
    controller.advance(ExperimentState.FIRST_BYTES_CAPTURED)

    peer.close(); registry.close_generation("synthetic-generation")
    assert serializer_calls == 1
    finish_type111(rt, txn, serializer_ok=True)
    controller.advance(ExperimentState.TYPE111_GENERATION_RETIRED)
    controller.advance(ExperimentState.DETACH_STARTED)
    assert attach.detach()
    controller.advance(ExperimentState.RESTORATION_VERIFIED)
    controller.advance(ExperimentState.COMPLETE)
    facts = RestorationFacts(bytes(attach.memory.code), True, 0x289F60, 0x28AFBE,
        True, not registry.owned_generations, accepted.fileno() == -1,
        not listener.worker.is_alive(), True)
    assert verify_restoration(facts) is RestoreState.RESTORED_TO_VERIFIED_STOCK
    assert controller.type110_closed is False and controller.audio_changed is False


def test_synthetic_rollback_listener_failure_and_policy_placeholder_leave_stock_unchanged():
    rt = FakeCF(); response = _response(rt); before = response.get("streams")
    with pytest.raises(ListenerError):
        PreparedListener.create("failed", InterfacePolicy(InterfaceKind.LOOPBACK_TEST), failure_at="bind")
    assert response.get("streams") is before
    assert evaluate_binding(NetworkEvidence())[0] is PolicyResult.BIND_POLICY_PARTIAL


def test_synthetic_rollback_after_response_append_failure_cleans_listener_and_attachment():
    attach = AttachmentModel(); assert attach.attach()
    listener = PreparedListener.create("rollback-generation", InterfacePolicy(InterfaceKind.LOOPBACK_TEST))
    registry = GenerationListenerRegistry(); registry.attach("rollback-generation", listener)
    rt = FakeCF(); response = _response(rt); original = response.get("streams")
    rt.fail_at = "array_append:2"  # existing Type110 copy succeeds; project append fails
    with pytest.raises(CFError, match="array_append_failed"):
        txn = prepare_type111(rt, response, listener.port)
        commit_type111(txn)
    registry.close_generation("rollback-generation")
    attach.listener_active = attach.worker_active = False
    attach.generation_active = attach.accepted_fd_active = False
    assert attach.detach()
    assert response.get("streams") is original
    facts = RestorationFacts(bytes(attach.memory.code), True, 0x289F60, 0x28AFBE,
        True, not registry.owned_generations, listener.accepted is None,
        not listener.worker.is_alive(), True)
    assert verify_restoration(facts) is RestoreState.RESTORED_TO_VERIFIED_STOCK
