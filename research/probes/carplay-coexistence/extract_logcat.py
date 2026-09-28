#!/usr/bin/env python3
"""Extract this probe's JSONL events from a saved Android logcat text file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_trace import evaluate


def extract(raw: str) -> list[dict]:
    events = []
    for line_number, line in enumerate(raw.splitlines(), start=1):
        if "ClarityCoexistence" not in line:
            continue
        start = line.find("{")
        if start < 0:
            continue
        try:
            event = json.loads(line[start:])
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON in logcat line {line_number}: {error}") from error
        if isinstance(event, dict) and "event" in event:
            events.append(event)
    if not events:
        raise ValueError("no ClarityCoexistence JSON events found")
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logcat", type=Path)
    parser.add_argument("jsonl", type=Path)
    args = parser.parse_args()
    events = extract(args.logcat.read_text(errors="replace"))
    result = evaluate(events)
    args.jsonl.write_text("".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
