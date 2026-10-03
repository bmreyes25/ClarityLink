from pathlib import Path
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src/claritylink-negotiation"), str(ROOT / "src/claritylink-honda")]

import pytest
from prep2_cf_bridge import CFError, CFType, FakeCF, prepare_type111, commit_type111, finish_type111
from prep2_runtime import (
    AttachState, AttachmentModel, ExperimentState, NetworkEvidence, PolicyResult,
    PrefixClass, RestorationFacts, RollbackAttemptEvidence, RestoreState, STOCK_CALLSITE, SimMemory,
    NegotiationController, classify_type111_prefix, evaluate_binding, verify_restoration,
)


def restore_facts(**overrides):
    digest = hashlib.sha256(STOCK_CALLSITE).hexdigest()
    attempt = RollbackAttemptEvidence("RESTORED", 0x1000, 2, STOCK_CALLSITE, digest,
                                     STOCK_CALLSITE, 0x289F60)
    retry = RollbackAttemptEvidence("ALREADY_RESTORED", 0x1000, 2, STOCK_CALLSITE, digest,
                                    STOCK_CALLSITE, 0x289F60)
    facts = dict(callsite=STOCK_CALLSITE, surrounding_context_matches=True, bl_target=0x289F60,
                 continuation=0x28AFBE, generation_absent=True, listener_absent=True,
                 accepted_fd_absent=True, worker_absent=True, bridge_inactive=True,
                 expected_address=0x1000, observed_address=0x1000,
                 expected_alignment=2, observed_alignment=2,
                 expected_instruction_sequence=STOCK_CALLSITE,
                 observed_instruction_sequence=STOCK_CALLSITE,
                 expected_hash=digest, observed_hash=digest,
                 rollback_attempts=(attempt, retry), rollback_completed=True)
    facts.update(overrides)
    return RestorationFacts(**facts)


def stock_graph(runtime, entries=None):
    t110 = runtime.number(110)
    stock = runtime.dictionary({"type": t110})
    streams = runtime.array([stock] if entries is None else entries)
    response = runtime.dictionary({"streams": streams})
    runtime.release(t110); runtime.release(stock); runtime.release(streams)
    return response


@pytest.mark.parametrize("failure", [
    "number_create:2", "number_create:3", "dictionary_create:3", "array_create:2",
    "array_append:1", "array_append:2",
])
def test_cf_allocation_and_append_failures_are_atomic_and_leak_free(failure):
    rt = FakeCF()
    response = stock_graph(rt)
    rt.fail_at = failure
    old_ids = set(rt.objects)
    before = response.get("streams")
    with pytest.raises(CFError):
        prepare_type111(rt, response, 43000)
    assert response.get("streams") is before
    assert before.value[0].get("type").value == 110
    assert all(not obj.alive for key, obj in rt.objects.items() if key not in old_ids)


@pytest.mark.parametrize("port", [0, -1, 65536, True, "1234", None])
def test_cf_bad_ports_rejected(port):
    rt = FakeCF(); response = stock_graph(rt)
    with pytest.raises(CFError): prepare_type111(rt, response, port)


@pytest.mark.parametrize("shape", ["null", "wrong_response", "missing_streams", "wrong_streams"])
def test_cf_invalid_graphs_are_rejected(shape):
    rt = FakeCF()
    if shape == "null":
        with pytest.raises(CFError): prepare_type111(rt, None, 42000)
    elif shape == "wrong_response":
        with pytest.raises(CFError): prepare_type111(rt, rt.array(), 42000)
    elif shape == "missing_streams":
        with pytest.raises(CFError): prepare_type111(rt, rt.dictionary(), 42000)
    else:
        wrong = rt.number(4); response = rt.dictionary({"streams": wrong})
        with pytest.raises(CFError): prepare_type111(rt, response, 42000)


def test_cf_duplicate_type111_and_stream_limit_fail_closed():
    rt = FakeCF(); one = rt.number(111); d = rt.dictionary({"type": one})
    response = stock_graph(rt, [d])
    with pytest.raises(CFError, match="duplicate_type111"): prepare_type111(rt, response, 42000)
    many = [rt.dictionary() for _ in range(8)]
    full = stock_graph(rt, many)
    with pytest.raises(CFError, match="stream_limit"): prepare_type111(rt, full, 42000)


def test_cf_success_preserves_order_and_borrowed_objects_and_commit_rolls_back():
    rt = FakeCF(); response = stock_graph(rt)
    streams = response.get("streams"); stock_entry = streams.value[0]
    txn = prepare_type111(rt, response, 43123)
    assert response.get("streams") is streams
    commit_type111(txn)
    updated = response.get("streams")
    assert updated.value[0] is stock_entry
    assert updated.value[1].get("type").value == 111
    assert updated.value[1].get("dataPort").value == 43123
    assert stock_entry.get("type").value == 110
    finish_type111(rt, txn, serializer_ok=False)
    assert response.get("streams") is streams
    assert len(streams.value) == 1


def test_cf_commit_success_releases_project_temporaries_without_retaining_txn_graph():
    rt = FakeCF(); response = stock_graph(rt)
    txn = prepare_type111(rt, response, 43124); candidate_id = txn.candidate_array.identity
    commit_type111(txn); finish_type111(rt, txn, serializer_ok=True)
    assert response.get("streams").identity == candidate_id
    assert txn.finished and not txn.owns_entry and not txn.owns_array
    assert response.get("streams").value[1].get("dataPort").value == 43124


@pytest.mark.parametrize("failure", ["dictionary_set", "array_append:1"])
def test_cf_failures_do_not_partially_change_response(failure):
    rt = FakeCF(failure); response = stock_graph(rt); original = response.get("streams")
    if failure == "dictionary_set":
        txn = prepare_type111(rt, response, 43125)
        with pytest.raises(CFError): commit_type111(txn)
        finish_type111(rt, txn, serializer_ok=False)
    else:
        with pytest.raises(CFError): prepare_type111(rt, response, 43125)
    assert response.get("streams") is original


def test_cf_separate_transactions_have_no_shared_current_response_state():
    rt = FakeCF(); left, right = stock_graph(rt), stock_graph(rt)
    a, b = prepare_type111(rt, left, 43001), prepare_type111(rt, right, 43002)
    commit_type111(a); commit_type111(b)
    assert left.get("streams").value[1].get("dataPort").value == 43001
    assert right.get("streams").value[1].get("dataPort").value == 43002
    finish_type111(rt, a, serializer_ok=True); finish_type111(rt, b, serializer_ok=True)


def test_cf_unknown_stream_values_and_opaque_metadata_are_preserved_exactly():
    rt = FakeCF(); key = rt.string("opaque"); opaque = rt.string("keep")
    other = rt.dictionary({"vendor": opaque}); original = stock_graph(rt, [other])
    before = original.get("streams")
    txn = prepare_type111(rt, original, 43003); commit_type111(txn)
    candidate = original.get("streams")
    assert candidate.value[0] is other and other.get("vendor") is opaque
    assert candidate.value[1].get("type").value == 111
    finish_type111(rt, txn, serializer_ok=True)


def test_cf_response_changed_before_rollback_is_not_overwritten():
    rt = FakeCF(); response = stock_graph(rt); txn = prepare_type111(rt, response, 43004)
    commit_type111(txn)
    foreign = rt.array(); response.set("streams", foreign)
    with pytest.raises(CFError, match="response_changed_during_transaction"):
        finish_type111(rt, txn, serializer_ok=False)
    assert response.get("streams") is foreign and txn.finished


def test_cf_rollback_set_failure_is_reported_and_temp_ownership_is_released():
    rt = FakeCF(); response = stock_graph(rt); original = response.get("streams")
    txn = prepare_type111(rt, response, 43005); commit_type111(txn)
    candidate = txn.candidate_array
    rt.fail_at = "dictionary_set:2"  # commit succeeded; rollback replacement fails
    with pytest.raises(CFError, match="dictionary_set_failed"):
        finish_type111(rt, txn, serializer_ok=False)
    assert response.get("streams") is candidate
    assert txn.finished and not txn.owns_array and not txn.owns_entry and not txn.owns_original_streams
    assert txn.response is txn.original_streams is txn.candidate_array is txn.entry is None
    assert response.get("streams") is not original


def test_cf_release_runtime_detects_double_release_and_use_after_release():
    rt = FakeCF(); obj = rt.number(7); rt.release(obj)
    with pytest.raises(CFError, match="double_release"): rt.release(obj)
    with pytest.raises(CFError, match="use_after_release"): obj.get("x")


@pytest.mark.parametrize("mutation", [
    {"jmcs_sha256": "0" * 64}, {"architecture": ("ELF32", "ARM", "big-endian", "EABI5", "Thumb")},
    {"callsite": b"\xfe\xf7\xd1\x00"}, {"bl_target": 1},
    {"continuation": 2}, {"caller_context_sha256": "0" * 64},
    {"caller_prologue_sha256": "0" * 64},
])
def test_attachment_compatibility_gates_fail_without_write(mutation):
    model = AttachmentModel(**mutation)
    assert not model.attach()
    assert model.state is AttachState.ABORT_WITHOUT_WRITE
    assert model.memory.writes == 0


def test_attachment_compare_install_detach_and_second_detach():
    model = AttachmentModel()
    assert model.attach() and model.bounded_test()
    assert model.memory.writes == 1 and model.memory.cache_syncs == 1
    assert model.detach()
    assert bytes(model.memory.code) == STOCK_CALLSITE
    assert model.memory.writes == 2 and model.state is AttachState.RESTORATION_VERIFIED
    assert model.detach()


@pytest.mark.parametrize("fault", ["before_install", "make_writable", "install_verify", "restore_verify"])
def test_attachment_failure_is_not_misreported_as_restored(fault):
    model = AttachmentModel(memory=SimMemory(fail_at=fault))
    attached = model.attach()
    if fault == "before_install":
        assert not attached and model.memory.writes == 0
    elif fault == "install_verify":
        assert not attached and bytes(model.memory.code) == STOCK_CALLSITE
        assert model.state is AttachState.ATTACHMENT_FAILED
        assert model.detach() and model.memory.writes == 2
    else:
        if fault == "restore_verify":
            assert attached and not model.detach()
            assert model.state is not AttachState.RESTORATION_VERIFIED
        else:
            assert not attached


def test_attachment_protection_failure_preserves_failure_state():
    install = AttachmentModel(memory=SimMemory(fail_at="restore_protection"))
    assert not install.attach()
    assert install.state is AttachState.REBOOT_REQUIRED
    assert not install.memory.read_only
    assert not install.detach() and install.state is AttachState.REBOOT_REQUIRED
    active = AttachmentModel(); assert active.attach()
    active.memory.fail_at = "restore_protection"
    assert not active.detach()
    assert active.state is not AttachState.RESTORATION_VERIFIED
    assert not active.memory.read_only


def test_attachment_foreign_bytes_and_cleanup_failure_are_no_write_failures():
    model = AttachmentModel(); assert model.attach()
    model.memory.code[:] = b"foreign"
    writes = model.memory.writes
    assert not model.detach() and model.memory.writes == writes
    model2 = AttachmentModel(); assert model2.attach()
    model2.listener_active = model2.worker_active = True
    assert not model2.detach(cleanup_ok=False)
    assert model2.listener_active and model2.worker_active


def test_attachment_lease_expiry_detaches_ram_and_crash_paths_are_not_persistence_claims():
    before = AttachmentModel(); assert not before.lease_active and not before.memory.writes
    after = AttachmentModel(); assert after.attach()
    assert after.lease_expired() and bytes(after.memory.code) == STOCK_CALLSITE
    crash_after_activation = AttachmentModel(); assert crash_after_activation.attach()
    # Process loss is modeled as volatile memory loss, not a Honda reboot guarantee.
    crash_after_activation.memory.code[:] = STOCK_CALLSITE
    assert verify_restoration(restore_facts()) is RestoreState.RESTORED_TO_VERIFIED_STOCK


@pytest.mark.parametrize("state", [AttachState.ATTACHMENT_VERIFIED, AttachState.BOUNDED_TEST_ACTIVE,
                                    AttachState.DETACH_REQUESTED, AttachState.ORIGINAL_BYTES_RESTORED])
def test_attachment_transition_preconditions_and_exact_detach_gate(state):
    model = AttachmentModel(state=state)
    if state in (AttachState.ATTACHMENT_VERIFIED, AttachState.BOUNDED_TEST_ACTIVE):
        assert not model.detach()
        assert model.memory.writes == 0
    elif state is AttachState.ORIGINAL_BYTES_RESTORED:
        assert not model.detach()  # independent proof state is required for idempotent success


def test_attachment_duplicate_attach_and_detach_while_disabled():
    disabled = AttachmentModel(); assert disabled.detach() and disabled.memory.writes == 0
    active = AttachmentModel(); assert active.attach()
    previous_state = active.state
    assert not active.attach()
    assert active.state is previous_state
    assert active.memory.writes == 1


@pytest.mark.parametrize("failure", ["stop_type111_work", "retire_generation", "close_accepted_fd",
                                     "close_listener", "join_worker", "disable_bridge"])
def test_detach_failure_identifies_first_unreleased_resource(failure):
    model = AttachmentModel(); assert model.attach()
    model.type111_work_active = model.generation_active = model.accepted_fd_active = True
    model.listener_active = model.worker_active = model.bridge_active = True
    assert not model.detach(fail_at=failure)
    expected_operations = ["stop_type111_work", "retire_generation", "close_accepted_fd",
                           "close_listener", "join_worker", "disable_bridge"]
    idx = expected_operations.index(failure)
    assert model.cleanup_log == expected_operations[:idx]
    assert getattr(model, {
        "stop_type111_work": "type111_work_active", "retire_generation": "generation_active",
        "close_accepted_fd": "accepted_fd_active", "close_listener": "listener_active",
        "join_worker": "worker_active", "disable_bridge": "bridge_active",
    }[failure])


@pytest.mark.parametrize("overrides", [
    {"callsite": b"bad"}, {"surrounding_context_matches": False}, {"bl_target": 0},
    {"continuation": 0}, {"generation_absent": False}, {"listener_absent": False},
    {"accepted_fd_absent": False}, {"worker_absent": False}, {"bridge_inactive": False},
    {"observed_address": 0x1002}, {"observed_alignment": 4},
    {"observed_instruction_sequence": b"bad"}, {"observed_hash": "bad"},
    {"rollback_attempts": ()}, {"rollback_completed": False}, {"interrupted": True},
    {"fresh": False}, {"listener_absent": "false"}, {"generation_absent": "false"},
])
def test_independent_verifier_requires_every_fresh_fact(overrides):
    facts = restore_facts(**overrides)
    assert verify_restoration(facts) is RestoreState.RESTORATION_NOT_PROVEN


def test_independent_verifier_exact_stock_and_not_applicable():
    facts = restore_facts()
    assert verify_restoration(facts) is RestoreState.RESTORED_TO_VERIFIED_STOCK
    assert verify_restoration(RestorationFacts(None, False, None, None, False, False, False, False, False, applicable=False)) is RestoreState.NOT_APPLICABLE


def test_independent_verifier_accepts_only_explicit_final_readback_after_interruption():
    assert verify_restoration(restore_facts(interrupted=True, final_readback_after_interruption=True)) is RestoreState.RESTORED_TO_VERIFIED_STOCK
    facts = restore_facts()
    bad_retry = RollbackAttemptEvidence("RESTORED", 0x1000, 2, STOCK_CALLSITE,
        hashlib.sha256(STOCK_CALLSITE).hexdigest(), STOCK_CALLSITE, 0x289F60)
    assert verify_restoration(restore_facts(rollback_attempts=(facts.rollback_attempts[0], bad_retry))) is RestoreState.RESTORATION_NOT_PROVEN


def ev(**kw):
    base = dict(capture_classification="COMPLETE", candidate_interface="wlan0", candidate_address="192.0.2.8",
                address_family="IPv4", prefix=24, route_interface="wlan0", route_supported=True,
                phase_reversal_supported=True, evidence_class="HONDA_CONFIRMED")
    base.update(kw); return NetworkEvidence(**base)


def test_binding_policy_ipv4_global_ipv6_and_scoped_link_local():
    assert evaluate_binding(ev())[0] is PolicyResult.BIND_POLICY_READY
    global6 = ev(candidate_address="2001:db8::8", address_family="IPv6", prefix=64)
    assert evaluate_binding(global6)[0] is PolicyResult.BIND_POLICY_READY
    ll = ev(candidate_address="fe80::8", address_family="IPv6", prefix=64, scope_id="wlan0")
    assert evaluate_binding(ll)[0] is PolicyResult.BIND_POLICY_READY
    ll_index = ev(candidate_address="fe80::8", address_family="IPv6", prefix=64,
                  scope_id=4, interface_scope_id=4)
    assert evaluate_binding(ll_index)[0] is PolicyResult.BIND_POLICY_READY
    assert evaluate_binding(ev(candidate_address="fe80::8", address_family="IPv6", prefix=64,
                                scope_id=4, interface_scope_id=5))[0] is PolicyResult.BIND_POLICY_REJECTED
    assert evaluate_binding(ev(candidate_address="fe80::8", address_family="IPv6", prefix=64))[0] is PolicyResult.BIND_POLICY_REJECTED


@pytest.mark.parametrize("changes", [
    {"candidate_address": "0.0.0.0"}, {"candidate_address": "::"},
    {"candidate_address": "not-an-ip"}, {"candidate_address": "192.0.2.1", "prefix": 99},
    {"candidate_address": "224.0.0.1"}, {"candidate_address": "127.0.0.1"},
    {"candidate_address": "fe80::1%wlan0", "address_family": "IPv6", "prefix": 64},
    {"address_family": "IPv6"}, {"prefix": None},
    {"route_interface": "eth0"}, {"route_supported": False},
    {"phase_reversal_supported": False}, {"competing_candidates": 2},
    {"competing_candidates": True}, {"competing_candidates": -1}, {"prefix": True},
    {"route_supported": "true"}, {"candidate_interface": []},
    {"phase_reversal_supported": "yes"}, {"capture_classification": "CANDIDATE"},
    {"traffic_only": True}, {"wildcard_requested": True}, {"stale": True},
    {"capture_classification": "PARTIAL"}, {"evidence_class": "LAB_SYNTHETIC_CONFIRMED"},
])
def test_binding_policy_rejects_bad_or_unproven_evidence(changes):
    assert evaluate_binding(ev(**changes))[0] is PolicyResult.BIND_POLICY_REJECTED


def test_binding_placeholder_is_partial_and_does_not_make_listener_policy():
    assert evaluate_binding(NetworkEvidence())[0] is PolicyResult.BIND_POLICY_PARTIAL
    assert evaluate_binding(ev(candidate_address="FROM_43T0D_EVIDENCE"))[0] is PolicyResult.BIND_POLICY_PARTIAL
    assert evaluate_binding(ev(candidate_interface="UNKNOWN"))[0] is PolicyResult.BIND_POLICY_PARTIAL


def test_controller_requires_order_and_keeps_type110_out_of_scope():
    c = NegotiationController()
    for state in c.ORDER:
        if state is ExperimentState.PHONE_CONNECTED:
            c.record_phone_connection()
        if state is ExperimentState.FIRST_BYTES_CAPTURED:
            c.capture_first_bytes(b"synthetic-prefix")
        c.advance(state, local_serializer_ok=True if state is ExperimentState.LOCAL_SERIALIZER_SUCCESS else None)
    assert c.state is ExperimentState.COMPLETE
    assert not c.type110_owned and not c.type110_closed and not c.audio_changed and not c.center_display_changed


@pytest.mark.parametrize("bad", [ExperimentState.PHONE_CONNECTED, ExperimentState.FIRST_BYTES_CAPTURED,
                                  ExperimentState.LOCAL_SERIALIZER_SUCCESS])
def test_controller_rejects_skipped_evidence_levels(bad):
    c = NegotiationController()
    with pytest.raises(ValueError): c.advance(bad, local_serializer_ok=True)
    assert c.state is ExperimentState.FAILED


def test_controller_bounds_connections_prefix_and_duration():
    c = NegotiationController()
    c.state = ExperimentState.WAITING_FOR_PHONE_CONNECT
    with pytest.raises(ValueError, match="connection_attempt_limit_exceeded"):
        c.record_phone_connection(); c.record_phone_connection()
    c = NegotiationController(); c.state = ExperimentState.WAITING_FOR_PHONE_CONNECT
    with pytest.raises(ValueError, match="phone_connect_timeout_or_invalid_elapsed"):
        c.record_phone_connection(elapsed_seconds=c.MAX_ACCEPT_WAIT_SECONDS + 0.01)
    c = NegotiationController()
    for state in c.ORDER[:10]:
        if state is ExperimentState.PHONE_CONNECTED: c.record_phone_connection()
        if state is ExperimentState.LOCAL_SERIALIZER_SUCCESS: c.advance(state, local_serializer_ok=True); continue
        c.advance(state)
    with pytest.raises(ValueError, match="first_bytes_invalid_or_over_limit"):
        c.capture_first_bytes(bytes(c.MAX_FIRST_BYTES + 1))
    c = NegotiationController()
    for state in c.ORDER[:10]:
        if state is ExperimentState.PHONE_CONNECTED: c.record_phone_connection()
        if state is ExperimentState.LOCAL_SERIALIZER_SUCCESS: c.advance(state, local_serializer_ok=True); continue
        c.advance(state)
    with pytest.raises(ValueError, match="first_byte_timeout_or_invalid_elapsed"):
        c.capture_first_bytes(b"x", elapsed_seconds=c.MAX_FIRST_BYTE_WAIT_SECONDS + 0.01)
    c = NegotiationController(); c.advance(ExperimentState.STOCK_BASELINE_VERIFIED, elapsed_seconds=4.0)
    with pytest.raises(ValueError, match="experiment_deadline_exceeded"):
        c.advance(ExperimentState.ATTACHMENT_VERIFIED, elapsed_seconds=1.01)
    c = NegotiationController()
    with pytest.raises(ValueError, match="invalid_elapsed_time"):
        c.advance(ExperimentState.STOCK_BASELINE_VERIFIED, elapsed_seconds="five")


def test_controller_enforces_type110_invariant_and_no_crypto_fallback():
    c = NegotiationController(); c.type110_owned = True
    with pytest.raises(ValueError, match="type110_invariant_broken"):
        c.advance(ExperimentState.STOCK_BASELINE_VERIFIED)


def header(size=32, opcode=1):
    return size.to_bytes(4, "little") + bytes([opcode]) + bytes(123)


@pytest.mark.parametrize("data,expected", [
    (b"", PrefixClass.CLEAR_OR_UNKNOWN), (b"short", PrefixClass.CLEAR_OR_UNKNOWN),
    (header(), PrefixClass.CLEAR_OR_UNKNOWN), (header(0, 0), PrefixClass.MALFORMED),
    (header(32, 6), PrefixClass.UNSUPPORTED),
    ((0xFFFFFFFF).to_bytes(4, "little") + b"\x01" + bytes(251), PrefixClass.MALFORMED),
    (header() * 3, PrefixClass.MALFORMED), (bytes(128), PrefixClass.MALFORMED),
])
def test_prefix_unknown_malformed_truncated_and_oversized(data, expected):
    assert classify_type111_prefix(data).classification is expected


def test_prefix_known_provenance_fixtures_are_candidates_not_crypto_selection():
    legacy = classify_type111_prefix(header(), source_class="HONDA_TYPE110_FIXTURE")
    modern = classify_type111_prefix(header(), source_class="PLAYPORT_MODERN_FIXTURE")
    assert legacy.classification is PrefixClass.LEGACY_SCREENSTREAM_CANDIDATE
    assert modern.classification is PrefixClass.CLEAR_OR_UNKNOWN
    assert not legacy.crypto_branch_selected and not modern.crypto_branch_selected
    assert "header_not_crypto_discriminator" in modern.reasons


def test_prefix_deterministic_bounded_malformed_sweep():
    for n in range(0, 129):
        sample = bytes((i * 37 + n) & 255 for i in range(n))
        result = classify_type111_prefix(sample)
        assert result.bytes_observed_count <= 256
        assert not result.crypto_branch_selected


@pytest.mark.parametrize("limit", [0, -1, 257, 10**9, True, 1.5])
def test_prefix_capture_limit_cannot_be_increased(limit):
    assert classify_type111_prefix(header(), max_bytes=limit).classification is PrefixClass.UNSUPPORTED
