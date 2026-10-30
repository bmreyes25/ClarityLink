"""CL-T111-INGEST-01 offline end-to-end: lab-framed Type111 H.264 -> real receiver
-> real FFmpeg decode -> lease-gated simulated Display 1 -> teardown.

Evidence scope: SYNTHETIC lifecycle + Type111 *protocol handling of generated
lab bytes*. NOT iPhone-origin video, NOT Honda receiver integration, NOT
physical Display 1 output. Inputs are SYNTHETIC_LAB_CONTENT from `t111_synth`.
"""
import pytest

import t111_synth as synth
from claritylink_jmcs.decoder import DecodedFrame
from claritylink_jmcs.display import DisplayError
from claritylink_jmcs.receiver import ReceiverError
from failsafe_coordinator import Fault, LinkState, SubmitResult
from type111_ingest import IngestError, LeaseBoundFrame, Type111IngestPipeline

DIMENSIONS = synth.DIMENSIONS
start_type111 = synth.start_type111


@pytest.fixture(scope="module")
def stream():
    return synth.SyntheticStream(4)


@pytest.fixture
def clock():
    return synth.Clock()


@pytest.fixture
def pipeline(clock):
    pipe = Type111IngestPipeline(lab_mode=True, clock=clock, receiver_kwargs=dict(DIMENSIONS))
    yield pipe
    pipe.receiver.teardown(pipe.generation)


def test_generated_type111_stream_reaches_simulated_display1_with_expected_pixels(pipeline, stream):
    client = start_type111(pipeline)
    try:
        client.sendall(stream.config_message())
        assert pipeline.pump_frame().accepted and pipeline.host.visible_content is None  # config only
        sequences = []
        for index in range(3):
            client.sendall(stream.frame_message(index))
            outcome = pipeline.pump_frame()
            assert outcome.accepted and outcome.fault is None
            held = pipeline.host.visible_content
            assert isinstance(held, LeaseBoundFrame) and held is outcome.frame
            synth.assert_pixels_match(held.frame, index)
            sequences.append(held.sequence)
            # every field the host-side frame is bound to
            assert held.frame.provenance.value == synth.PROVENANCE
            assert (held.frame.width, held.frame.height, held.frame.stride) == (synth.WIDTH, synth.HEIGHT, synth.WIDTH * 3)
            assert held.frame.timestamp == index + 1
            assert held.frame.session_generation == pipeline.generation
            assert held.frame.stream_type == 111 and held.frame.stream_connection_id == 12
            assert held.lease_epoch == pipeline.host.epoch
            assert held.lease_generation == pipeline.coordinator.lease.generation
        assert sequences == [0, 1, 2]
        assert pipeline.coordinator.state is LinkState.STREAMING
        assert pipeline.receiver.frames == 3
    finally:
        client.close()


def test_disconnect_withdraws_frame_and_releases_every_project_resource(pipeline, stream):
    client = start_type111(pipeline)
    client.sendall(stream.config_message())
    client.sendall(stream.frame_message(0))
    pipeline.pump_frame()
    outcome = pipeline.pump_frame()
    assert outcome.accepted and pipeline.host.visible_content is not None
    old_generation, old_identity = pipeline.generation, pipeline.receiver.stream_identity(111)
    stale_decoded = DecodedFrame(b"\x89PNG", 9, old_identity.stream_generation, synth.WIDTH, synth.HEIGHT)

    report = pipeline.disconnect(Fault.CARPLAY_ENDED)
    client.close()

    assert pipeline.host.visible_content is None and pipeline.host.residual_state == ()
    assert pipeline.residual() == () and not report.failed
    assert pipeline.coordinator.state is LinkState.PHONE_PRESENT
    snapshot = pipeline.receiver.snapshot()
    assert snapshot == type(snapshot)(0, 0, 0, 0, 0, 0, 0)
    # stale callbacks after teardown are all refused and never re-expose content
    with pytest.raises(ReceiverError, match="stale_or_closed_session"):
        pipeline.receiver.receive_secondary_frame(old_generation)
    with pytest.raises(DisplayError):
        pipeline.output.show(stale_decoded)
    assert pipeline.coordinator.submit_frame("late") is SubmitResult.REJECTED_NO_LEASE
    assert pipeline.host.visible_content is None


def test_reconnect_after_teardown_gets_a_fresh_lease_generation(pipeline, stream):
    first_client = start_type111(pipeline)
    first_client.sendall(stream.config_message() + stream.frame_message(0))
    assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
    first_lease = pipeline.coordinator.lease
    pipeline.disconnect(Fault.USB_UNPLUG)
    first_client.close()
    assert pipeline.coordinator.state is LinkState.FACTORY_ONLY

    second_client = start_type111(pipeline)
    try:
        assert pipeline.coordinator.lease.generation > first_lease.generation
        second_client.sendall(stream.config_message() + stream.frame_message(1))
        assert pipeline.pump_frame().accepted and pipeline.pump_frame().accepted
        synth.assert_pixels_match(pipeline.host.visible_content.frame, 1)
    finally:
        second_client.close()


def test_lab_mode_off_refuses_synthetic_session_and_shows_nothing(clock):
    pipe = Type111IngestPipeline(lab_mode=False, clock=clock, receiver_kwargs=dict(DIMENSIONS))
    with pytest.raises(IngestError, match="lab_mode_required"):
        pipe.open_session()
    assert pipe.host.visible_content is None and pipe.residual() == ()
    # the sink itself also refuses clear lab content outside lab mode
    with pytest.raises(DisplayError, match="lab_mode_required"):
        pipe.output.show(DecodedFrame(b"\x89PNG", 1, 1, 1, 1))
    assert pipe.host.visible_content is None
