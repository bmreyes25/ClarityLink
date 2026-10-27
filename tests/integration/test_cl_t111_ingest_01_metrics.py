"""CL-T111-INGEST-01 observed host-side measurements (NOT Honda acceptance thresholds).

Measures the offline synthetic path on whatever machine runs it. Assertions are
resource invariants only; timings are printed (run with ``-s``) and, when
``CL_T111_METRICS_OUT`` is set, written as JSON. Nothing here is an Android,
Honda or real-iPhone performance claim.
"""
import json
import os
import statistics
import threading
import tracemalloc
from time import perf_counter

import t111_synth as synth
from claritylink_jmcs.decoder import FFmpegDecoder
from failsafe_coordinator import Fault
from type111_ingest import Type111IngestPipeline

FRAMES = 12
CYCLES = 25
OUTPUT = (800, 480)


def _stats(samples):
    ordered = sorted(samples)
    return {"n": len(ordered), "median_ms": round(statistics.median(ordered) * 1000, 2),
            "max_ms": round(ordered[-1] * 1000, 2)}


def test_observed_ingest_metrics_and_repeated_cycle_resource_stability():
    stream = synth.SyntheticStream(4)
    clock = synth.Clock()
    pipe = Type111IngestPipeline(lab_mode=True, clock=clock, receiver_kwargs={
        "primary_dimensions": OUTPUT, "secondary_dimensions": OUTPUT})
    client = synth.start_type111(pipe)
    client.sendall(stream.config_message())
    assert pipe.pump_frame().accepted

    decoder, decode_times = FFmpegDecoder(), []
    for index in range(FRAMES):
        started = perf_counter()
        decoder.decode(stream.annexb[index % 4], index + 1, 1, OUTPUT)
        decode_times.append(perf_counter() - started)
    decoder.close()

    pump_times = []
    tracemalloc.start()
    for index in range(FRAMES):
        client.sendall(stream.frame_message(index % 4, timestamp=index + 1))
        started = perf_counter()
        assert pipe.pump_frame().accepted
        pump_times.append(perf_counter() - started)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    started = perf_counter()
    pipe.output.fail_closed("metrics probe")
    withdrawal = perf_counter() - started
    assert pipe.host.visible_content is None
    started = perf_counter()
    pipe.disconnect(Fault.CARPLAY_ENDED)
    cleanup = perf_counter() - started
    client.close()
    assert pipe.residual() == ()

    threads, fds = threading.active_count(), len(os.listdir("/dev/fd"))
    for cycle in range(CYCLES):
        cycle_client = synth.start_type111(pipe)
        cycle_client.sendall(stream.config_message() + stream.frame_message(cycle % 4))
        assert pipe.pump_frame().accepted and pipe.pump_frame().accepted
        pipe.disconnect(Fault.CARPLAY_ENDED)
        cycle_client.close()
        assert pipe.residual() == ()
    assert (threading.active_count(), len(os.listdir("/dev/fd"))) == (threads, fds)

    report = {
        "scope": "host-only synthetic measurement; not an Android/Honda/iPhone result",
        "output": f"{OUTPUT[0]}x{OUTPUT[1]}",
        "ffmpeg_decode_incl_scale": _stats(decode_times),
        "png_to_rgb24_conversion": _stats(list(pipe.output.convert_seconds)),
        "pump_frame_end_to_end": _stats(pump_times),
        "withdrawal_ms": round(withdrawal * 1000, 3),
        "disconnect_cleanup_ms": round(cleanup * 1000, 2),
        "peak_python_alloc_mib_over_frames": round(peak_bytes / 2**20, 2),
        "max_pending_frames_bound": 2,
        "cycles": CYCLES, "threads_before_after": [threads, threading.active_count()],
        "fds_before_after": [fds, len(os.listdir("/dev/fd"))],
    }
    print("\nCL_T111_METRICS " + json.dumps(report, sort_keys=True))
    target = os.environ.get("CL_T111_METRICS_OUT")
    if target:
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
