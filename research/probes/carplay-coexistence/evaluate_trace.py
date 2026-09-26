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
    inputs: dict[int, int] = {}
    outputs: dict[int, int] = {}
    format_ok = False
    eos = False
    errors = []
    last_output_ns = -1
    last_input_ns = -1
    gaps_ms = []
    for event in events[1:]:
        kind = event.get("event")
        if kind == "input":
            pts, now = event.get("pts_us"), event.get("mono_ns")
            if not isinstance(pts, int) or pts < 0 or pts in inputs or not isinstance(now, int) or now < 0:
                raise ValueError("invalid or duplicate input PTS/timestamp")
            if now <= last_input_ns:
                raise ValueError("non-monotonic input timestamp")
            inputs[pts] = now
            last_input_ns = now
        elif kind == "output":
            pts, now = event.get("pts_us"), event.get("mono_ns")
            if not isinstance(pts, int) or pts < 0 or pts in outputs or not isinstance(now, int) or now < 0:
                raise ValueError("invalid output PTS/timestamp")
            if now <= last_output_ns:
                raise ValueError("non-monotonic output timestamp")
            if last_output_ns >= 0:
                gaps_ms.append((now - last_output_ns) / 1_000_000)
            last_output_ns = now
            outputs[pts] = now
        elif kind == "format":
            format_ok = event.get("width") == 800 and event.get("height") == 480
        elif kind == "eos":
            eos = True
        elif kind == "error":
            errors.append(str(event.get("message", "codec error")))
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
    if submitted > 1:
        input_times = list(inputs.values())
        expected_span_ns = (planned - 1) * 1_000_000_000 / 15
        if input_times[-1] - input_times[0] < expected_span_ns - 250_000_000:
            reasons.append("input run shorter than planned duration")
    if produced < required:
        reasons.append("output below 95% of submitted frames")
    if max_gap_ms is None or max_gap_ms > 250:
        reasons.append("missing output cadence or gap over 250 ms")
    if not format_ok:
        reasons.append("800x480 output format not confirmed")
    if not eos:
        reasons.append("EOS/drain not confirmed")
    if errors:
        reasons.append("codec error")
    return {
        "decoder_gate": "PASS" if not reasons else "FAIL",
        "submitted": submitted,
        "produced": produced,
        "required_output": required,
        "output_percent": round(100 * produced / submitted, 2) if submitted else 0,
        "max_output_gap_ms": max_gap_ms,
        "format_ok": format_ok,
        "eos": eos,
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
