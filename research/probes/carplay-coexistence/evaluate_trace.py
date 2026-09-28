#!/usr/bin/env python3
"""Score a future bounded decoder trace; does not contact the car."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def evaluate(events: list[dict]) -> dict[str, object]:
    if not events or events[0].get("event") != "start":
        raise ValueError("trace must begin with start")
    start = events[0]
    planned = start.get("planned_frames")
    if not isinstance(planned, int) or planned <= 0:
        raise ValueError("invalid planned frame count")
    if start.get("width") != 800 or start.get("height") != 480 or start.get("fps") != 15:
        raise ValueError("trace is not the reviewed 800x480/15fps fixture")
    codec_name = start.get("codec")
    start_ns = start.get("mono_ns")
    if not isinstance(start_ns, int) or start_ns < 0:
        raise ValueError("start event requires monotonic nanosecond timestamp")
    inputs: dict[int, int] = {}
    outputs: dict[int, int] = {}
    format_ok = False
    eos = False
    errors = []
    reported_drops = 0
    last_output_ns = -1
    last_input_ns = -1
    last_event_ns = start_ns
    gaps_ms = []
    format_events = []
    eos_confirmed = False
    eos_seen = False
    for event in events[1:]:
        kind = event.get("event")
        if kind == "input":
            if eos_seen:
                raise ValueError("input observed after EOS")
            pts, now = event.get("pts_us"), event.get("mono_ns")
            if not isinstance(pts, int) or pts < 0 or pts in inputs or not isinstance(now, int) or now < 0:
                raise ValueError("invalid or duplicate input PTS/timestamp")
            if now <= last_input_ns:
                raise ValueError("non-monotonic input timestamp")
            if now <= last_event_ns:
                raise ValueError("non-monotonic trace event timestamp")
            inputs[pts] = now
            last_input_ns = now
            last_event_ns = now
        elif kind == "output":
            if eos_seen:
                raise ValueError("output observed after EOS drain marker")
            pts, now = event.get("pts_us"), event.get("mono_ns")
            if not isinstance(pts, int) or pts < 0 or pts in outputs or not isinstance(now, int) or now < 0:
                raise ValueError("invalid output PTS/timestamp")
            if now <= last_output_ns:
                raise ValueError("non-monotonic output timestamp")
            if now <= last_event_ns:
                raise ValueError("non-monotonic trace event timestamp")
            if pts not in inputs:
                raise ValueError("output PTS was not submitted before output")
            if last_output_ns >= 0:
                gaps_ms.append((now - last_output_ns) / 1_000_000)
            last_output_ns = now
            last_event_ns = now
            outputs[pts] = now
        elif kind == "format":
            valid_format = event.get("width") == 800 and event.get("height") == 480
            format_events.append(valid_format)
            format_ok = all(format_events)
        elif kind == "eos":
            if eos_seen:
                raise ValueError("duplicate EOS marker")
            eos_seen = True
            if event.get("confirmed") is not True:
                continue
            eos = True
            eos_confirmed = True
        elif kind == "error":
            errors.append(str(event.get("message", "codec error")))
        elif kind == "dropped":
            reported_drops += 1
        elif kind in {"metric", "thermal", "summary", "cleanup", "cleanup_warning"}:
            continue
        else:
            raise ValueError(f"unknown trace event: {kind}")
    if len(inputs) > planned:
        raise ValueError("more submitted inputs than planned")
    unmatched = set(outputs) - set(inputs)
    if unmatched:
        raise ValueError("output PTS absent from submitted input")
    submitted = len(inputs)
    produced = len(outputs)
    required = math.ceil(submitted * 0.95)
    max_gap_ms = max(gaps_ms, default=None)
    reasons = []
    if submitted != planned:
        reasons.append("submitted fewer than planned frames")
    duration_ok = planned == 900 and start.get("duration_ms") == 60000 and submitted == 900
    if submitted > 1:
        input_times = list(inputs.values())
        if input_times[0] - start_ns > 250_000_000:
            duration_ok = False
            reasons.append("first input started too late")
        if input_times[-1] - start_ns < 59_750_000_000:
            duration_ok = False
            reasons.append("input run shorter than planned duration")
    if not duration_ok:
        reasons.append("not the declared 900-frame/60-second candidate run")
    if produced < required:
        reasons.append("output below 95% of submitted frames")
    if max_gap_ms is None or max_gap_ms > 250:
        reasons.append("missing output cadence or gap over 250 ms")
    if not format_ok:
        reasons.append("800x480 output format not confirmed")
    if not eos:
        reasons.append("EOS/drain not confirmed")
    if not eos_confirmed or submitted != planned:
        reasons.append("incomplete input or unconfirmed EOS drain")
    if codec_name != "OMX.Nvidia.h264.decode":
        reasons.append("NVIDIA hardware decoder identity not confirmed")
    if errors:
        reasons.append("codec error")
    quality_ok = (submitted == planned and produced >= required and max_gap_ms is not None and
                  max_gap_ms <= 250 and format_ok and eos_confirmed and not errors and
                  codec_name == "OMX.Nvidia.h264.decode")
    return {
        "decoder_gate": "PASS" if quality_ok and duration_ok else "FAIL",
        "sample_quality_gate": "PASS" if quality_ok else "FAIL",
        "full_duration_ok": duration_ok,
        "submitted": submitted,
        "produced": produced,
        "required_output": required,
        "output_percent": round(100 * produced / submitted, 2) if submitted else 0,
        "max_output_gap_ms": max_gap_ms,
        "format_ok": format_ok,
        "eos": eos,
        "codec": codec_name or "unavailable",
        "reported_drops": reported_drops,
        "missing_output_pts": sorted(set(inputs) - set(outputs)),
        "errors": errors,
        "reasons": reasons,
        "carplay_picture_voice_verdict": "UNOBSERVED — separate parked observation required",
    }


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(read_jsonl(args.trace)), indent=2))
