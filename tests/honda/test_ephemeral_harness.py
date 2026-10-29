"""CL-T111-EPHEMERAL-HARNESS-01: offline cleanup/recovery state machine.

Evidence scope: SYNTHETIC/MODEL only. These tests run on the development host against the
existing CL-INT-04 stack. They prove nothing about a Honda, a target filesystem, a real reboot
or restoration; ``safe_for_honda`` stays False and deployment is not authorized.
"""
import copy
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "integration"))

import ephemeral_harness as eh  # noqa: E402
import t111_synth as synth  # noqa: E402
from display1_host_ipc import RemoteDisplay1Host  # noqa: E402
from type111_ingest import Type111IngestPipeline  # noqa: E402

F = eh.HarnessFault
S = eh.HarnessState
O = eh.ObligationStatus
WAIT = 8.0


def wait_for(predicate, timeout=WAIT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


@pytest.fixture
def harness():
    h = eh.EphemeralHarness()
    h.start()
    h.attach_producer()
    yield h
    assert h.close() is True


def assert_no_target_claims(outcome):
    claims = outcome.claims
    assert claims.honda_cleanup_established is False
    assert claims.ram_backed_target_storage_established is False
    assert claims.restoration_established is False
    assert claims.reboot_recovery_established is False
    assert claims.safe_for_honda is False
    assert claims.deployment_status == "VEHICLE_DEPLOYMENT_NOT_AUTHORIZED"
    assert outcome.evidence_label == "SYN"


def assert_host_clean(h):
    status = h.control.status()
    assert not status["lease_held"] and not status["visible"] and status["residual"] == 0
    assert not status["withdrawal_pending"]


# ---- manifest ----
def test_manifest_covers_every_resource_kind_and_labels_honda_properties_unknown():
    manifest = eh.load_manifest()
    for section in eh.SECTIONS:
        entries = manifest[section]
        assert entries, section
        assert any(e["scope"] == "HONDA_TARGET" for e in entries), section
    for _section, entry in eh._entries(manifest):
        if entry["honda_dependent"]:
            assert entry["status"] == "UNKNOWN" and entry["evidence"] == []
        else:
            assert entry["scope"] == "SYNTHETIC_HOST_MODEL" and entry["evidence"]


def test_manifest_separates_storage_classes_and_leaves_data_local_tmp_unestablished():
    manifest = eh.load_manifest()
    assert set(manifest["storage_classes"]) == set(eh.STORAGE_CLASSES)
    assert all(c["target_established"] is False for c in manifest["storage_classes"].values())
    unknown = {u["id"]: u for u in manifest["platform_unknowns"]}["data_local_tmp_reboot_volatility"]
    assert unknown["subject"] == "/data/local/tmp" and unknown["status"] == "UNKNOWN"
    assert "not established as reboot-volatile" in unknown["note"]
    assert all(v is False for v in manifest["claims"].values())
    assert manifest["safe_for_honda"] is False


@pytest.mark.parametrize("mutate", [
    lambda m: m["mounts"][1].update(status="ESTABLISHED"),
    lambda m: m["mounts"][1].update(status="MODELED_SYN", evidence=["README.md"]),
    lambda m: m["claims"].update(reboot_recovery_established=True),
    lambda m: m["platform_unknowns"][0].update(status="VOLATILE"),
    lambda m: m.update(safe_for_honda=True),
    lambda m: m["files"][0].update(evidence=["no/such/file.py"]),
    lambda m: m["storage_classes"]["RAM_BACKED_VOLATILE"].update(target_established=True),
    lambda m: m["mounts"][1].update(status="ESTABLISHED", evidence=["README.md"]),
    lambda m: m["mounts"][1].update(evidence=["README.md"]),
    lambda m: m["platform_unknowns"][1].update(status="ESTABLISHED"),
    lambda m: m["platform_unknowns"][0].update(evidence=["README.md"]),
])
def test_manifest_validator_rejects_promoting_a_honda_property(mutate):
    manifest = copy.deepcopy(eh.load_manifest())
    mutate(manifest)
    with pytest.raises(eh.ManifestError):
        eh.validate_manifest(manifest)


# ---- fault matrix ----
def test_normal_termination_cleans_the_model(harness):
    outcome = harness.inject(F.NORMAL_TERMINATION)
    assert outcome.clean and outcome.stale_lease_withdrawn is True
    assert all(s is O.CLEARED_MODEL for s in outcome.obligations.values())
    assert_host_clean(harness)
    assert not any(harness.path_of(k).exists() for k in eh._FILE_OBLIGATIONS)
    assert_no_target_claims(outcome)


def test_process_crash_is_withdrawn_by_the_host_not_by_producer_cleanup(harness):
    outcome = harness.inject(F.PROCESS_CRASH)
    assert outcome.clean and outcome.stale_lease_withdrawn is True
    assert "producer connection lost" in harness.control.status()["revocations"]
    assert_host_clean(harness)
    assert_no_target_claims(outcome)


def test_lost_producer_is_withdrawn_by_the_host_timer_alone(harness):
    outcome = harness.inject(F.LOST_PRODUCER)
    assert outcome.clean and outcome.stale_lease_withdrawn is True
    status = harness.control.status()
    assert "producer connection lost" not in status["revocations"]  # socket was still open when withdrawn
    assert status["watchdog_enforcements"] >= 1  # the timer, not a read, did the work
    assert any(r in ("lease expired", "no frame progress") for r in status["revocations"])
    assert_no_target_claims(outcome)


def test_lost_control_connection_is_unknown_never_clean_until_reobserved(harness):
    outcome = harness.inject(F.LOST_CONTROL_CONNECTION)
    assert outcome.state is S.CLEANUP_INCOMPLETE and not outcome.clean
    assert outcome.obligations["display1_lease_withdrawn"] is O.UNKNOWN
    assert outcome.stale_lease_withdrawn is None  # unobservable is not "withdrawn"
    assert harness.recover().state is S.CLEANUP_INCOMPLETE  # still unobservable: still unknown
    harness.reconnect_control()
    final = harness.recover()
    assert final.clean and final.stale_lease_withdrawn is True
    assert_host_clean(harness)


def test_interrupted_cleanup_resumes_and_is_idempotent(harness):
    outcome = harness.inject(F.INTERRUPTED_CLEANUP)
    assert outcome.state is S.CLEANUP_INCOMPLETE
    assert outcome.obligations["producer_connection_closed"] is O.CLEARED_MODEL
    assert outcome.obligations["display1_lease_withdrawn"] is O.PENDING
    assert harness.path_of("persistent_marker_removed").exists()  # nothing claimed removed yet
    resumed = harness.recover()
    assert resumed.clean and resumed.stale_lease_withdrawn is True
    assert harness.state is S.CLEAN_MODEL
    assert not any(harness.path_of(k).exists() for k in eh._FILE_OBLIGATIONS)


def test_host_restart_fences_the_previous_boots_lease_by_epoch(harness):
    first_epoch = harness.control.epoch
    outcome = harness.inject(F.HOST_RESTART)
    assert outcome.clean and outcome.stale_lease_fenced is True
    assert harness.control.epoch != first_epoch and harness.boots == 2
    assert_host_clean(harness)
    assert_no_target_claims(outcome)


def test_epoch_fence_is_only_observable_while_the_new_boot_holds_a_lease(harness):
    # Regression: a lease-less new boot answers NO_LEASE before it compares epochs, so a naive
    # post-restart submit never exercised the epoch fence. The probe must grant, check, then revoke.
    stale = harness.producer.lease
    harness.inject(F.HOST_RESTART)
    assert harness.host.submit(stale, eh.LATE_SEQUENCE, "late") is eh.fsc.SubmitResult.REJECTED_NO_LEASE
    assert harness._probe_epoch_fence(stale) is True
    assert harness.host.submit(stale, eh.LATE_SEQUENCE, "late") is eh.fsc.SubmitResult.REJECTED_NO_LEASE
    assert_host_clean(harness)


def test_missing_cleanup_resource_is_unknown_not_clean(harness):
    outcome = harness.inject(F.MISSING_CLEANUP_RESOURCE)
    assert outcome.state is S.CLEANUP_INCOMPLETE and not outcome.clean
    assert outcome.obligations["persistent_marker_removed"] is O.UNKNOWN
    assert any("resource missing" in d for d in outcome.detail)
    assert harness.recover().obligations["persistent_marker_removed"] is O.UNKNOWN  # never self-heals
    assert harness.state is S.CLEANUP_INCOMPLETE


def test_withdrawal_failures_are_reported_and_retried_until_the_host_is_clean():
    h = eh.EphemeralHarness(inject_withdraw_failures=3)
    h.start()
    h.attach_producer()
    try:
        outcome = h.inject(F.PROCESS_CRASH)
        assert outcome.clean and outcome.stale_lease_withdrawn is True
        assert h.control.status()["withdrawal_failure_count"] >= 3
        assert_host_clean(h)
    finally:
        assert h.close() is True


def test_unreachable_host_is_unknown_not_withdrawn():
    h = eh.EphemeralHarness(cleanup_bound=0.2)
    h.start()
    h.attach_producer()
    try:
        h._boot.server.stop()  # the host itself disappears under the harness
        outcome = h.inject(F.PROCESS_CRASH)
        assert outcome.obligations["display1_lease_withdrawn"] is O.UNKNOWN
        assert outcome.stale_lease_withdrawn is None and not outcome.clean
    finally:
        h.close()


# ---- simulated reboot: model only ----
def test_simulated_reboot_wipes_only_the_modelled_volatile_dir_and_keeps_the_rest(harness):
    outcome = harness.inject(F.SIMULATED_REBOOT, max_steps=2)  # stop before file cleanup
    assert outcome.state is S.CLEANUP_INCOMPLETE
    assert not harness.path_of("volatile_marker_removed").exists()  # model wiped it
    assert harness.path_of("persistent_marker_removed").exists()  # persistent survives
    assert harness.path_of("unknown_class_marker_removed").exists()  # unknown treated as persistent
    assert outcome.stale_lease_fenced is True
    final = harness.recover()
    assert final.clean
    assert not any(harness.path_of(k).exists() for k in eh._FILE_OBLIGATIONS)


@pytest.mark.parametrize("fault", list(F))
def test_no_fault_outcome_ever_establishes_a_target_claim(fault):
    h = eh.EphemeralHarness(cleanup_bound=0.5)
    h.start()
    h.attach_producer()
    try:
        outcome = h.inject(fault)
        assert_no_target_claims(outcome)
        assert outcome.claims == eh.NO_TARGET_CLAIMS
    finally:
        h.close()


def test_simulated_reboot_cannot_establish_honda_cleanup_ram_storage_restoration_or_recovery(harness):
    outcome = harness.inject(F.SIMULATED_REBOOT)
    assert outcome.clean  # clean in the MODEL, and only there
    assert outcome.state is S.CLEAN_MODEL  # not a target-clean state name
    assert_no_target_claims(outcome)
    assert any("model assumption" in d and "no target behavior observed" in d for d in outcome.detail)
    manifest = harness.manifest
    assert manifest["claims"]["reboot_recovery_established"] is False
    assert manifest["claims"]["ram_backed_target_storage_established"] is False
    assert manifest["claims"]["data_local_tmp_reboot_volatile_established"] is False
    assert all(c["target_established"] is False for c in manifest["storage_classes"].values())
    with pytest.raises(AttributeError):
        outcome.claims.reboot_recovery_established = True  # frozen: cannot be promoted


# ---- state machine guards ----
def test_illegal_operations_are_refused(harness):
    with pytest.raises(eh.HarnessStateError):
        harness.recover()  # nothing faulted
    with pytest.raises(eh.HarnessStateError):
        harness.attach_producer()  # already attached
    harness.inject(F.NORMAL_TERMINATION)
    with pytest.raises(eh.HarnessStateError):
        harness.inject(F.PROCESS_CRASH)  # CLEAN_MODEL must return to ACTIVE first
    fresh = eh.EphemeralHarness()
    with pytest.raises(eh.HarnessStateError):
        fresh.attach_producer()


# ---- stale lease withdrawal and Type110 independence through the existing CL-INT-04 pipeline ----
def test_stale_display1_lease_is_withdrawn_and_type110_state_stays_independent():
    stream = synth.SyntheticStream(4)
    h = eh.EphemeralHarness(lab_controls=True)
    h.start()
    remote = RemoteDisplay1Host(h.socket_path)
    pipe = Type111IngestPipeline(lab_mode=True, host=remote, receiver_kwargs=dict(synth.DIMENSIONS))
    client = primary = None
    try:
        client, primary = synth.start_type111(pipe, with_primary=True)
        primary.sendall(stream.primary_message(0))
        pipe.receiver.receive_primary_frame(pipe.generation)
        held, decoder = pipe.primary_display.current, pipe.receiver.primary_decoder
        client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
        assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
        assert h.control.status()["visible"] is True
        h.clock.advance(h.lease_seconds * eh.LEASE_EXPIRY_MULTIPLE)  # the producer goes silent
        h._boot.service.poke()
        assert wait_for(lambda: h.control.status()["visible"] is False)  # host withdrew alone
        assert pipe.tick() is True  # the producer adopts what the host already did
        assert pipe.primary_display.current is held and not decoder.closed  # Type110 untouched
        primary.sendall(stream.primary_message(1))
        assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
        assert pipe.residual() == ()
        assert_host_clean(h)
    finally:
        for sock in (client, primary):
            if sock is not None:
                sock.close()
        pipe.receiver.teardown(pipe.generation)
        remote.close()
        assert h.close() is True
