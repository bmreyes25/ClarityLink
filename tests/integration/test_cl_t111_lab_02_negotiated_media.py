"""Negotiated Type111 child -> existing real host lab receiver/FFmpeg/display.

Only generated SYNTHETIC_LAB_CONTENT is sent over loopback. This is not Honda,
iPhone, wire-compatibility or Android API17 acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import threading

import pytest

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "src/claritylink-jmcs", ROOT / "src/claritylink-negotiation",
             ROOT / "src/claritylink-transport", ROOT / "src/carplay-session-model",
             ROOT / "src/claritylink-honda", ROOT / "tests/integration"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import t111_synth as synth
from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.display import NullDisplay
from claritylink_jmcs.lab_dual_display import InfoPolicy, LabDualDisplayModel, SyntheticReadiness
from claritylink_jmcs.lab_media_coordinator import (
    LabMediaError, NegotiatedType111MediaSession, SetupOrder,
)
from claritylink_jmcs.receiver import FaultInjector, ReceiverState
from claritylink_jmcs.setup import serialize_lab_plist
from claritylink_jmcs.stock_delegation import MockStockPrimarySession, StockFirstType111Delegator
from type111_ingest import Type111IngestPipeline
from type111_setup_contract import (
    DeterministicListenerAllocator, SerializerResult, Type111SetupContract,
)
from dual_screen_lifecycle import DualScreenLifecycleTwin
from legacy_dual_screen_twin import LegacyDualScreenTwin, ScreenRole


STOCK_INFO = {
    "sourceVersion": "synthetic-fixture",
    "features": 17,
    "displays": [{"type": 110, "uuid": "b7e6c5a0-1111-4000-8000-000000000001", "features": 10}],
}
STOCK_SETUP = {
    "streams": [{"type": 110, "dataPort": 41001, "opaque": {"factory": True}}],
    "audio": {"owner": "mock-Type110", "unchanged": True},
}
PRIMARY_ID = 1101
SECONDARY_ID = 2201


class Lab:
    def __init__(self, *, parent_generation: int = 41, faults: FaultInjector | None = None,
                 clock=None, lease_seconds: float = 300.0):
        twin = LegacyDualScreenTwin(
            bytes(16), encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter))
        )
        twin.add_screen(ScreenRole.TYPE110, PRIMARY_ID)
        lifecycle = DualScreenLifecycleTwin(twin)
        secondary = Type111SetupContract(lifecycle, DeterministicListenerAllocator())
        self.primary = MockStockPrimarySession(STOCK_SETUP)
        model = LabDualDisplayModel(
            StockFirstType111Delegator(self.primary, secondary), STOCK_INFO, STOCK_SETUP,
            secondary_capability=SecondaryDisplayCapability.synthetic_lab(
                main_uuid="b7e6c5a0-1111-4000-8000-000000000001",
                secondary_uuid="b7e6c5a0-2222-4000-8000-000000000002"),
            readiness=SyntheticReadiness(True, True, True),
        )
        kwargs = dict(synth.DIMENSIONS)
        if faults is not None:
            kwargs["faults"] = faults
        self.display0 = NullDisplay()
        self.pipeline = Type111IngestPipeline(
            lab_mode=True, receiver_kwargs=kwargs, primary_display=self.display0,
            **({"clock": clock, "lease_seconds": lease_seconds} if clock is not None else {}),
        )
        self.session = NegotiatedType111MediaSession(model, self.pipeline)
        self.parent = object()
        self.parent_generation = parent_generation
        self.info = None
        self.observed_child_resources = []

    def open(self, policy=InfoPolicy.MODEL_ONLY):
        self.info = self.session.open(self.parent, self.parent_generation, info_policy=policy)
        return self.info

    def serialize(self, fields, *, fail=False):
        self.serialized.append(deepcopy(dict(fields)))
        owner = self.session._child_lease
        if owner is not None and owner not in self.observed_child_resources:
            self.observed_child_resources.append(owner)
        serialize_lab_plist(fields)
        return SerializerResult(500 if fail else 0xC8, 1 if fail else 0)

    @property
    def serialized(self):
        if not hasattr(self, "_serialized"):
            self._serialized = []
        return self._serialized

    def setup(self, *, primary=True, secondary=True,
              order=SetupOrder.TYPE110_FIRST, fail_serializer=False):
        streams = []
        if order is SetupOrder.TYPE110_FIRST:
            if primary:
                streams.append({"type": 110, "streamConnectionID": PRIMARY_ID})
            if secondary:
                streams.append({"type": 111, "streamConnectionID": SECONDARY_ID})
        else:
            if secondary:
                streams.append({"type": 111, "streamConnectionID": SECONDARY_ID})
            if primary:
                streams.append({"type": 110, "streamConnectionID": PRIMARY_ID})
        return self.session.setup(
            {"streams": streams},
            lambda fields: self.serialize(fields, fail=fail_serializer),
            order=order,
        )

    def connect_primary(self):
        client = synth.connect(self.pipeline.receiver.primary.port)
        self.session.accept_primary()
        return client

    def connect_secondary(self, stream_id=SECONDARY_ID):
        client = synth.connect(self.pipeline.receiver.secondary.port)
        self.session.accept_type111(self.parent, self.parent_generation, stream_id)
        return client

    def close(self):
        if self.session.active:
            self.session.close_parent(self.parent, self.parent_generation)


@pytest.fixture
def stream():
    return synth.SyntheticStream(4)


def test_type110_only_startup_uses_factory_owner_and_never_allocates_type111(stream):
    lab = Lab()
    try:
        info = lab.open(InfoPolicy.DISABLED)
        result = lab.setup(secondary=False)
        assert not info.type111_candidate_present
        assert result.type110_ready and not result.type111_ready
        assert result.model_setup.response == STOCK_SETUP
        assert lab.pipeline.receiver.state is ReceiverState.PRIMARY_ACTIVE
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.primary.setup_calls == 1 and lab.session.identity is None
        client = lab.connect_primary()
        client.sendall(stream.primary_message(0))
        lab.session.pump_primary()
        assert lab.display0.current is not None
        assert lab.pipeline.host.visible_content is None
    finally:
        lab.close()


@pytest.mark.parametrize("order", [SetupOrder.TYPE110_FIRST, SetupOrder.TYPE111_FIRST])
def test_negotiated_child_drives_existing_receiver_ffmpeg_and_independent_sinks(order, stream):
    lab = Lab()
    clients = []
    try:
        info = lab.open()
        assert info.type111_candidate_present
        result = lab.setup(order=order)
        assert result.type110_ready and result.type111_ready and result.error_code is None
        binding = result.identity
        assert binding == lab.session.identity
        assert (binding.parent_identity is lab.parent and
                binding.parent_generation == lab.parent_generation and
                binding.stream_connection_id == SECONDARY_ID)
        assert binding.receiver_session_generation == lab.pipeline.generation
        assert binding.receiver_stream_generation == lab.pipeline.receiver.stream_identity(111).stream_generation
        assert binding.child_generation == lab.session.model.delegator.secondary.lifecycle.current_type111.generation
        assert lab.pipeline.receiver.secondary is not None
        assert lab.pipeline.receiver.decoder is not None
        assert lab.pipeline.coordinator.lease is not None
        assert lab.primary.setup_calls == 1
        assert result.model_setup.response["streams"][0] == STOCK_SETUP["streams"][0]
        assert result.model_setup.response["streams"][1]["type"] == 111
        # The negotiation allocator's model port and the OS listener are distinct owners.
        model_reservation = lab.session.model.delegator.secondary.listeners.reservations[0]
        assert not hasattr(model_reservation, "sock")
        assert hasattr(lab.pipeline.receiver.secondary, "sock")

        clients.append(lab.connect_primary())
        clients.append(lab.connect_secondary())
        clients[0].sendall(stream.primary_message(0))
        primary_png = lab.session.pump_primary()
        assert lab.display0.current is not None and lab.display0.current.png == primary_png

        clients[1].sendall(stream.config_message())
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        assert lab.pipeline.host.visible_content is None
        clients[1].sendall(stream.frame_message(2))
        outcome = lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert outcome.accepted and outcome.frame is not None
        held = lab.pipeline.host.visible_content
        assert held is outcome.frame
        synth.assert_pixels_match(held.frame, 2)
        assert (held.frame.width, held.frame.height, held.frame.stream_type,
                held.frame.stream_connection_id) == (synth.WIDTH, synth.HEIGHT, 111, SECONDARY_ID)
        assert held.frame.provenance.value == synth.PROVENANCE
        assert lab.pipeline.receiver.stream_identity(110).connection_id == PRIMARY_ID
        mapped = lab.session.identity
        assert mapped.decoder_generation.receiver_session_generation == lab.pipeline.generation
        assert mapped.decoder_generation.restart_ordinal == lab.pipeline.receiver.secondary_decoder_generation == 0
        assert mapped.display_lease_epoch == held.lease_epoch
        assert mapped.display_lease_generation == held.lease_generation
        assert mapped.receiver_stream_generation != 0
        assert lab.pipeline.receiver.primary is not None
        assert lab.pipeline.receiver.primary_decoder is not None
        child = lab.session.model.delegator.secondary.lifecycle.current_type111
        child_state = child._owner._registry.child(child.key)
        assert child_state is not None
        assert lab.session._child_lease in child_state.resources
        assert lab.pipeline.receiver.primary_security is not lab.pipeline.receiver.security
        assert lab.pipeline.receiver.primary_decoder is not lab.pipeline.receiver.decoder
        assert lab.display0 is not lab.pipeline.host
        active_residues = set(lab.session.residual())
        assert {"host:LeaseGrant", "listener", "decoder", "security", "display_frame"} <= active_residues
    finally:
        for client in clients:
            client.close()
        lab.close()


@pytest.mark.parametrize("fault", ["listener_bind", "decoder"])
@pytest.mark.parametrize("order", [SetupOrder.TYPE110_FIRST, SetupOrder.TYPE111_FIRST])
def test_actual_receiver_setup_failure_withdraws_only_type111_and_type110_keeps_working(
        fault, order, stream):
    lab = Lab(faults=FaultInjector(fault))
    client = None
    try:
        lab.open()
        result = lab.setup(order=order)
        assert result.type110_ready and not result.type111_ready
        assert result.error_code is not None
        assert lab.pipeline.receiver.primary is not None
        assert lab.pipeline.receiver.primary_decoder is not None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.session.model.delegator.secondary.lifecycle.current_type111 is None
        client = lab.connect_primary()
        client.sendall(stream.primary_message(1))
        lab.session.pump_primary()
        assert lab.display0.current.timestamp == 2
        assert lab.primary.active and lab.primary.setup_calls == 1
        assert lab.pipeline.receiver.state is ReceiverState.PRIMARY_ACTIVE
        assert lab.session.residual() == ()
    finally:
        if client:
            client.close()
        lab.close()


def test_type111_first_request_waits_for_type110_receiver_before_child_commit():
    lab = Lab(faults=FaultInjector("primary_listener"))
    try:
        lab.open()
        result = lab.setup(order=SetupOrder.TYPE111_FIRST)
        assert not result.type110_ready and not result.type111_ready
        assert result.error_code == "type110_receiver_setup_failed"
        assert result.model_setup.response == STOCK_SETUP
        assert not result.model_setup.child_committed
        assert lab.serialized == []  # no child response serialized without Type110 readiness
        assert lab.pipeline.receiver.primary is None and lab.pipeline.receiver.secondary is None
        assert lab.pipeline.receiver.decoder is None and lab.primary.active
        assert lab.session.model.delegator.secondary.lifecycle.current_type111 is None
    finally:
        lab.close()


def test_type111_only_setup_is_rejected_without_primary_parent():
    lab = Lab()
    try:
        lab.open()
        result = lab.session.setup(
            {"streams": [{"type": 111, "streamConnectionID": SECONDARY_ID}]},
            lambda fields: (serialize_lab_plist(fields), SerializerResult(0xC8, 0))[1],
            order=SetupOrder.TYPE111_FIRST,
        )
        assert result.error_code == "type110_parent_required"
        assert result.model_setup.response == STOCK_SETUP
        assert not result.model_setup.child_committed and not result.type111_ready
        assert lab.primary.setup_calls == 1
        assert lab.session.model.delegator.secondary.lifecycle.current_type111 is None
        assert lab.pipeline.receiver.primary is None and lab.pipeline.receiver.secondary is None
        assert lab.pipeline.coordinator.lease is None
    finally:
        lab.close()


@pytest.mark.parametrize("bad_request", [
    {"streams": [{"type": 111, "streamConnectionID": SECONDARY_ID}] * 17},
    {"streams": [{"type": 110, "streamConnectionID": PRIMARY_ID}, "bad-entry"]},
    {"streams": [{"type": 110, "streamConnectionID": PRIMARY_ID},
                  {"type": 111, "streamConnectionID": PRIMARY_ID}]},
])
def test_malformed_setup_uses_stock_fallback_without_allocating_media_resources(bad_request):
    lab = Lab()
    try:
        lab.open()
        result = lab.session.setup(bad_request, lab.serialize)
        assert result.model_setup.response == STOCK_SETUP
        assert not result.type111_ready and not result.model_setup.child_committed
        assert lab.primary.setup_calls == 1
        assert lab.pipeline.receiver.primary is None and lab.pipeline.receiver.secondary is None
        assert lab.pipeline.coordinator.lease is None
        assert lab.session.model.delegator.secondary.lifecycle.current_type111 is None
    finally:
        lab.close()


def test_invalid_video_config_withdraws_child_then_type110_continues(stream):
    lab = Lab()
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.append(lab.connect_primary())
        clients.append(lab.connect_secondary())
        clients[1].sendall(synth.encode_lab_message(1, b"avcCbad", 0))
        result = lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert not result.accepted and lab.session.identity is None
        assert lab.pipeline.host.visible_content is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.receiver.primary is not None
        clients[0].sendall(stream.primary_message(2))
        lab.session.pump_primary()
        assert lab.display0.current.timestamp == 3
        assert lab.primary.active and lab.session.residual() == ()
    finally:
        for client in clients:
            client.close()
        lab.close()


@pytest.mark.parametrize("failure", ["malformed_h264", "decoder_crash", "lease_revoked"])
def test_media_or_presentation_failure_withdraws_only_child(failure, stream, monkeypatch):
    lab = Lab()
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.append(lab.connect_primary())
        clients.append(lab.connect_secondary())
        clients[1].sendall(stream.config_message())
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        if failure == "malformed_h264":
            clients[1].sendall(synth.encode_lab_message(0, b"\xff\xff\xff\xff", 1))
        elif failure == "decoder_crash":
            def crash(*_args, **_kwargs):
                raise RuntimeError("synthetic decoder crash")
            monkeypatch.setattr(lab.pipeline.receiver.decoder, "decode", crash)
            clients[1].sendall(stream.frame_message(0))
        else:
            lab.pipeline.host.revoke("synthetic lease-revocation test")
            clients[1].sendall(stream.frame_message(0))
        outcome = lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert not outcome.accepted
        assert lab.session.identity is None
        assert lab.pipeline.host.visible_content is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.receiver.primary is not None
        clients[0].sendall(stream.primary_message(3))
        lab.session.pump_primary()
        assert lab.display0.current.timestamp == 4
        assert lab.primary.active and lab.session.residual() == ()
    finally:
        for client in clients:
            client.close()
        lab.close()


def test_wrong_parent_generation_and_connection_id_are_rejected_without_touching_child(stream):
    lab = Lab()
    client = None
    try:
        lab.open()
        assert lab.setup().type111_ready
        client = lab.connect_secondary()
        with pytest.raises(LabMediaError, match="parent_identity_or_generation_mismatch"):
            lab.session.accept_type111(object(), lab.parent_generation, SECONDARY_ID)
        with pytest.raises(LabMediaError, match="parent_identity_or_generation_mismatch"):
            lab.session.accept_type111(lab.parent, lab.parent_generation + 1, SECONDARY_ID)
        with pytest.raises(LabMediaError, match="stream_connection_id_mismatch"):
            lab.session.accept_type111(lab.parent, lab.parent_generation, SECONDARY_ID + 1)
        assert lab.session.identity is not None
        client.sendall(stream.config_message())
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
    finally:
        if client:
            client.close()
        lab.close()


def test_duplicate_setup_is_rejected_without_replacing_the_active_child():
    lab = Lab()
    try:
        lab.open()
        result = lab.setup()
        child = lab.session.model.delegator.secondary.lifecycle.current_type111
        receiver = lab.pipeline.receiver.secondary
        with pytest.raises(LabMediaError, match="setup_already_completed"):
            lab.setup()
        assert lab.session.model.delegator.secondary.lifecycle.current_type111 is child
        assert lab.pipeline.receiver.secondary is receiver
        assert lab.pipeline.coordinator.lease is not None
    finally:
        lab.close()


def test_replaced_decoder_epoch_rejects_stale_coordinator_identity():
    lab = Lab()
    client = None
    try:
        lab.open()
        assert lab.setup().type111_ready
        client = lab.connect_secondary()
        client.sendall(synth.SyntheticStream(1).config_message())
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        old_identity = lab.session.identity
        lab.pipeline.receiver.restart_secondary_decoder(
            lab.pipeline.generation, synth.WIDTH, synth.HEIGHT
        )
        with pytest.raises(LabMediaError, match="stale_decoder_generation"):
            lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert lab.session.identity == old_identity
        assert lab.pipeline.receiver.secondary is not None
    finally:
        if client:
            client.close()
        lab.close()


def test_listener_close_after_setup_withdraws_only_type111_and_primary_continues(stream):
    lab = Lab()
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.extend((lab.connect_primary(), lab.connect_secondary()))
        listener = lab.pipeline.receiver.secondary
        listener.close()
        result = lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert not result.accepted and lab.session.identity is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.host.visible_content is None
        clients[0].sendall(stream.primary_message(1))
        lab.session.pump_primary()
        assert lab.pipeline.receiver.primary is not None
        assert lab.display0.current.timestamp == 2
        assert lab.primary.active and lab.session.residual() == ()
    finally:
        for client in clients:
            client.close()
        lab.close()


def test_media_producer_disconnect_withdraws_only_child_and_primary_continues(stream):
    lab = Lab()
    primary_client = secondary_client = None
    try:
        lab.open()
        assert lab.setup().type111_ready
        primary_client = lab.connect_primary()
        secondary_client = lab.connect_secondary()
        secondary_client.sendall(stream.config_message())
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        secondary_client.close()
        secondary_client = None
        result = lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID)
        assert not result.accepted and lab.session.identity is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        primary_client.sendall(stream.primary_message(0))
        lab.session.pump_primary()
        assert lab.display0.current is not None
        assert lab.primary.active and lab.session.residual() == ()
    finally:
        if primary_client:
            primary_client.close()
        if secondary_client:
            secondary_client.close()
        lab.close()


def test_failed_serializer_after_real_child_preparation_releases_child_resources(stream):
    lab = Lab()
    try:
        lab.open()
        result = lab.setup(fail_serializer=True)
        assert not result.type111_ready and result.type110_ready
        assert result.model_setup.error_code == "stock_serializer_failed"
        assert result.model_setup.serializer_invocations == 1
        assert lab.observed_child_resources[0].close_count == 1
        assert lab.session._child_lease is None and lab.session.identity is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.coordinator.lease is None
        assert lab.pipeline.receiver.primary is not None
        assert lab.primary.active and lab.session.residual() == ()
    finally:
        lab.close()


def test_child_teardown_is_idempotent_clears_display_and_keeps_type110_active(stream):
    lab = Lab()
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.append(lab.connect_primary())
        clients.append(lab.connect_secondary())
        clients[1].sendall(stream.config_message() + stream.frame_message(0))
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        owner = lab.session._child_lease
        assert owner is not None
        assert lab.session.teardown_type111(lab.parent, lab.parent_generation)
        assert lab.session.teardown_type111(lab.parent, lab.parent_generation)
        assert owner.close_count == 1
        assert lab.pipeline.host.visible_content is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.coordinator.lease is None
        assert lab.pipeline.receiver.primary is not None and lab.pipeline.receiver.primary_decoder is not None
        assert lab.primary.active and lab.session.residual() == ()
        clients[0].sendall(stream.primary_message(0))
        lab.session.pump_primary()
        assert lab.display0.current is not None
    finally:
        for client in clients:
            client.close()
        lab.close()


def test_parent_teardown_clears_both_streams_and_every_project_resource(stream):
    lab = Lab()
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.extend((lab.connect_primary(), lab.connect_secondary()))
        clients[1].sendall(stream.config_message() + stream.frame_message(1))
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        assert lab.display0.current is None
        assert lab.pipeline.host.visible_content is not None
        assert lab.session.close_parent(lab.parent, lab.parent_generation)
        assert lab.pipeline.receiver.snapshot() == type(lab.pipeline.receiver.snapshot())(0, 0, 0, 0, 0, 0, 0)
        assert lab.pipeline.host.visible_content is None
        assert lab.pipeline.host.residual_state == ()
        assert lab.session.residual() == ()
    finally:
        for client in clients:
            client.close()


def test_reconnect_uses_new_receiver_identity_and_rejects_late_b1_events(stream):
    pipe_lab = Lab(parent_generation=51)
    first_client = second_client = None
    try:
        pipe_lab.open()
        assert pipe_lab.setup().type111_ready
        first_client = pipe_lab.connect_secondary()
        first_client.sendall(stream.config_message() + stream.frame_message(0))
        assert pipe_lab.session.pump_type111(pipe_lab.parent, pipe_lab.parent_generation, SECONDARY_ID).accepted
        assert pipe_lab.session.pump_type111(pipe_lab.parent, pipe_lab.parent_generation, SECONDARY_ID).accepted
        b1_identity = pipe_lab.session.identity
        b1_child_resource = pipe_lab.session._child_lease
        assert pipe_lab.session.close_parent(pipe_lab.parent, pipe_lab.parent_generation)

        # New model parent on the same, cleanly reusable ingest pipeline.
        root = pipe_lab
        lab2 = Lab.__new__(Lab)
        lab2.pipeline = root.pipeline
        lab2.display0 = root.display0
        lab2.primary = MockStockPrimarySession(STOCK_SETUP)
        twin = LegacyDualScreenTwin(
            bytes(16), encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter))
        )
        twin.add_screen(ScreenRole.TYPE110, PRIMARY_ID)
        lifecycle = DualScreenLifecycleTwin(twin)
        delegator = StockFirstType111Delegator(
            lab2.primary, Type111SetupContract(lifecycle, DeterministicListenerAllocator())
        )
        from claritylink_jmcs.capabilities import SecondaryDisplayCapability
        from claritylink_jmcs.lab_dual_display import LabDualDisplayModel
        model = LabDualDisplayModel(
            delegator, STOCK_INFO, STOCK_SETUP,
            secondary_capability=SecondaryDisplayCapability.synthetic_lab(
                main_uuid="b7e6c5a0-1111-4000-8000-000000000001",
                secondary_uuid="b7e6c5a0-3333-4000-8000-000000000003"),
            readiness=SyntheticReadiness(True, True, True),
        )
        lab2.session = NegotiatedType111MediaSession(model, root.pipeline)
        lab2.parent = object()
        lab2.parent_generation = 52
        lab2.info = lab2.session.open(
            lab2.parent, lab2.parent_generation, info_policy=InfoPolicy.MODEL_ONLY
        )
        second_id = SECONDARY_ID + 1
        result = lab2.session.setup(
            {"streams": [{"type": 111, "streamConnectionID": second_id},
                         {"type": 110, "streamConnectionID": PRIMARY_ID}]},
            lambda fields: (serialize_lab_plist(fields), SerializerResult(0xC8, 0))[1],
            order=SetupOrder.TYPE111_FIRST,
        )
        assert result.type111_ready
        b2_identity = result.identity
        assert b1_identity is not None and b2_identity is not None
        assert b1_identity.receiver_session_generation != b2_identity.receiver_session_generation
        assert b1_identity.stream_connection_id != b2_identity.stream_connection_id
        assert b1_child_resource is not None and b1_child_resource.close_count == 1
        with pytest.raises(LabMediaError, match="parent_session_not_active"):
            pipe_lab.session.pump_type111(pipe_lab.parent, pipe_lab.parent_generation, SECONDARY_ID)
        second_client = synth.connect(root.pipeline.receiver.secondary.port)
        lab2.session.accept_type111(lab2.parent, lab2.parent_generation, second_id)
        second_client.sendall(stream.config_message() + stream.frame_message(3))
        assert lab2.session.pump_type111(lab2.parent, lab2.parent_generation, second_id).accepted
        outcome = lab2.session.pump_type111(lab2.parent, lab2.parent_generation, second_id)
        assert outcome.accepted
        synth.assert_pixels_match(root.pipeline.host.visible_content.frame, 3)
        assert lab2.session.close_parent(lab2.parent, lab2.parent_generation)
    finally:
        if first_client:
            first_client.close()
        if second_client:
            second_client.close()
        if pipe_lab.session.active:
            pipe_lab.close()


def test_host_lease_timeout_retires_child_without_stopping_primary(stream):
    clock = synth.Clock()
    lab = Lab(clock=clock, lease_seconds=1.0)
    clients = []
    try:
        lab.open()
        assert lab.setup().type111_ready
        clients.append(lab.connect_primary())
        clients.append(lab.connect_secondary())
        clients[1].sendall(stream.config_message() + stream.frame_message(0))
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        assert lab.session.pump_type111(lab.parent, lab.parent_generation, SECONDARY_ID).accepted
        clock.advance(2.0)
        assert lab.session.reconcile()
        assert lab.session.identity is None and lab.pipeline.host.visible_content is None
        assert lab.pipeline.receiver.secondary is None and lab.pipeline.receiver.decoder is None
        assert lab.pipeline.receiver.primary is not None and lab.primary.active
        clients[0].sendall(stream.primary_message(0))
        lab.session.pump_primary()
        assert lab.display0.current is not None and lab.session.residual() == ()
    finally:
        for client in clients:
            client.close()
        lab.close()


def test_concurrent_repeated_child_teardown_has_no_orphaned_worker(stream):
    lab = Lab()
    try:
        lab.open()
        assert lab.setup().type111_ready
        owner = lab.session._child_lease
        results = []
        threads = [threading.Thread(
            target=lambda: results.append(
                lab.session.teardown_type111(lab.parent, lab.parent_generation)
            )) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(5)
        assert all(not thread.is_alive() for thread in threads)
        assert results and all(results)
        assert owner is not None and owner.close_count == 1
        assert lab.session.residual() == ()
        dispatch = lab.pipeline.receiver.dispatch_registry_snapshot()
        assert 110 in dispatch and 111 not in dispatch
    finally:
        lab.close()
