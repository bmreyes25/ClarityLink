"""Canonical synthetic Type111 replay assembled from current offline models."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for relative in (
    "src/claritylink-interposer",
    "src/claritylink-negotiation",
    "src/claritylink-transport",
    "src/claritylink-renderer",
):
    sys.path.insert(0, str(ROOT / relative))

from lifecycle_coord import ClarityLinkLifecycleCoordinator, ClarityLinkRedactedDiagnostics
from listener import FakeSecondaryListenerFactory
from models import (
    ClarityLinkCapabilityProfile, ClarityLinkSecondaryDisplayDescriptor,
    Provenance, ResponseStrategy, SourcedValue, Type111ResponseProfile,
)
from receiver_core import HondaScreenReceiverCore, VideoConfigEvent, VideoMediaBufferEvent
from screen_parser import HEADER_SIZE
from server_info import ClarityLinkServerInfoAugmentor
from setup_interposer import ClarityLinkSetupInterposer, ClarityLinkType111ResponseBuilder, StockSetupDelegate
from model import ClarityLinkRenderer, MockDisplay1Backend, SyntheticPatternSource

from capability_gating import CapabilityDecision, CapabilityInputs, ReplayMode, evaluate_capability_gate
from host_h264_decoder import FfmpegCliDecoder


def _message(opcode: int, body: bytes, timestamp_raw: int) -> bytes:
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    header[4] = opcode
    header[8:16] = timestamp_raw.to_bytes(8, "little")
    return bytes(header) + body


def synthetic_type111_cluster_replay(mode: ReplayMode = ReplayMode.HYPOTHETICAL_TYPE111) -> dict[str, Any]:
    """Run stock-first Setup, candidate media pipeline, mock render, and cleanup.

    The Type110 response and audio values are synthetic fixtures shaped by
    Honda-confirmed fields. Type111 response fields are MHI2-derived hypothesis.
    Screen body is synthetic plaintext; this does not exercise Type111 crypto.
    """
    events: list[dict[str, Any]] = []
    host_decoder = FfmpegCliDecoder()
    diagnostics = ClarityLinkRedactedDiagnostics()
    stock_type110_response = {"type": 110, "dataPort": 42110}
    stock_audio = {"center_active": True, "voice_route_active": True, "focus_owner": "synthetic-stock"}
    original_server_info = {"displays": [{
        "uuid": "SYNTHETIC_MAIN_DISPLAY", "evidence": "synthetic Honda-shaped baseline"
    }], "features": 3}
    stock_response = {"streams": [
        {"type": 100, "dataPort": 42100},
        deepcopy(stock_type110_response),
    ], "stockOpaqueField": "keep"}
    setup_request = {"streams": [
        {"type": 100, "streamConnectionID": 42000},
        {"type": 110, "streamConnectionID": 42001},
        {"type": 111, "streamConnectionID": 42002, "displayCorrelation": "synthetic-only"},
    ]}
    setup_request_baseline = deepcopy(setup_request)
    stock_calls: list[str] = []

    def stock_setup(original):
        assert original is setup_request
        stock_calls.append("stock")
        events.append({"event": "type110_setup_started", "evidence": "synthetic Honda-shaped baseline"})
        events.append({"event": "type110_setup_preserved"})
        events.append({"event": "capability_gate_checked", "mode": mode.value,
                       "allowed": decision.allowed, "evidence": decision.evidence,
                       "unknowns": ["Honda Type111 response schema", "display/stream correlation",
                                    "Type111 KDF and master reuse"]})
        return 0, deepcopy(stock_response)

    gates = CapabilityInputs(
        session_active=True, type110_established=True, capability_advertised=True,
        display_descriptor_available=True, stream_fields_available=True,
        synthetic_security_inputs_available=True, renderer_target_available=True,
        unknown_honda_fields_explicit=True,
    )
    decision: CapabilityDecision = evaluate_capability_gate(mode, gates)
    if decision.allowed:
        display_profile = ClarityLinkCapabilityProfile(
            descriptor=ClarityLinkSecondaryDisplayDescriptor(
                uuid=SourcedValue("SYNTHETIC_CLUSTER_DISPLAY", Provenance.CONFIGURABLE)
            ),
            evidence_label="SYNTHETIC_TEST_VALUE; display/stream correlation UNKNOWN",
        )
        server_info = ClarityLinkServerInfoAugmentor(display_profile).augment(original_server_info)
    else:
        server_info = deepcopy(original_server_info)
    events.append({"event": "session_started", "evidence": "synthetic"})

    listener_factory = FakeSecondaryListenerFactory(first_port=43111)
    # These fixed bytes are synthetic placeholders only. The ScreenStream
    # receiver below runs without crypto, so no key derivation is modeled.
    interposer = ClarityLinkSetupInterposer(
        StockSetupDelegate(stock_setup),
        listener_factory,
        lambda _connection_id: (b"K" * 16, b"I" * 16),
        ClarityLinkType111ResponseBuilder(
            Type111ResponseProfile(ResponseStrategy.PRIOR_ART_CLONE, include_stream_id=True)
        ),
        diagnostics=diagnostics,
    )
    _, response = interposer.setup(setup_request, enabled=decision.allowed)
    if decision.allowed:
        events.append({"event": "type111_allowed_hypothetical",
                       "evidence": "MHI2_DERIVED_HYPOTHESIS"})
        events.append({"event": "type111_setup_created",
                       "fields": {"type": "MHI2_DERIVED_HYPOTHESIS",
                                  "dataPort": "SYNTHETIC_TEST_VALUE",
                                  "streamConnectionID": "SYNTHETIC_TEST_VALUE",
                                  "displayCorrelation": "UNKNOWN"}})
    else:
        events.append({"event": "type111_skipped_by_honda",
                       "evidence": "HONDA_CONFIRMED stock unsupported branch"})

    primary_snapshot = deepcopy({"stock_response": response["streams"][:2],
                                 "type110_request": setup_request["streams"][1],
                                 "type110_response": stock_type110_response, "audio": stock_audio,
                                 "center_display": "stock-type110-active",
                                 "crypto_counter": 0, "listener": "active"})
    renderer_backend = MockDisplay1Backend()
    renderer = ClarityLinkRenderer(renderer_backend)
    frame = None
    renderer_received_frame = None
    media_bytes: bytes | None = None
    raw_timestamp = 0
    synthetic_secrets_cleared = True

    if decision.allowed:
        generation = interposer.current
        lifecycle = ClarityLinkLifecycleCoordinator(interposer, diagnostics)
        assert lifecycle.session_start(True)
        events.append({"event": "type111_listener_started", "dataPort": generation.data_port,
                       "evidence": "SYNTHETIC_TEST_VALUE"})
        accepted = generation.accept()
        assert accepted is not None
        events.append({"event": "type111_client_connected"})
        generation.receiver = HondaScreenReceiverCore(crypto=None)

        # Synthetic avcC-like config with one SPS and one PPS; 4-byte NAL lengths.
        avcc = bytes([1, 66, 0, 30, 0xFF, 0xE1]) + b"\x00\x02\x67\x42" + b"\x01\x00\x02\x68\xCE"
        video = (3).to_bytes(4, "big") + b"\x65\x88\x99"
        config_events = generation.feed(_message(1, avcc, 1234))
        assert any(isinstance(item, VideoConfigEvent) for item in config_events)
        events.append({"event": "type111_videoconfig_received",
                       "evidence": "SYNTHETIC_TEST_VALUE; parser semantics modeled from Type110"})

        frame_events = generation.feed(_message(0, video, 2345))
        media = next(item for item in frame_events if isinstance(item, VideoMediaBufferEvent))
        media_bytes = media.data
        assert media_bytes.startswith(b"\x00\x00\x00\x01\x67\x42")
        assert media_bytes.endswith(b"\x00\x00\x00\x01\x65\x88\x99")
        raw_timestamp = media.timestamp_raw
        events.append({"event": "type111_frame_received", "timestamp_raw": raw_timestamp,
                       "format": media.data_format, "evidence": "SYNTHETIC_TEST_VALUE"})

        # The replay fixture is parser-shaped, not valid decodable H.264.
        # Keep rendering an explicit synthetic fallback; never claim decode.
        source = SyntheticPatternSource()
        frame = source.next_frame(datetime(2026, 9, 30, tzinfo=timezone.utc))
        events.append({"event": "host_decode_not_run", "backend_available": host_decoder.available,
                       "reason": "replay access unit is synthetic parser fixture, not valid H.264"})
        events.append({"event": "synthetic_frame_source_fallback",
                       "source": "pattern-after-synthetic-Annex-B-parser-fixture",
                       "pts_ns": frame.presentation_time_ns,
                       "evidence": "SYNTHETIC_TEST_VALUE"})
        renderer.start()
        renderer.submit(frame)
        renderer_received_frame = renderer_backend.frames[0]
        events.append({"event": "type111_frame_submitted_to_renderer",
                       "target": {"display": 1, "size": [800, 480], "host": "mock"},
                       "evidence": "SYNTHETIC_TEST_VALUE"})

        # Required cluster overlay is retained as an explicit, unresolved
        # compositor policy; this host mock does not draw over Honda UI.
        safety_overlay = "UNKNOWN_NOT_RENDERED_BY_MOCK"
        crop_mask = "UNKNOWN"
        receiver_existed_before_teardown = generation.receiver is not None
        key_handle, iv_handle = generation.key, generation.iv
        lifecycle.teardown_type111_generation()
        renderer.close()
        events.append({"event": "type111_teardown"})
        events.append({"event": "type110_still_active"})
        events.append({"event": "audio_state_unchanged"})
        assert interposer.current is None
        assert listener_factory.created[0].closed
        assert receiver_existed_before_teardown
        synthetic_secrets_cleared = len(key_handle) == 0 and len(iv_handle) == 0
        after_type111_teardown = {
            "type110_active": True, "center_display": "stock-type110-active",
            "audio": deepcopy(stock_audio), "type111_active": False,
            "renderer_attached": False,
        }

    else:
        safety_overlay = "UNKNOWN_NOT_RENDERED"
        crop_mask = "UNKNOWN"
        after_type111_teardown = {
            "type110_active": True, "center_display": "stock-type110-active",
            "audio": deepcopy(stock_audio), "type111_active": False,
            "renderer_attached": False,
        }
    full_session = {"type110_active": False, "type111_active": False,
                    "renderer_attached": False,
                    "audio": {"center_active": False, "voice_route_active": False,
                              "focus_owner": None}}
    events.append({"event": "full_session_teardown"})

    return {
        "mode": mode.value, "decision": decision, "stock_calls": stock_calls,
        "server_info": server_info, "original_server_info": original_server_info,
        "stock_response": response, "stock_baseline": stock_response,
        "setup_request": setup_request, "setup_request_baseline": setup_request_baseline,
        "type110_snapshot": primary_snapshot, "audio_snapshot": stock_audio,
        "hypothetical_type111_response": response["streams"][2:] if decision.allowed else [],
        "annex_b_access_unit": media_bytes, "decoded_frame": frame,
        "renderer_received_frame": renderer_received_frame,
        "renderer_target": renderer_backend.target,
        "renderer_events": list(renderer_backend.events),
        "renderer_frame_count": 1 if decision.allowed else 0,
        "raw_screen_timestamp": raw_timestamp,
        "display_pts_is_synthetic": True,
        "synthetic_secrets_cleared": synthetic_secrets_cleared,
        "safety_overlay": safety_overlay, "crop_mask": crop_mask,
        "unknown_honda_fields": list(decision.blockers) + [
            "Honda Type111 response schema", "display/stream correlation",
            "Type111 KDF and master reuse", "Type111 opcodes/crypto",
        ],
        "events": events, "diagnostics": diagnostics.events,
        "after_type111_teardown": after_type111_teardown,
        "full_session_state": full_session,
        "evidence": {
            "HONDA_CONFIRMED": ["stock Type110 field names/stock-first ownership", "Honda skips unsupported Type111"],
            "MHI2_DERIVED_HYPOTHESIS": ["cloned Type111 response and streamID=111 candidate"],
            "SYNTHETIC_TEST_VALUE": ["ports", "IDs", "display correlation", "cleartext screen bodies", "frame", "audio"],
            "UNKNOWN": ["Honda Type111 schema", "display/stream relation", "Type111 security", "cluster crop/overlay"],
        },
        "field_provenance": {
            "Type111 response profile": "MHI2_DERIVED_HYPOTHESIS",
            "Type111 response values": "SYNTHETIC_TEST_VALUE",
            "displayCorrelation": "UNKNOWN",
            "key/iv": "UNKNOWN; no Type111 crypto is executed",
            "display UUID": "SYNTHETIC_TEST_VALUE; not correlated to stream",
        },
        "video_handoff_mode": "SYNTHETIC_FRAME_SOURCE",
        "host_decode": {
            "backend": "FFMPEG_CLI" if host_decoder.available else "MOCK_ONLY",
            "backend_available": host_decoder.available,
            "performed": False,
            "status": "NOT_RUN_SYNTHETIC_FIXTURE_NOT_VALID_H264" if host_decoder.available
            else "HOST_DECODER_UNAVAILABLE",
            "fallback": "synthetic pattern frame",
        },
    }
