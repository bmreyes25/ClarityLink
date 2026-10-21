#!/usr/bin/env python3
"""Evaluate the predeclared CL-R12 API17 short-run acceptance gates."""
import re
import sys


def result_line(path):
    text = open(path, encoding="utf-8").read()
    lines = [line for line in text.splitlines() if "R12B_RESULT mode=" in line]
    if not lines:
        raise ValueError("no R12B_RESULT record")
    return dict(re.findall(r"([a-zA-Z0-9_]+)=([^\s]+)", lines[-1]))


def main():
    values = result_line(sys.argv[1])
    failures = []

    def number(name):
        return float(values[name])

    checks = {
        "result_has_no_error": values.get("error") == "null",
        "offered_rate_29_to_31_fps": 29 <= number("offered_fps") <= 31,
        "delivered_rate_at_least_27_fps": number("delivered_fps") >= 27,
        "p95_at_most_50_ms": number("latency_p95_ms") <= 50,
        "p99_at_most_100_ms": number("latency_p99_ms") <= 100,
        "valid_frame_drop_rate_at_most_10_percent": number("dropped") / max(1, number("offered")) <= 0.10,
        "no_pixel_mismatch": number("pixel_mismatches") == 0,
        "no_transport_error": number("transport_errors") == 0,
        "no_host_rejection": number("host_rejected") == 0,
        "frame_accounting_balances": number("offered") == number("delivered") + number("dropped") + number("host_rejected") + number("transport_errors"),
        "bounded_queue": number("queue_high_water") <= 1,
        "partial_payload_rejected": values.get("partial_frame_rejected") == "true",
        "producer_memoryfiles_balanced": number("source_memoryfiles_created") == number("source_memoryfiles_closed") and number("source_memoryfiles_open") == 0,
        "host_memoryfiles_balanced": number("host_memoryfiles_created") == number("host_memoryfiles_closed") and number("host_memoryfiles_open") == 0,
        "producer_fd_returns_within_two": number("source_fd_final") <= number("source_fd_base") + 2,
        "host_fd_returns_within_two": number("host_fd_final") <= number("host_fd_base") + 2,
        "producer_java_heap_delta_within_8mib": abs(number("source_java_final") - number("source_java_base")) <= 8 * 1024 * 1024,
        "producer_native_heap_delta_within_8mib": abs(number("source_native_final") - number("source_native_base")) <= 8 * 1024 * 1024,
        "host_java_heap_delta_within_8mib": abs(number("host_java_final") - number("host_java_base")) <= 8 * 1024 * 1024,
        "host_native_heap_delta_within_8mib": abs(number("host_native_final") - number("host_native_base")) <= 8 * 1024 * 1024,
        "final_stats_received": values.get("final_stats") == "true",
    }
    for name, passed in checks.items():
        print(f"{name}={'PASS' if passed else 'FAIL'}")
        if not passed:
            failures.append(name)
    if failures:
        print("CL_R12_PERFORMANCE_GATE=FAIL " + ",".join(failures))
        return 1
    print("CL_R12_PERFORMANCE_GATE=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError) as error:
        print(f"CL_R12_PERFORMANCE_GATE=INVALID {error}")
        raise SystemExit(2)
