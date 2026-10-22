#!/usr/bin/env python3
"""Summarize repeated CL-R12 baseline/candidate short runs from a receipt directory.

Informational only: it never decides an acceptance gate (tools/check_cl_r12_perf_gate.py
does that, unchanged). It reports every run, the median of each metric per variant, and
whether the two variants are distinguishable at all, so a throughput difference caused by
a noisy shared emulator is not read as a renderer regression, and a real regression is
not hidden behind a single lucky run.

A metric is called distinguishable only when the ranges of the two variants do not
overlap. With three runs each that happens by chance one time in ten, so it is evidence
to investigate, not proof.
"""
import json
import re
import statistics
import sys
from pathlib import Path

METRICS = {  # name -> True when a larger value is better
    "delivered_fps": True,
    "latency_p50_ms": False,
    "latency_p95_ms": False,
    "latency_p99_ms": False,
    "drop_fraction": False,
    "source_fd_delta": False,
}
RUN_NAME = re.compile(r"^perf-(baseline|optimized)(?:-r(\d+))?-logcat\.txt$")


def parse_result(path: Path):
    lines = [l for l in path.read_text(encoding="utf-8", errors="replace").splitlines()
             if "R12B_RESULT mode=short" in l]
    if not lines:
        return None
    v = dict(re.findall(r"([a-zA-Z0-9_]+)=([^\s]+)", lines[-1]))
    try:
        offered = float(v["offered"])
        return {
            "delivered_fps": float(v["delivered_fps"]),
            "latency_p50_ms": float(v["latency_p50_ms"]),
            "latency_p95_ms": float(v["latency_p95_ms"]),
            "latency_p99_ms": float(v["latency_p99_ms"]),
            "drop_fraction": float(v["dropped"]) / max(1.0, offered),
            "source_fd_delta": float(v["source_fd_final"]) - float(v["source_fd_base"]),
            "host_fd_delta": float(v["host_fd_final"]) - float(v["host_fd_base"]),
            "pixel_mismatches": float(v["pixel_mismatches"]),
            "transport_errors": float(v["transport_errors"]),
            "error": v.get("error"),
        }
    except (KeyError, ValueError):
        return None


def collect(receipt: Path):
    runs = {"baseline": {}, "optimized": {}}
    for path in sorted(receipt.glob("perf-*-logcat.txt")):
        m = RUN_NAME.match(path.name)
        if not m:
            continue
        parsed = parse_result(path)
        if parsed is not None:
            runs[m.group(1)][int(m.group(2) or 1)] = parsed
    return runs


MIN_RUNS_PER_VARIANT = 3


def compare(base, cand, larger_is_better):
    if len(base) < MIN_RUNS_PER_VARIANT or len(cand) < MIN_RUNS_PER_VARIANT:
        return "INSUFFICIENT_RUNS"   # one pair on a shared emulator says nothing about the renderer
    if larger_is_better:
        if min(cand) > max(base):
            return "CANDIDATE_BETTER"
        if max(cand) < min(base):
            return "CANDIDATE_WORSE"
    else:
        if max(cand) < min(base):
            return "CANDIDATE_BETTER"
        if min(cand) > max(base):
            return "CANDIDATE_WORSE"
    return "NOT_DISTINGUISHABLE"


def summarize(receipt: Path):
    runs = collect(receipt)
    out = {"runs": {k: {str(i): r for i, r in sorted(v.items())} for k, v in runs.items()},
           "metrics": {}, "integrity": {}}
    for name, larger in METRICS.items():
        b = [r[name] for r in runs["baseline"].values()]
        c = [r[name] for r in runs["optimized"].values()]
        out["metrics"][name] = {
            "baseline_median": statistics.median(b) if b else None,
            "candidate_median": statistics.median(c) if c else None,
            "baseline_values": b, "candidate_values": c,
            "verdict": compare(b, c, larger),
        }
    for variant, label in (("baseline", "baseline"), ("optimized", "candidate")):
        rs = list(runs[variant].values())
        out["integrity"][label] = {
            "runs": len(rs),
            "pixel_mismatches": sum(r["pixel_mismatches"] for r in rs),
            "transport_errors": sum(r["transport_errors"] for r in rs),
            "errors": [r["error"] for r in rs if r["error"] not in (None, "null")],
        }
    return out


def to_markdown(summary):
    lines = ["| metric | baseline median | candidate median | baseline runs | candidate runs | verdict |",
             "|---|---|---|---|---|---|"]
    fmt = lambda xs: ", ".join("%.3f" % x for x in xs)
    for name, m in summary["metrics"].items():
        bm = "n/a" if m["baseline_median"] is None else "%.3f" % m["baseline_median"]
        cm = "n/a" if m["candidate_median"] is None else "%.3f" % m["candidate_median"]
        lines.append(f"| {name} | {bm} | {cm} | {fmt(m['baseline_values'])} | {fmt(m['candidate_values'])} | {m['verdict']} |")
    return "\n".join(lines)


def main(argv):
    if len(argv) != 2:
        print("usage: summarize_cl_r12_ab.py <receipt-dir>", file=sys.stderr)
        return 2
    summary = summarize(Path(argv[1]))
    print(to_markdown(summary))
    print(json.dumps(summary["integrity"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
