"""CL-T111-INGEST-01 failure / fail-safe / Type110-independence matrix.

Offline, synthetic, real receiver + real FFmpeg. Scope: SYNTHETIC lifecycle and
Type111 protocol handling of generated lab bytes only. No iPhone, Honda or
physical Display 1 evidence is established here.
"""
import os
import struct
import threading
import zlib

import pytest

import t111_synth as synth
from claritylink_jmcs.auth import UnavailableAuthenticationAuthority
from claritylink_jmcs.decoder import DecodedFrame, DecodeError, FFmpegDecoder
from claritylink_jmcs.display import DisplayError
from claritylink_jmcs.receiver import FaultInjector, ReceiverError, ReceiverState
from claritylink_jmcs.security import EvidenceRequiredSecurity, ModernChaChaScreenSecurity
from failsafe_coordinator import Fault, LeaseGrant, LinkState, SubmitResult
from type111_ingest import IngestError, Type111IngestPipeline, classify_receiver_code

start_type111 = synth.start_type111
TRANSPORT = Fault.TYPE111_TRANSPORT_FAILURE


@pytest.fixture(scope="module")
def stream():
    return synth.SyntheticStream(4)


@pytest.fixture
def clock():
    return synth.Clock()


@pytest.fixture
def make(clock):
    created = []

    def factory(**kwargs):
        receiver_kwargs = dict(synth.DIMENSIONS)
        receiver_kwargs.update(kwargs.pop("receiver_kwargs", {}))
        pipe = Type111IngestPipeline(lab_mode=True, clock=clock, receiver_kwargs=receiver_kwargs, **kwargs)
        created.append(pipe)
        return pipe

    yield factory
    for pipe in created:
        pipe.receiver.teardown(pipe.generation)


@pytest.fixture
def pipeline(make):
    return make()


def raw_header(size, opcode=0, timestamp=1):
    header = bytearray(128)
    header[:4] = size.to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = timestamp.to_bytes(8, "little")
    return bytes(header)


def show_first_frame(pipe, client, stream, index=0):
    client.sendall(stream.config_message() + stream.frame_message(index))
    assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
    assert pipe.host.visible_content is not None


def assert_withdrawn(pipe):
    assert pipe.host.visible_content is None
    assert pipe.host.residual_state == () and pipe.residual() == ()


# ---- fault classification ---------------------------------------------------
@pytest.mark.parametrize("code, kind", [
    ("media_eof", TRANSPORT), ("media_read_failed", TRANSPORT), ("invalid_body_length", TRANSPORT),
    ("invalid_avcc_nal_length", TRANSPORT), ("screen_authentication_failed", TRANSPORT),
    ("type111_security_evidence_required", TRANSPORT), ("lease_rejected:REJECTED_EPOCH", TRANSPORT),
    ("decode_failed", Fault.DECODER_DEATH), ("decoder_closed", Fault.DECODER_DEATH),
    ("invalid_decoded_dimensions", Fault.DECODER_DEATH),
    ("stale_secondary_decoder", None),  # the only error the receiver survives without tearing down
    ("stale_or_closed_session", TRANSPORT), ("stale_or_conflicting_stream_identity", TRANSPORT),
    ("never_seen_before", TRANSPORT),  # unknown errors fail closed, not open
])
def test_receiver_error_codes_map_to_the_intended_fault(code, kind):
    assert classify_receiver_code(code) is kind


# ---- frame handling ---------------------------------------------------------
@pytest.mark.parametrize("name, payload, close_after, code, kind, with_prior_frame", [
    ("oversized", lambda s: raw_header(8 * 1024 * 1024 + 1), False, "invalid_body_length", TRANSPORT, True),
    ("zero_length", lambda s: raw_header(0), False, "invalid_body_length", TRANSPORT, True),
    ("unknown_opcode", lambda s: raw_header(4, opcode=2) + b"abcd", False, "unsupported_screen_opcode", TRANSPORT, True),
    ("truncated_body", lambda s: raw_header(100) + b"x" * 10, True, "media_eof", TRANSPORT, True),
    ("bad_avcc_length", lambda s: synth.encode_lab_message(0, b"\x00\x00\x00\xff\x65", 9), False,
     "invalid_avcc_nal_length", TRANSPORT, True),
    ("missing_sps_pps", lambda s: s.frame_message(0), False, "decode_failed", Fault.DECODER_DEATH, False),
    ("garbage_nal", lambda s: synth.encode_lab_message(0, (9).to_bytes(4, "big") + b"\x1e" + bytes(range(8)), 9), False,
     "decode_failed", Fault.DECODER_DEATH, True),
    ("timestamp_regression", lambda s: s.frame_message(1, timestamp=0), False, "timestamp_regression", TRANSPORT, True),
])
def test_malformed_input_withdraws_content_and_releases_everything(pipeline, stream, name, payload, close_after,
                                                                   code, kind, with_prior_frame):
    client = start_type111(pipeline)
    if with_prior_frame:
        client.sendall(stream.config_message() + stream.frame_message(0, timestamp=5))
        assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
        assert pipeline.host.visible_content is not None
    client.sendall(payload(stream))
    if close_after:
        client.close()
    outcome = pipeline.pump_frame()
    client.close()
    assert (outcome.accepted, outcome.code, outcome.fault) == (False, code, kind)
    assert_withdrawn(pipeline)
    assert pipeline.coordinator.state is LinkState.CARPLAY_ACTIVE  # CarPlay itself is untouched
    assert pipeline.receiver.snapshot().secondary_listeners == 0


def test_decoder_returning_malformed_output_is_rejected_not_displayed(pipeline, stream, monkeypatch):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    generation = pipeline.receiver.stream_identity(111).stream_generation
    junk = DecodedFrame(b"\x89PNG\r\n\x1a\njunk", 2, generation, synth.WIDTH, synth.HEIGHT)
    monkeypatch.setattr(pipeline.receiver.decoder, "decode", lambda *a, **k: junk)
    client.sendall(stream.frame_message(1))
    outcome = pipeline.pump_frame()
    client.close()
    assert not outcome.accepted and outcome.code == "invalid_png" and outcome.fault is TRANSPORT
    assert_withdrawn(pipeline)


@pytest.mark.parametrize("make_frame, code", [
    (lambda g: DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT), 1, g + 1, synth.WIDTH, synth.HEIGHT),
     "stale_stream_generation"),
    (lambda g: DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT), 1, g, synth.WIDTH + 1, synth.HEIGHT),
     "decoder_dimension_mismatch"),
    (lambda g: DecodedFrame(b"not a png", 1, g, synth.WIDTH, synth.HEIGHT), "invalid_png"),
])
def test_sink_refuses_stale_mismatched_or_invalid_frames_and_fails_closed(pipeline, make_frame, code):
    pipeline.open_session()
    assert pipeline.setup_type111(12).accepted
    generation = pipeline.receiver.stream_identity(111).stream_generation
    good = DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT, (1, 2, 3)), 1, generation, synth.WIDTH, synth.HEIGHT)
    pipeline.output.show(good)  # positive control: content-agnostic, any valid pixels are accepted
    assert pipeline.host.visible_content.frame.pixel(0, 0) == (1, 2, 3)
    with pytest.raises(DisplayError, match=code):
        pipeline.output.show(make_frame(generation))
    assert pipeline.host.visible_content is None  # the rejection itself hid the old frame


def test_sink_never_accepts_frames_after_clear(pipeline):
    pipeline.open_session()
    assert pipeline.setup_type111(12).accepted
    generation = pipeline.receiver.stream_identity(111).stream_generation
    frame = DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT), 1, generation, synth.WIDTH, synth.HEIGHT)
    pipeline.output.clear()
    with pytest.raises(DisplayError, match="output_inactive"):
        pipeline.output.show(frame)
    assert pipeline.host.visible_content is None


def test_host_fences_reject_replayed_epoch_duplicate_sequence_and_superseded_generation(pipeline, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    old_lease, next_sequence, host = pipeline.coordinator.lease, pipeline.coordinator.sequence, pipeline.host
    assert host.submit(old_lease, next_sequence - 1, "duplicate") is SubmitResult.REJECTED_OUT_OF_ORDER
    assert host.submit(LeaseGrant(old_lease.epoch + 1, old_lease.generation), next_sequence, "x") \
        is SubmitResult.REJECTED_EPOCH
    pipeline.end_type111()
    client.close()
    assert pipeline.setup_type111(13).accepted
    assert pipeline.coordinator.lease.generation > old_lease.generation
    assert host.submit(old_lease, 0, "late") is SubmitResult.REJECTED_STALE_GENERATION
    assert host.visible_content is None  # nothing was ever shown for the new lease


def test_direct_enqueue_with_wrong_stream_identity_is_refused_by_the_receiver(pipeline, stream):
    """The refusal itself does not touch the lease; on the real pump path any such error
    tears the stream down, which is why it is classified as a fault (see classification)."""
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    identity = pipeline.receiver.stream_identity(111)
    forged = type(identity)(identity.session_generation, 111, identity.connection_id + 1,
                            identity.stream_generation, identity.output_id)
    frame = DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT), 9, identity.stream_generation,
                         synth.WIDTH, synth.HEIGHT)
    with pytest.raises(ReceiverError, match="stale_or_conflicting_stream_identity"):
        pipeline.receiver.enqueue_decoded_frame(forged, frame)
    assert pipeline.coordinator.lease is not None and pipeline.host.visible_content is not None
    client.close()


def test_backpressure_rejects_new_frames_and_keeps_the_queue_bounded(pipeline, stream):
    pipeline.open_session()
    assert pipeline.setup_type111(12).accepted
    receiver, identity = pipeline.receiver, pipeline.receiver.stream_identity(111)
    dispatcher = receiver.dispatch_registry.dispatcher(identity)

    class Gate:
        def __init__(self, inner):
            self.inner, self.entered, self.release = inner, threading.Event(), threading.Event()

        def show(self, frame):
            self.entered.set()
            assert self.release.wait(5)
            self.inner.show(frame)

        def clear(self):
            self.release.set()
            self.inner.clear()

    gate = Gate(pipeline.output)
    dispatcher.sink = gate
    decoder = FFmpegDecoder()
    frames = [decoder.decode(stream.annexb[i], i + 1, identity.stream_generation, (synth.WIDTH, synth.HEIGHT))
              for i in range(3)]
    first = receiver.enqueue_decoded_frame(identity, frames[0])
    assert gate.entered.wait(2)
    second = receiver.enqueue_decoded_frame(identity, frames[1])
    third = receiver.enqueue_decoded_frame(identity, frames[2])
    assert third.result(timeout=1) is False  # dropped, not queued without bound
    assert dispatcher.snapshot().outstanding_frames == 2 and dispatcher.snapshot().rejected == 1
    gate.release.set()
    assert first.result(timeout=5) and second.result(timeout=5)
    synth.assert_pixels_match(pipeline.host.visible_content.frame, 1)
    decoder.close()


# ---- session handling -------------------------------------------------------
def test_no_session_at_startup_refuses_type111_and_holds_nothing(pipeline):
    outcome = pipeline.setup_type111(12)
    assert (outcome.accepted, outcome.code, outcome.fault) == (False, "stale_or_closed_session", Fault.INIT_FAILURE)
    assert_withdrawn(pipeline)


@pytest.mark.parametrize("point", ["listener_bind", "security", "decoder", "response", "commit"])
def test_setup_interrupted_partway_releases_everything_acquired(make, point):
    pipe = make(receiver_kwargs={"faults": FaultInjector(point)})
    pipe.open_session()
    outcome = pipe.setup_type111(12)
    assert not outcome.accepted and outcome.fault is Fault.INIT_FAILURE
    assert_withdrawn(pipe)
    assert pipe.receiver.snapshot().secondary_listeners == 0 and pipe.receiver.snapshot().decoders == 0
    assert pipe.coordinator.lease is None


def test_grant_refused_by_host_releases_the_just_built_receiver_resources(pipeline):
    pipeline.open_session()
    pipeline.host.lose_display()
    outcome = pipeline.setup_type111(12)
    assert (outcome.accepted, outcome.code) == (False, "negotiation_refused")
    assert_withdrawn(pipeline)
    assert pipeline.receiver.secondary is None and pipeline.coordinator.lease is None


def test_duplicate_setup_cannot_disturb_a_live_stream(pipeline, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    outcome = pipeline.setup_type111(13)
    assert (outcome.accepted, outcome.code) == (False, "type111_already_active")
    assert pipeline.host.visible_content is not None and pipeline.receiver.secondary is not None
    client.close()


def test_setup_during_factory_interrupt_is_refused_and_clearing_it_never_reexposes(pipeline, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    pipeline.factory_interrupt()
    client.close()
    assert_withdrawn(pipeline)
    assert pipeline.setup_type111(13).code == "negotiation_refused"  # interrupt still active
    pipeline.clear_factory_interrupt()
    assert pipeline.host.visible_content is None  # cleared interrupt shows nothing by itself
    assert pipeline.setup_type111(14).accepted  # only a brand-new lease may show content again
    second = synth.connect(pipeline.receiver.secondary.port)
    pipeline.accept_type111()
    second.sendall(stream.config_message() + stream.frame_message(2))
    assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
    synth.assert_pixels_match(pipeline.host.visible_content.frame, 2)
    second.close()


def test_display_loss_withdraws_then_a_new_lease_recovers(pipeline, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    pipeline.display_restart()
    client.close()
    assert_withdrawn(pipeline)
    assert pipeline.setup_type111(13).accepted
    pipeline.receiver.teardown_secondary(pipeline.generation)


def test_rapid_disconnect_reconnect_cycles_do_not_accumulate_owners(pipeline, stream):
    baseline_threads, baseline_fds = threading.active_count(), len(os.listdir("/dev/fd"))
    for cycle in range(12):
        client = start_type111(pipeline)
        client.sendall(stream.config_message() + stream.frame_message(cycle % 4))
        assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
        pipeline.disconnect(Fault.CARPLAY_ENDED if cycle % 2 else Fault.USB_UNPLUG)
        client.close()
        assert_withdrawn(pipeline)
        assert pipeline.receiver.snapshot() == type(pipeline.receiver.snapshot())(0, 0, 0, 0, 0, 0, 0)
    assert threading.active_count() == baseline_threads
    assert len(os.listdir("/dev/fd")) == baseline_fds


# ---- fail-safe --------------------------------------------------------------
def test_expired_lease_is_hidden_by_the_host_alone_then_resources_follow_on_tick(pipeline, clock, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    clock.advance(1.5)  # past the 1.0s lease; no pipeline or receiver call is made
    assert pipeline.host.visible_content is None  # the host decided on its own
    assert pipeline.receiver.secondary is not None  # documented limit: our resources still held
    assert pipeline.tick() is True
    assert_withdrawn(pipeline)
    assert pipeline.faults[-1].kind is None and "expired" in pipeline.faults[-1].code
    assert pipeline.tick() is False  # idempotent
    client.close()


def test_heartbeats_cannot_keep_a_frozen_frame_visible(pipeline, clock, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    results = []
    for _ in range(4):
        clock.advance(0.5)
        results.append(pipeline.heartbeat())
    assert results == [True, True, True, False]
    assert pipeline.host.revocations[-1] == "no frame progress"
    assert_withdrawn(pipeline)
    client.close()


def test_cleanup_failure_cannot_block_revocation_or_the_other_cleanups(make, stream, monkeypatch):
    pipe = make()
    client = start_type111(pipe)
    show_first_frame(pipe, client, stream)
    seen = []
    real_teardown = pipe.receiver.teardown_secondary

    def spying_teardown(generation, **kwargs):
        seen.append(pipe.host.visible_content)  # content must already be gone when cleanup starts
        return real_teardown(generation, **kwargs)

    monkeypatch.setattr(pipe.receiver, "teardown_secondary", spying_teardown)

    def failing_close():
        raise RuntimeError("injected decoder close failure")

    monkeypatch.setattr(pipe.receiver.decoder, "close", failing_close)
    report = pipe.end_type111()
    client.close()
    assert seen and all(item is None for item in seen)
    assert "receiver_secondary" in report.failed and "output" in report.ran
    assert pipe.host.visible_content is None and pipe.coordinator.lease is None
    assert pipe.receiver.secondary is None and pipe.receiver.security is None  # the rest still released
    assert "decoder" in pipe.residual()  # honest: the failed close stays visible, not hidden
    assert pipe.cleanup_failures


def test_multiple_and_late_faults_are_idempotent_and_never_raise_the_link_state(pipeline, stream):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    pipeline.end_type111()
    pipeline.factory_interrupt()
    pipeline.disconnect(Fault.USB_UNPLUG)
    assert pipeline.coordinator.state is LinkState.FACTORY_ONLY
    pipeline.disconnect(Fault.CARPLAY_ENDED)  # a late, weaker fault
    pipeline.end_type111()
    assert pipeline.coordinator.state is LinkState.FACTORY_ONLY
    assert_withdrawn(pipeline)
    client.close()


def test_receiver_death_returns_to_factory_only_and_tears_the_session_down(pipeline, stream, monkeypatch):
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)

    def explode(generation):
        raise MemoryError("injected receiver failure")

    monkeypatch.setattr(pipeline.receiver, "receive_secondary_frame", explode)
    outcome = pipeline.pump_frame()
    client.close()
    assert (outcome.accepted, outcome.fault, outcome.code) == (
        False, Fault.RECEIVER_DEATH, "receiver_exception:MemoryError")  # cause stays diagnosable
    assert pipeline.coordinator.state is LinkState.FACTORY_ONLY
    assert_withdrawn(pipeline)
    assert pipeline.receiver.snapshot().sessions == 0


# ---- Type110 independence ---------------------------------------------------
def _crash_decoder(pipe, stream, client):
    def crash(*args, **kwargs):
        raise DecodeError("decode_failed")

    pipe.receiver.decoder.decode = crash
    client.sendall(stream.frame_message(1))
    assert pipe.pump_frame().fault is Fault.DECODER_DEATH


def _malformed(pipe, stream, client):
    client.sendall(raw_header(8 * 1024 * 1024 + 1))
    assert pipe.pump_frame().fault is TRANSPORT


def _expire(pipe, stream, client):
    pipe.host._clock.advance(1.5)
    assert pipe.tick()


def _normal_end(pipe, stream, client):
    assert not pipe.end_type111().failed


def _stale_callback(pipe, stream, client):
    identity = pipe.receiver.stream_identity(111)
    frame = DecodedFrame(synth.make_png(synth.WIDTH, synth.HEIGHT), 9, identity.stream_generation,
                         synth.WIDTH, synth.HEIGHT)
    pipe.end_type111()
    with pytest.raises(ReceiverError):
        pipe.receiver.enqueue_decoded_frame(identity, frame)
    with pytest.raises(ReceiverError, match="secondary_not_connected"):
        pipe.receiver.receive_secondary_frame(pipe.generation)


@pytest.mark.parametrize("scenario", [_crash_decoder, _malformed, _expire, _normal_end, _stale_callback])
def test_synthetic_type110_is_untouched_by_every_type111_failure(make, stream, scenario):
    pipe = make()
    client, primary = start_type111(pipe, with_primary=True)
    show_first_frame(pipe, client, stream)
    primary.sendall(stream.primary_message(0))
    pipe.receiver.receive_primary_frame(pipe.generation)
    held_frame, primary_decoder, primary_listener = pipe.primary_display.current, pipe.receiver.primary_decoder, \
        pipe.receiver.primary
    assert held_frame is not None

    scenario(pipe, stream, client)

    assert_withdrawn(pipe)
    assert pipe.primary_display.current is held_frame  # Type110 output was never cleared
    assert pipe.receiver.primary is primary_listener and pipe.receiver.primary_decoder is primary_decoder
    assert not primary_decoder.closed and pipe.receiver.state is ReceiverState.PRIMARY_ACTIVE
    primary.sendall(stream.primary_message(1))  # and it still decodes new Type110 frames
    assert pipe.receiver.receive_primary_frame(pipe.generation).startswith(b"\x89PNG")
    assert pipe.primary_display.current is not held_frame
    client.close()
    primary.close()


def test_type111_setup_failure_leaves_type110_established(make):
    pipe = make(receiver_kwargs={"faults": FaultInjector("decoder")})
    pipe.open_session()
    assert pipe.setup_primary(11)
    primary = synth.connect(pipe.receiver.primary.port)
    pipe.receiver.accept_primary(pipe.generation)
    outcome = pipe.setup_type111(12)
    assert (outcome.accepted, outcome.code, outcome.fault) == (False, "type111_setup_refused", Fault.INIT_FAILURE)
    assert pipe.receiver.primary is not None and not pipe.receiver.primary_decoder.closed
    assert_withdrawn(pipe)
    primary.close()


# ---- regression tests for ECC review findings ---------------------------------
def test_failed_full_teardown_is_reported_not_swallowed(make, stream, monkeypatch):
    pipe = make()
    client = start_type111(pipe)
    show_first_frame(pipe, client, stream)

    def failing_authority_close(session):
        raise RuntimeError("injected authority close failure")

    monkeypatch.setattr(pipe.receiver.authentication_authority, "close", failing_authority_close)
    pipe.disconnect(Fault.CARPLAY_ENDED)
    client.close()
    assert pipe.host.visible_content is None  # content is still withdrawn first
    assert pipe.faults[-1].cleanup_ok is False
    assert any(code.startswith("session_cleanup_incomplete") for code in pipe.cleanup_failures)
    assert "sessions" in pipe.session_residual() or "state_failed" in pipe.session_residual()


def test_display_that_cannot_clear_is_reported_as_uncleared(make, stream, monkeypatch):
    pipe = make()
    client = start_type111(pipe)
    show_first_frame(pipe, client, stream)

    def failing_clear():
        raise RuntimeError("injected display clear failure")

    monkeypatch.setattr(pipe.output, "clear", failing_clear)
    report = pipe.end_type111()
    client.close()
    assert pipe.host.visible_content is None  # fail_closed already hid it
    assert "receiver_secondary" in report.failed
    assert "display_uncleared" in pipe.residual() and pipe.faults[-1].cleanup_ok is False


def test_revocation_during_a_frame_defers_cleanup_off_the_worker_and_completes_it(pipeline, stream):
    """The host loses the lease while the coordinator still holds it: closers then run on the
    dispatcher worker (inside show), where joining itself is impossible, so cleanup is deferred."""
    client = start_type111(pipeline)
    show_first_frame(pipeline, client, stream)
    pipeline.host.activate_interrupt()  # host-side revoke the coordinator has not been told about
    client.sendall(stream.frame_message(1))
    outcome = pipeline.pump_frame()
    client.close()
    assert not outcome.accepted and outcome.code.startswith("lease_rejected") and outcome.fault is TRANSPORT
    assert pipeline.residual() == () and not pipeline._cleanup_deferred
    assert pipeline.cleanup_failures == [] and pipeline.receiver.snapshot().secondary_listeners == 0
    assert pipeline.coordinator.lease is None


def test_negotiation_refusal_with_failing_cleanup_is_recorded_and_does_not_raise(make, monkeypatch):
    pipe = make()
    pipe.open_session()
    pipe.host.lose_display()

    def failing_close(self):
        raise RuntimeError("injected decoder close failure")

    monkeypatch.setattr(FFmpegDecoder, "close", failing_close)
    outcome = pipe.setup_type111(12)
    assert (outcome.accepted, outcome.code) == (False, "negotiation_refused")
    assert pipe.faults[-1].code == "negotiation_refused" and pipe.faults[-1].cleanup_ok is False
    assert pipe.cleanup_failures
    monkeypatch.undo()
    pipe.receiver.teardown(pipe.generation)


def test_reserved_receiver_options_cannot_be_overridden(clock):
    for key in ("clear_lab", "display", "primary_display", "framing_profile"):
        with pytest.raises(IngestError, match="reserved_receiver_option"):
            Type111IngestPipeline(lab_mode=True, clock=clock, receiver_kwargs={key: object()})


# ---- authentication / security boundaries -----------------------------------
def test_authority_refusal_fails_closed_and_holds_nothing(make):
    pipe = make(receiver_kwargs={"authentication_authority": UnavailableAuthenticationAuthority()})
    with pytest.raises(ReceiverError):
        pipe.open_session()
    assert_withdrawn(pipe)
    assert pipe.coordinator.state is LinkState.FACTORY_ONLY and pipe.receiver.snapshot().sessions == 0


def test_production_style_security_provider_fails_closed_with_type110_preserved(make):
    pipe = make(receiver_kwargs={"security_factory": EvidenceRequiredSecurity})
    pipe.open_session()
    assert pipe.setup_primary(11)
    outcome = pipe.setup_type111(12)
    assert (outcome.accepted, outcome.fault) == (False, Fault.INIT_FAILURE)
    assert pipe.receiver.primary is not None
    assert_withdrawn(pipe)


def test_unknown_session_key_cannot_authenticate_frames(make, stream):
    pipe = make(receiver_kwargs={"security_factory": lambda: ModernChaChaScreenSecurity(
        os.urandom(32), provenance="generated test context")})
    client = start_type111(pipe)
    client.sendall(stream.config_message())
    assert pipe.pump_frame().accepted
    client.sendall(stream.frame_message(0))  # clear bytes where an AEAD tag is required
    outcome = pipe.pump_frame()
    client.close()
    assert outcome.code == "screen_authentication_failed" and outcome.fault is TRANSPORT
    assert_withdrawn(pipe)


@pytest.mark.parametrize("defect", ["noncontiguous_png_idat", "invalid_png_iend"])
def test_structurally_invalid_png_withdraws_previous_type111_content(pipeline, defect):
    pipeline.open_session()
    assert pipeline.setup_type111(12).accepted
    generation = pipeline.receiver.stream_identity(111).stream_generation
    good = synth.make_png(synth.WIDTH, synth.HEIGHT, (1, 2, 3))
    pipeline.output.show(DecodedFrame(good, 1, generation, synth.WIDTH, synth.HEIGHT))
    assert pipeline.host.visible_content is not None
    iend = good[-12:]
    body = good[:-12]
    if defect == "invalid_png_iend":
        bad = body + struct.pack(">I", 1) + b"IEND" + b"x" + struct.pack(">I", zlib.crc32(b"IENDx"))
    else:
        text = struct.pack(">I", 3) + b"tEXt" + b"k\x00v" + struct.pack(">I", zlib.crc32(b"tEXtk\x00v"))
        data = zlib.compress(b"".join(b"\x00" + bytes(synth.WIDTH * 3) for _ in range(synth.HEIGHT)))
        half = len(data) // 2
        def idat(part):
            return struct.pack(">I", len(part)) + b"IDAT" + part + struct.pack(">I", zlib.crc32(b"IDAT" + part))
        bad = good[:8 + 25] + idat(data[:half]) + text + idat(data[half:]) + iend
    with pytest.raises(DisplayError, match=defect):
        pipeline.output.show(DecodedFrame(bad, 2, generation, synth.WIDTH, synth.HEIGHT))
    assert pipeline.host.visible_content is None
