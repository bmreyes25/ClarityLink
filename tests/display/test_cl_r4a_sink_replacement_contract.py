from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "android/cl-imp-03-app/java/org/claritylink/android"


def test_sink_replacement_is_version3_owner_authorized_and_identity_checked():
    protocol = (APP / "FrameIpcProtocol.java").read_text()
    client = (APP / "FrameIpcClient.java").read_text()
    service = (APP / "CompositorService.java").read_text()

    assert "static final int VERSION = 3;" in protocol
    assert "TYPE111_REPLACE_SINK = 25" in protocol
    assert "FrameIpcProtocol.TYPE111_REPLACE_SINK" in client
    assert "type110Owner.streamType != FrameStreamIdentity.TYPE110" in client
    assert "oldIdentity.streamType != FrameStreamIdentity.TYPE111" in service
    assert "oldIdentity.sameStream(newIdentity)" in service
    assert "oldIdentity.sessionId != ownerIdentity.sessionId" in service
    assert "newIdentity.streamGeneration != oldIdentity.streamGeneration + 1L" in service
    assert "ownerIdentity.equals(owner.identity)" in service
    assert "plane.canTransportGeneration(oldIdentity, newIdentity)" in service
    assert "!state.transferActive.get()" in service


def test_death_and_end_callbacks_are_fenced_to_the_registered_generation():
    service = (APP / "CompositorService.java").read_text()

    assert "createSinkDeathRecipient(state, identity, sink, null)" in service
    assert "state, newIdentity, newSink, deathGate" in service
    assert "deadIdentity = state.sink == registeredSink ? state.identity : registeredIdentity;" in service
    assert "streams.get(identity.key()) != state || !identity.equals(state.identity)" in service
    assert "detachType111SinkIfCurrent(state, deadIdentity)" in service
    assert "parent_session_preserved=true" in service


def test_pipe_and_worker_start_failures_release_owned_resources():
    service = (APP / "CompositorService.java").read_text()
    client = (APP / "FrameIpcClient.java").read_text()

    assert "boolean writerStarted = false;" in service
    assert "if (!writerStarted) try { pipe[1].close();" in service
    assert "catch (RuntimeException startFailure)" in client
    assert "catch (OutOfMemoryError startFailure)" in client
    assert client.count("frameGate.release();") >= 3
    forwarder = service[service.index("private boolean forwardToViewSink"):]
    assert "if (pipe != null && !writerStarted)" in forwarder
    assert "state.activePfdTransfers.decrementAndGet();" in forwarder


def test_failed_replacement_unlinks_candidate_and_rolls_back_generation():
    service = (APP / "CompositorService.java").read_text()

    assert "if (!accepted) {" in service
    assert "newSink.unlinkToDeath(newRecipient, 0)" in service
    assert "ReplacementDeathGate deathGate = new ReplacementDeathGate();" in service
    assert "if (!deathGate.dead && stillCurrent" in service
    assert "state.compositor.end(newIdentity.streamGeneration);" in service
