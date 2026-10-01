"""Export a synthetic-only JSON view of the canonical Type111 replay."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src/claritylink-renderer"))

from capability_gating import ReplayMode
from host_h264_decoder import (
    DecodeStatus, FfmpegCliDecoder, generate_synthetic_h264, probe_ffmpeg_capabilities,
)
from model import ClarityLinkRenderer, MockDisplay1Backend
from synthetic_type111_replay import synthetic_type111_cluster_replay
from synthetic_screenstream_fixture import (
    create_synthetic_screenstream_fixture, run_fixture_through_transport,
)


def run_synthetic_decode_validation() -> dict[str, Any]:
    """Encode/decode one generated test pattern in memory and submit it to mock Display 1."""
    capabilities = probe_ffmpeg_capabilities()
    try:
        encoded = generate_synthetic_h264()
    except RuntimeError as exc:
        return {"status": "ATTEMPTED_FAILED", "reason": str(exc), "evidence": "SYNTHETIC_TEST_VALUE",
                "capabilities": capabilities.__dict__}
    result = FfmpegCliDecoder().decode_access_unit(
        encoded, width=320, height=180, timestamp_ns=1_000_000_000, frame_index=0,
    )
    if result.status is not DecodeStatus.DECODED or result.frame is None:
        return {"status": "ATTEMPTED_FAILED", "reason": result.reason or result.status.value,
                "evidence": "SYNTHETIC_TEST_VALUE", "capabilities": capabilities.__dict__}
    backend = MockDisplay1Backend()
    renderer = ClarityLinkRenderer(backend)
    try:
        renderer.start()
        renderer.submit(result.frame)
        submitted = len(backend.frames) == 1 and backend.frames[0] == result.frame
    except (RuntimeError, ValueError) as exc:
        submitted = False
        reason = str(exc)
    else:
        reason = "mock renderer did not accept decoded frame"
    finally:
        renderer.close()
    if not submitted:
        return {"status": "ATTEMPTED_FAILED", "reason": reason,
                "evidence": "SYNTHETIC_TEST_VALUE", "capabilities": capabilities.__dict__}
    return {
        "status": "HOST_DECODED_SYNTHETIC_H264",
        "backend": "FFMPEG_CLI/libx264",
        "ffmpeg_version": capabilities.version,
        "output_format": "ANNEXB",
        "encoded_bytes": len(encoded),
        "capabilities": capabilities.__dict__,
        "dimensions": [result.frame.width, result.frame.height],
        "rgba_payload_size": len(result.frame.rgba or b""),
        "presentation_timestamp_ns": result.frame.presentation_time_ns,
        "frame_index": 0,
        "renderer_target": "Display 1 mock",
        "evidence": "SYNTHETIC_TEST_VALUE",
        "separate_from_type111_fixture": True,
    }


def run_screenstream_h264_validation() -> dict[str, Any]:
    """Generate synthetic H.264 and validate the modeled ScreenStream path end to end."""
    capabilities = probe_ffmpeg_capabilities()
    try:
        fixture = create_synthetic_screenstream_fixture()
        result = run_fixture_through_transport(fixture)
    except (RuntimeError, ValueError, AssertionError) as exc:
        return {
            "status": "ATTEMPTED_FAILED",
            "reason": str(exc),
            "evidence": "SYNTHETIC_TEST_VALUE",
            "crypto_mode": "PLAINTEXT_SYNTHETIC",
            "capabilities": capabilities.__dict__,
        }
    if result["status"] != "PASS":
        return {
            "status": "ATTEMPTED_FAILED",
            "reason": result.get("reason", "ScreenStream decode or renderer failed"),
            "evidence": "SYNTHETIC_TEST_VALUE",
            "crypto_mode": fixture.crypto_mode,
            "capabilities": capabilities.__dict__,
        }
    return {
        "status": "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM",
        "backend": "FFMPEG_CLI/libx264",
        "ffmpeg_version": capabilities.version,
        "output_format": "ANNEXB",
        "screenstream_input": "SYNTHETIC_TEST_VALUE",
        "crypto_mode": fixture.crypto_mode,
        "nal_types": sorted({nal[0] & 0x1F for nal in fixture.nals}),
        "sps_count": result["sps_count"],
        "pps_count": result["pps_count"],
        "vcl_count": result["vcl_count"],
        "nal_length_size": result["config"].nal_length_size,
        "avcc_config_length": result["avcc_config_length"],
        "avcc_frame_length": result["avcc_frame_length"],
        "encoded_annexb_length": result["encoded_annexb_length"],
        "packet_lengths": result["packet_lengths"],
        "dimensions": result["media_dimensions"],
        "rgba_payload_size": result["rgba_payload_size"],
        "renderer_target": "Display 1 mock",
        "evidence": "SYNTHETIC_TEST_VALUE",
        "separate_from_honda_type111": True,
    }


def build_visual_demo_payload(
    host_decode_validation: dict[str, Any] | None = None,
    screenstream_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    modes: dict[str, Any] = {}
    for mode in ReplayMode:
        replay = synthetic_type111_cluster_replay(mode)
        allowed = replay["decision"].allowed
        events = replay["events"]
        event_names = [item["event"] for item in events]
        response = replay["hypothetical_type111_response"]
        frame = replay["decoded_frame"]
        submitted = "type111_frame_submitted_to_renderer" in event_names
        if not submitted:
            decode_status_label = "No frame in strict Honda mode"
        elif screenstream_validation and screenstream_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM":
            decode_status_label = "HOST-DECODED SYNTHETIC H264 VIA SCREENSTREAM FIXTURE"
        elif screenstream_validation and screenstream_validation.get("status") == "ATTEMPTED_FAILED":
            decode_status_label = "HOST DECODER ATTEMPTED — FAILED"
        elif host_decode_validation and host_decode_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264":
            decode_status_label = "HOST-DECODED SYNTHETIC H264"
        elif host_decode_validation and host_decode_validation.get("status") == "ATTEMPTED_FAILED":
            decode_status_label = "HOST DECODER ATTEMPTED — FAILED"
        elif not replay["host_decode"]["backend_available"]:
            decode_status_label = "SYNTHETIC FRAME SOURCE — HOST DECODER UNAVAILABLE"
        else:
            decode_status_label = "SYNTHETIC FRAME SOURCE — VALID H.264 TEST MEDIA NOT GENERATED"
        modes[mode.value] = {
            "type110": {
                "active": True,
                "unchanged": replay["stock_response"]["streams"][:2]
                == replay["stock_baseline"]["streams"],
                "display": "Display 0 · stock center placeholder",
                "evidence": ["HONDA_CONFIRMED", "SYNTHETIC_TEST_VALUE"],
            },
            "audio": {
                "unchanged": replay["after_type111_teardown"]["audio"]
                == replay["audio_snapshot"],
                "evidence": "SYNTHETIC_TEST_VALUE",
            },
            "type111": {
                "status": "synthetic replay completed" if allowed else "skipped / unsupported",
                "listener_started": "type111_listener_started" in event_names,
                "video_config_received": "type111_videoconfig_received" in event_names,
                "frame_received": "type111_frame_received" in event_names,
                "renderer_submitted": submitted,
                "response_fields": list(response[0].keys()) if response else [],
                "evidence": "MHI2_DERIVED_HYPOTHESIS" if allowed else "HONDA_CONFIRMED",
                "field_values": "SYNTHETIC_TEST_VALUE" if allowed else None,
            },
            "cluster_frame": {
                "visible": submitted,
                "source": "generated synthetic media via ScreenStream fixture" if submitted else None,
                "decoded_from_h264": bool(
                    screenstream_validation
                    and screenstream_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM"
                ),
                "width": frame.width if frame else None,
                "height": frame.height if frame else None,
                "presentation_timestamp": "SYNTHETIC_TEST_VALUE" if frame else None,
                "evidence": "SYNTHETIC_TEST_VALUE",
                "decode_status": replay["host_decode"]["status"],
                "decode_backend": replay["host_decode"]["backend"],
                "status_label": decode_status_label,
            },
            "renderer": {
                "target": "Display 1 · ExternalDisplay host mock" if submitted else "inactive",
                "real_externaldisplay_integration": "UNKNOWN",
                "crop_mask": "UNKNOWN",
                "safety_overlay_composition": "UNKNOWN",
                "evidence": "SYNTHETIC_TEST_VALUE",
            },
            "evidence_labels": [
                {"element": "Display 0 stock Type110 path", "label": "HONDA_CONFIRMED"},
                {"element": "Display 0 generated fixture values", "label": "SYNTHETIC_TEST_VALUE"},
                {"element": "Display 1 mock canvas", "label": "SYNTHETIC_TEST_VALUE"},
                {"element": "Type111 candidate response profile", "label": "MHI2_DERIVED_HYPOTHESIS" if allowed else "UNKNOWN"},
                {"element": "Type111 candidate field values", "label": "SYNTHETIC_TEST_VALUE" if allowed else "UNKNOWN"},
                {"element": "Display-to-stream correlation", "label": "UNKNOWN"},
                {"element": "Type111 security/key derivation", "label": "UNKNOWN"},
                {"element": "Synthetic ScreenStream H.264 fixture", "label": "SYNTHETIC_TEST_VALUE"},
                {"element": "Host H.264 decode", "label": (
                    "SYNTHETIC_TEST_VALUE" if (
                        (screenstream_validation and screenstream_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM")
                        or (host_decode_validation and host_decode_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264")
                    ) else "UNKNOWN"
                )},
                {"element": "Mock renderer submission", "label": "SYNTHETIC_TEST_VALUE"},
                {"element": "Real ExternalDisplay integration", "label": "UNKNOWN"},
                {"element": "Cluster crop/mask", "label": "UNKNOWN"},
            ],
            "unknowns": [
                {"topic": "Honda Type111 response schema", "evidence": "UNKNOWN"},
                {"topic": "display-to-stream correlation", "evidence": "UNKNOWN"},
                {"topic": "Type111 security and key derivation", "evidence": "UNKNOWN"},
                {"topic": "real ExternalDisplay frame handoff", "evidence": "UNKNOWN"},
                {"topic": "jmcs integration/load seam", "evidence": "UNKNOWN"},
                {"topic": "crop and mask geometry", "evidence": "UNKNOWN"},
            ],
            "timeline": events,
        }

    return {
        "schema": "claritylink.synthetic-type111-visual-demo.v1",
        "generated_at": datetime(2026, 9, 30, tzinfo=timezone.utc).isoformat(),
        "source": "STEP_42E_REPLAY_OUTPUT+SYNTHETIC_SCREENSTREAM_H264_VALIDATION"
        if screenstream_validation and screenstream_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264_VIA_SCREENSTREAM"
        else "STEP_42E_REPLAY_OUTPUT+SYNTHETIC_FFMPEG_VALIDATION"
        if host_decode_validation and host_decode_validation.get("status") == "HOST_DECODED_SYNTHETIC_H264"
        else "STEP_42E_REPLAY_OUTPUT",
        "host_decode_validation": host_decode_validation or {
            "status": "NOT_RUN", "reason": "no external synthetic encode/decode validation supplied"
        },
        "screenstream_validation": screenstream_validation or {
            "status": "NOT_RUN", "reason": "no synthetic ScreenStream H.264 validation supplied"
        },
        "live_test": "NOT_READY",
        "jmcs_noop_test": "NOT_READY",
        "externaldisplay_live_render_test": "NOT_READY",
        "ld_preload": "PARKED",
        "modes": modes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "demo/type111/replay-data.json",
        help="output JSON path (default: demo/type111/replay-data.json)",
    )
    parser.add_argument(
        "--decode-synthetic-h264", action="store_true",
        help="encode/decode one in-memory synthetic H.264 frame and record renderer-mock status",
    )
    parser.add_argument(
        "--screenstream-h264", action="store_true",
        help="run synthetic H.264 through modeled ScreenStream parsing, decode, and Display 1 mock",
    )
    args = parser.parse_args()
    validation = run_synthetic_decode_validation() if args.decode_synthetic_h264 else None
    screenstream_validation = run_screenstream_h264_validation() if args.screenstream_h264 else None
    payload = build_visual_demo_payload(validation, screenstream_validation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote synthetic Step 42E replay summary: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
