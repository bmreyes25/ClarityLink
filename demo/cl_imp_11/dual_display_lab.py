"""End-to-end synthetic Type110/Type111 laboratory session.

The browser output is a two-panel artifact viewer. It is not Honda hardware,
CarPlay authentication, a physical cluster, or an iPhone session.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for path in (
    ROOT / "src/claritylink-jmcs",
    ROOT / "src/claritylink-negotiation",
    ROOT / "src/carplay-session-model",
    ROOT / "src/claritylink-transport",
    ROOT / "src/claritylink-renderer",
    ROOT / "src/claritylink-sim",
):
    sys.path.insert(0, str(path))

from claritylink_jmcs.authentication import (  # noqa: E402
    ReplayAuthenticationProvider, SessionHandoff, SessionOrigin,
)
from claritylink_jmcs.capabilities import SecondaryDisplayCapability  # noqa: E402
from claritylink_jmcs.decoder import DecodedFrame as ReceiverFrame  # noqa: E402
from claritylink_jmcs.identity import LabIdentity  # noqa: E402
from claritylink_jmcs.info import InfoProfile  # noqa: E402
from claritylink_jmcs.media import encode_lab_message  # noqa: E402
from claritylink_jmcs.receiver import Receiver  # noqa: E402
from claritylink_jmcs.runtime import DualDisplayRuntime  # noqa: E402
from claritylink_jmcs.session import ReceiverSession  # noqa: E402
from claritylink_jmcs.session_transport import (  # noqa: E402
    ControlRequest, ControlResponse, ReplaySessionTransport,
)
from claritylink_jmcs.stock_delegation import (  # noqa: E402
    MockStockPrimarySession, StockFirstType111Delegator,
)
from dual_screen_lifecycle import DualScreenLifecycleTwin  # noqa: E402
from legacy_dual_screen_twin import LegacyDualScreenTwin, ScreenRole  # noqa: E402
from model import (  # noqa: E402
    ClarityLinkRenderer, DecodedFrame as RendererFrame, MockDisplay1Backend, PIXEL_FORMAT,
)
from safe_area import SafeAreaConfig, SafeAreaGate  # noqa: E402
from type111_setup_contract import (  # noqa: E402
    DeterministicListenerAllocator, SerializerResult, Type111SetupContract,
)
from export_visual_demo import encode_rgba_png  # noqa: E402

SYNTHETIC_LABEL = "SYNTHETIC LAB CONTENT — NOT AUTHENTIC CARPLAY"
FRAME_LIMIT = 4 * 1024 * 1024


def _fixture(name: str) -> bytes:
    raw = (ROOT / "tests/fixtures/cl-imp-08" / name).read_text(encoding="ascii").strip()
    if len(raw) > 24 * 1024:
        raise ValueError("synthetic fixture exceeds encoded bound")
    payload = base64.b64decode(raw, validate=True)
    if not payload or len(payload) > FRAME_LIMIT:
        raise ValueError("synthetic fixture exceeds payload bound")
    return payload


def _profile() -> InfoProfile:
    return InfoProfile(
        identity=LabIdentity("02:00:00:00:00:01", "b7e6c5a0-1111-4000-8000-000000000001",
                             "b7e6c5a0-2222-4000-8000-000000000002"),
        name="ClarityLink CL-IMP-11 Synthetic Lab", model="LAB", manufacturer="ClarityLink",
        source_version="CL-IMP-11-MODEL_ONLY", feature_bits=0,
        audio_formats=({"type": 1, "audioType": 1, "audioOutputFormats": 1},),
        audio_latencies=({"type": 1, "inputLatencyMicros": 0, "outputLatencyMicros": 0},),
        hid_devices=({"uuid": "lab-hid", "name": "Synthetic Lab Input",
                      "displayUUID": "b7e6c5a0-1111-4000-8000-000000000001",
                      "hidDescriptor": b"\x00", "hidProductID": 1,
                      "hidVendorID": 1, "hidCountryCode": 0},),
        displays=SecondaryDisplayCapability.synthetic_lab(width=800, height=480),
    )


class MockDelegatedReplayTransport:
    """Replay control transport with a separate mock stock-first SETUP seam."""

    authenticated = False

    def __init__(self, replay: ReplaySessionTransport,
                 delegation: StockFirstType111Delegator) -> None:
        self.replay = replay
        self.delegation = delegation
        self.delegation_result = None
        self._closed = False

    @property
    def generation(self) -> int:
        return self.replay.generation

    @property
    def session_identifier(self) -> str:
        return self.replay.session_identifier

    def read_request(self, timeout: float):
        request = self.replay.read_request(timeout)
        if request.method == "SETUP" and request.path == "/session":
            self.delegation_result = self.delegation.handle_setup(
                request.generation, request.body, lambda _candidate: SerializerResult(0xC8, 0))
            if not (self.delegation_result.secondary_committed and
                    self.delegation_result.primary_preserved):
                raise RuntimeError("mock_stock_delegation_rejected")
        return request

    def write_response(self, response: ControlResponse) -> None:
        if self._closed:
            raise RuntimeError("mock_transport_closed")
        if response.status == 200 and self.delegation_result is not None:
            streams = response.body.get("streams", ())
            if {item.get("type") for item in streams if isinstance(item, dict)} != {110, 111}:
                raise RuntimeError("runtime_dual_stream_setup_missing")
        self.replay.write_response(response)

    def close(self) -> None:
        self._closed = True
        self.replay.close()


def _mock_delegation(generation: int) -> StockFirstType111Delegator:
    twin = LegacyDualScreenTwin(
        bytes(range(16)),
        encrypt_block=lambda key, counter: bytes(a ^ b for a, b in zip(key, counter)),
    )
    twin.add_screen(ScreenRole.TYPE110, 1100 + generation)
    lifecycle = DualScreenLifecycleTwin(twin)
    contract = Type111SetupContract(lifecycle, DeterministicListenerAllocator())
    mock_primary = MockStockPrimarySession({
        "streams": [{"type": 110, "dataPort": 41001}],
        "audio": {"owner": "MOCK_STOCK_PRIMARY"},
        "primaryControlOwner": "MOCK_STOCK_SESSION",
    })
    delegator = StockFirstType111Delegator(mock_primary, contract)
    delegator.open(generation)
    return delegator


class PrimaryLabOutput:
    """Bounded Display 0 receiver sink; it never touches a physical display."""
    def __init__(self) -> None:
        self.current: ReceiverFrame | None = None
        self._condition = threading.Condition()
        self.frames = 0

    def begin_generation(self, _generation: int) -> None:
        self.clear()
        with self._condition:
            self.frames = 0

    def show(self, frame: ReceiverFrame) -> None:
        with self._condition:
            self.current = frame
            self.frames += 1
            self._condition.notify_all()

    def clear(self) -> None:
        with self._condition:
            self.current = None
            self._condition.notify_all()

    def wait_for_frame(self, minimum: int, timeout: float = 5.0) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: self.frames >= minimum, timeout)


class RenderedSecondaryOutput:
    """Type111 sink through the existing synthetic safe-area renderer."""
    def __init__(self, ffmpeg: str) -> None:
        self.ffmpeg = ffmpeg
        self._condition = threading.Condition()
        self.generation = 0
        self.warning_visible = False
        self.warning_dropped = 0
        self.submitted = 0
        self.renderer: ClarityLinkRenderer | None = None
        self.backend: MockDisplay1Backend | None = None
        self.current: RendererFrame | None = None
        self.last_rendered_png: bytes | None = None

    def begin_generation(self, generation: int) -> None:
        self.clear()
        config_json = json.loads((ROOT / "research/architecture/p2c4-safe-area.schema.json")
                                 .read_text(encoding="utf-8"))
        self.backend = MockDisplay1Backend()
        self.renderer = ClarityLinkRenderer(
            self.backend, safe_area=SafeAreaGate(SafeAreaConfig.from_mapping(config_json["examples"][0])))
        self.renderer.start()
        self.generation = generation
        self.warning_visible = False
        self.warning_dropped = 0
        self.submitted = 0
        self.last_rendered_png = None

    def show(self, frame: ReceiverFrame) -> None:
        with self._condition:
            if self.warning_visible:
                self.warning_dropped += 1
                self._condition.notify_all()
                return
            if frame.generation != self.generation or self.renderer is None or self.backend is None:
                raise ValueError("stale_synthetic_renderer_generation")
        rgba = self._decode_rgba(frame.png, frame.width, frame.height)
        render_frame = RendererFrame(
            frame.width, frame.height, PIXEL_FORMAT, frame.width * 4,
            max(1, frame.timestamp * 1_000_000), rgba=rgba,
        )
        self.renderer.submit(render_frame)
        with self._condition:
            if len(self.backend.frames) != 1:
                raise RuntimeError("renderer_retention_not_single_frame")
            self.current = self.backend.frames[0]
            self.last_rendered_png = encode_rgba_png(self.current)
            self.submitted += 1
            self._condition.notify_all()

    def _decode_rgba(self, png: bytes, width: int, height: int) -> bytes:
        expected = width * height * 4
        if expected <= 0 or expected > FRAME_LIMIT or len(png) > FRAME_LIMIT:
            raise ValueError("decoded_frame_bounds")
        result = subprocess.run(
            [self.ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error",
             "-f", "image2pipe", "-vcodec", "png", "-i", "pipe:0", "-frames:v", "1",
             "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"],
            input=png, capture_output=True, timeout=5, check=False,
        )
        if result.returncode != 0 or len(result.stdout) != expected:
            raise ValueError("decoded_png_to_rgba_failed")
        return result.stdout

    def warning_preempted(self) -> None:
        with self._condition:
            if self.renderer is not None:
                self.renderer.warning_preempted()
            self.current = None
            self.last_rendered_png = None
            self.warning_visible = True
            self._condition.notify_all()

    def warning_cleared(self) -> None:
        with self._condition:
            if self.renderer is not None:
                self.renderer.warning_cleared()
            self.warning_visible = False
            self._condition.notify_all()

    def clear(self) -> None:
        with self._condition:
            if self.renderer is not None:
                self.renderer.close()
            self.renderer = None
            self.backend = None
            self.current = None
            self.last_rendered_png = None
            self.warning_visible = False
            self.generation = 0
            self._condition.notify_all()

    def wait_for(self, predicate, timeout: float = 5.0) -> bool:
        with self._condition:
            return self._condition.wait_for(predicate, timeout)


def _profile_transport(generation: int, delegation: StockFirstType111Delegator,
                       streams: list[dict[str, int]]) -> MockDelegatedReplayTransport:
    handoff = SessionHandoff(f"cl-imp-11-synthetic-{generation}", generation,
                             SessionOrigin.SANITIZED_REPLAY, "CL-IMP-11-MODEL_ONLY",
                             object())
    replay = ReplaySessionTransport(handoff, [
        ControlRequest("GET", "/info", {}, generation),
        ControlRequest("SETUP", "/session", {"streams": streams}, generation),
    ])
    return MockDelegatedReplayTransport(replay, delegation)


def _start_runtime(receiver: Receiver, primary: PrimaryLabOutput,
                   secondary: RenderedSecondaryOutput, generation: int):
    streams = [
        {"type": 110, "streamConnectionID": 1100 + generation},
        {"type": 111, "streamConnectionID": 1110 + generation},
    ]
    delegation = _mock_delegation(generation)
    transport = _profile_transport(generation, delegation, streams)
    session = ReceiverSession(
        ReplayAuthenticationProvider(SessionHandoff(
            f"cl-imp-11-synthetic-{generation}", generation, SessionOrigin.SANITIZED_REPLAY,
            "CL-IMP-11-MODEL_ONLY", transport)),
        receiver, _profile(), allow_replay=True,
    )
    # Replay handoff transport must be a separate opaque token; the transport itself
    # is supplied explicitly to ReceiverSession as its replay control channel.
    runtime = DualDisplayRuntime(session)
    active_generation = runtime.start(transport)
    if active_generation != generation:
        raise RuntimeError("unexpected_runtime_generation")
    if runtime.handle_control_once().status != 200 or runtime.handle_control_once().status != 200:
        raise RuntimeError("synthetic_control_exchange_failed")
    if (transport.delegation_result is None or
            not transport.delegation_result.primary_preserved or
            not transport.delegation_result.secondary_committed):
        raise RuntimeError("mock_delegation_not_exercised")
    return runtime, delegation, streams


def _connect(runtime: DualDisplayRuntime, stream_type: int) -> socket.socket:
    listener = runtime.receiver.primary if stream_type == 110 else runtime.receiver.secondary
    if listener is None:
        raise RuntimeError("synthetic_stream_listener_missing")
    return socket.create_connection(("127.0.0.1", listener.port), timeout=2)


def _send(peer: socket.socket, stream_type: int, fixture: bytes, timestamp: int) -> None:
    del stream_type  # stream separation is enforced by the independently selected socket.
    peer.sendall(encode_lab_message(0, fixture, timestamp=timestamp))


def _start_producer(peer: socket.socket, stream_type: int, fixture: bytes,
                    stop: threading.Event, timestamp_start: int) -> threading.Thread:
    def produce() -> None:
        timestamp = timestamp_start
        while not stop.is_set():
            try:
                _send(peer, stream_type, fixture, timestamp)
            except OSError:
                return
            timestamp += 1
            stop.wait(0.2)
    worker = threading.Thread(target=produce, name=f"CLIMP11Synthetic{stream_type}", daemon=True)
    worker.start()
    return worker


def _write_png(path: Path, content: bytes) -> None:
    if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) > FRAME_LIMIT:
        raise ValueError("invalid_lab_png_artifact")
    path.write_bytes(content)


def _snapshot_png(primary: PrimaryLabOutput, secondary: RenderedSecondaryOutput,
                  output_dir: Path, suffix: str = "") -> tuple[Path, Path]:
    if primary.current is None or secondary.last_rendered_png is None:
        raise RuntimeError("dual_display_frames_not_ready")
    primary_path = output_dir / f"display0-type110{suffix}.png"
    secondary_path = output_dir / f"display1-type111{suffix}.png"
    _write_png(primary_path, primary.current.png)
    _write_png(secondary_path, secondary.last_rendered_png)
    return primary_path, secondary_path


def _run_generation(receiver: Receiver, primary: PrimaryLabOutput,
                    secondary: RenderedSecondaryOutput, generation: int,
                    output_dir: Path, *, exercise_faults: bool) -> dict[str, Any]:
    runtime, delegation, _streams = _start_runtime(receiver, primary, secondary, generation)
    primary_peer = _connect(runtime, 110)
    secondary_peer = _connect(runtime, 111)
    stop_primary = threading.Event()
    stop_secondary = threading.Event()
    primary_sender = secondary_sender = None
    result: dict[str, Any] = {"generation": generation, "evidence": "MODEL_ONLY",
                              "stockDelegation": "MOCK_STOCK_FIRST_PRESERVED",
                              "primaryOwner": "MOCK_HONDA_TYPE110", "secondaryOwner": "CLARITYLINK_LAB_TYPE111"}
    try:
        runtime.wait_for_event("stream_connected", 5, 110)
        runtime.wait_for_event("stream_connected", 5, 111)
        red = _fixture("type110-red-32x32.h264.b64")
        blue = _fixture("type111-blue-32x32.h264.b64")
        green = _fixture("type111-green-64x64.h264.b64")
        primary_sender = _start_producer(primary_peer, 110, red, stop_primary, generation * 10000 + 1)
        secondary_sender = _start_producer(secondary_peer, 111, blue, stop_secondary, generation * 10000 + 2)
        if not primary.wait_for_frame(1, 5) or not secondary.wait_for(lambda: secondary.submitted >= 1, 5):
            raise RuntimeError("first_dual_stream_frame_timeout")
        if primary.current.png == secondary.last_rendered_png:
            raise RuntimeError("display_streams_not_independent")
        result["simultaneousIndependentFrames"] = True
        primary_path, secondary_path = _snapshot_png(primary, secondary, output_dir, f"-gen{generation}-initial")
        result["initialDisplay0Sha256"] = hashlib.sha256(primary_path.read_bytes()).hexdigest()
        result["initialDisplay1Sha256"] = hashlib.sha256(secondary_path.read_bytes()).hexdigest()
        if exercise_faults:
            secondary.warning_preempted()
            warning_baseline = secondary.warning_dropped
            if not secondary.wait_for(lambda: secondary.warning_dropped > warning_baseline, 3):
                raise RuntimeError("warning_did_not_preempt_secondary_frames")
            secondary.warning_cleared()
            rendered_before = secondary.submitted
            if not secondary.wait_for(lambda: secondary.submitted > rendered_before, 5):
                raise RuntimeError("secondary_failed_to_resume_after_warning")
            result["warningPreemptionAndResume"] = True
            if secondary.last_rendered_png is None:
                raise RuntimeError("warning_resume_frame_missing")
            _write_png(output_dir / f"display1-type111{f'-gen{generation}-resumed'}.png",
                       secondary.last_rendered_png)
            stop_secondary.set()
            secondary_sender.join(timeout=2)
            if secondary_sender.is_alive():
                raise RuntimeError("secondary_synthetic_source_failed_to_stop")
            secondary_peer.sendall(encode_lab_message(0, b"invalid synthetic H264", timestamp=generation * 10000 + 999))
            if runtime.wait_for_event("stream_stopped", 5, 111) is None:
                raise RuntimeError("secondary_decode_failure_not_isolated")
            delegation.teardown_secondary(generation)
            if receiver.secondary is not None or receiver.primary is None or receiver.primary.closed:
                raise RuntimeError("secondary_failure_changed_primary_ownership")
            primary_baseline = primary.frames
            if not primary.wait_for_frame(primary_baseline + 1, 5):
                raise RuntimeError("primary_did_not_continue_after_secondary_failure")
            result["secondaryFailureIsolation"] = True
            result["primaryRemainedActive"] = True
            if not delegation.primary.active:
                raise RuntimeError("mock_stock_primary_was_unexpectedly_revoked")
            if secondary.current is not None:
                raise RuntimeError("secondary_display_not_cleared_after_failure")
            # Save only the still-active primary output. A stale secondary
            # last-good frame must not be presented as live post-fault output.
            _write_png(output_dir / f"display0-type110-gen{generation}-postfault.png",
                       primary.current.png)
        else:
            stop_secondary.set()
            secondary_sender.join(timeout=2)
            result["reconnectDemonstrated"] = generation > 1
            _snapshot_png(primary, secondary, output_dir, f"-gen{generation}-initial")
        result["rendererFrameBytes"] = len(secondary.last_rendered_png or b"")
        result["rendererSafeAreaProvenance"] = "SYNTHETIC_TEST_ONLY"
        return result
    finally:
        stop_primary.set()
        stop_secondary.set()
        for worker in (primary_sender, secondary_sender):
            if worker is not None:
                worker.join(timeout=2)
        primary_peer.close()
        secondary_peer.close()
        runtime_closed = runtime.close()
        delegation_revoked = delegation.revoke_session(generation)
        if not runtime_closed:
            raise RuntimeError("runtime_resource_cleanup_incomplete")
        if not delegation_revoked:
            raise RuntimeError("mock_stock_session_revocation_failed")
        if runtime.receiver.snapshot().sessions != 0:
            raise RuntimeError("receiver_resources_remain_after_close")


def _write_page(output_dir: Path, report: dict[str, Any]) -> None:
    primary = "display0-type110-gen2-initial.png"
    secondary = "display1-type111-gen2-initial.png"
    page = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>ClarityLink CL-IMP-11 Dual Display Lab</title>
<style>
body{{margin:0;background:#101923;color:#edf3f8;font:16px system-ui,sans-serif}}
header{{padding:18px 24px;background:#192837;border-bottom:2px solid #00d2ff}}
header strong{{color:#ffcd4a}}main{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;padding:20px}}
section{{background:#172430;border:1px solid #486071;border-radius:10px;padding:12px}}
h2{{margin:0 0 10px;font-size:18px}}img{{display:block;width:100%;aspect-ratio:5/3;object-fit:contain;background:#05080a;border:2px solid #00d2ff}}
.tag{{color:#ffcd4a;font-weight:700}}small{{display:block;margin-top:8px;color:#b7c7d2}}@media(max-width:720px){{main{{grid-template-columns:1fr}}}}
</style>
<header><strong>{SYNTHETIC_LABEL}</strong><div>CL-IMP-11 two-stream demonstration · generation 2 after reconnect · model-only</div></header>
<main><section><h2>Display 0 simulator — mock Type110 primary</h2><img src="{primary}" alt="Synthetic red Type110 fixture rendered in Display 0 simulator"><small>Independent Type110 test fixture. A mock stock-session model retains primary ownership; not a factory Honda display.</small></section>
<section><h2>Display 1 simulator — ClarityLink Type111 output</h2><img src="{secondary}" alt="Synthetic blue Type111 fixture after the ClarityLink renderer"><small>Independent H.264 fixture decoded and passed through the existing synthetic safe-area renderer. No mirroring; no authentic navigation content or physical scanout.</small></section></main>
</html>'''
    (output_dir / "index.html").write_text(page, encoding="utf-8")
    (output_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_lab(output_dir: Path, *, ffmpeg: str | None = None) -> dict[str, Any]:
    requested_path = output_dir.absolute()
    if any(part.is_symlink() for part in (requested_path, *requested_path.parents)):
        raise ValueError("lab output path must not traverse symbolic links")
    output_dir = output_dir.resolve()
    if output_dir.name != "cl-imp-11" or output_dir.parent.name != "build":
        raise ValueError("lab artifacts must be written under the build directory")
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir():
            raise ValueError("lab output path must be a regular directory")
        # Replace only known artifacts from this demo. Never recursively
        # delete caller-owned content in a supplied output directory.
        names = {"index.html", "report.json"}
        for generation in (1, 2):
            for suffix in ("-initial", "-resumed", "-postfault"):
                names.add(f"display0-type110-gen{generation}{suffix}.png")
                names.add(f"display1-type111-gen{generation}{suffix}.png")
        for name in names:
            artifact = output_dir / name
            if artifact.is_symlink():
                artifact.unlink()
            elif artifact.exists():
                if not artifact.is_file():
                    raise ValueError("known lab artifact path is not a regular file")
                artifact.unlink()
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = ffmpeg or shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg_unavailable")
    receiver = Receiver(clear_lab=True, primary_dimensions=(800, 480), secondary_dimensions=(800, 480))
    primary = PrimaryLabOutput()
    secondary = RenderedSecondaryOutput(ffmpeg_path)
    receiver.primary_display = primary
    receiver.display = secondary
    first = _run_generation(receiver, primary, secondary, 1, output_dir, exercise_faults=True)
    if receiver.generation != 1:
        raise RuntimeError("first_generation_not_closed")
    second = _run_generation(receiver, primary, secondary, 2, output_dir, exercise_faults=False)
    if second["generation"] <= first["generation"]:
        raise RuntimeError("session_generation_did_not_advance")
    report = {
        "milestone": "CL-IMP-11", "status": "PASS", "evidence": "MODEL_ONLY",
        "label": SYNTHETIC_LABEL, "display0": first, "display1": second,
        "reconnect": {"generation1": 1, "generation2": 2, "passed": True},
        "physicalScanout": "UNPROVEN", "hondaIntegration": "DISABLED",
        "iphoneAuthentication": "NOT_PERFORMED", "stockDelegation": "MOCK_ONLY",
        "resourcesAfterFinalClose": vars(receiver.snapshot()),
    }
    _write_page(output_dir, report)
    return report


def main() -> int:
    output_dir = ROOT / "build/cl-imp-11"
    report = run_lab(output_dir)
    print(json.dumps({"status": report["status"], "evidence": report["evidence"],
                      "output": str(output_dir), "display0": report["display0"],
                      "display1": report["display1"], "physicalScanout": report["physicalScanout"],
                      "hondaIntegration": report["hondaIntegration"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
