#!/usr/bin/env python3
"""Send a small, curated ClarityLab step packet to loopback Ollama only."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "research/plans/CARPLAY_SECOND_DISPLAY_REVIEW.plan.md"
BRIEF = ROOT / "research/local-model/PROJECT_BRIEF.md"
STATUS = ROOT / "research/plans/STEP_STATUS.md"
POLICY = ROOT / "research/plans/STEP_COMPLETION_POLICY.md"
MODEL = "clarity-research:latest"
MAX_CHARS = 48000  # Conservative ~16k-token input; 65,536 tokens are configured.
SOURCES = {
    "F-B": ["research/acquisition/FORENSIC_STATUS_20260925.md", "research/acquisition/STORAGE_MAP.md"],
    "2": ["research/simulator/INFOTAINMENT_TWIN_SCOPE.md", "research/simulator/README.md", "research/simulator/sample-dual-screen.jsonl", "research/simulator/test-dual-screen.js"],
    "3": ["research/probes/decoder-capacity/README.md", "research/probes/decoder-capacity/src/org/claritylab/decoderprobe/DecoderCapacityProbeActivity.java", "research/captures/20260925T150706Z-SESSION_FINDINGS.md"],
    "4": ["research/probes/decoder-capacity/ON_CAR_RUN_CARD.md"],
    "5": ["research/native/receiver-multidisplay-audit.md", "research/NATIVE_CARPLAY_CLUSTER.md"],
    "6": ["research/native/receiver-multidisplay-audit.md"],
    "7": ["research/native/receiver-multidisplay-audit.md", "research/REPORT.md"],
    "8": ["research/plans/NATIVE_CLUSTER_IMPLEMENTATION_GATES.md"],
    "9": ["research/simulator/README.md"],
    "10": ["research/simulator/README.md"],
    "11": ["research/plans/NATIVE_CLUSTER_IMPLEMENTATION_GATES.md"],
    "12": ["research/simulator/README.md"],
}


def numbered_excerpt(path: Path, limit: int) -> str:
    lines = path.read_text().splitlines()
    text = "\n".join(f"{i}: {line}" for i, line in enumerate(lines, 1))
    if len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0] + "\n[EXCERPT TRUNCATED]"
    return f"SOURCE {path.relative_to(ROOT)}\n{text}\n"


def plan_section(step: str) -> str:
    lines = PLAN.read_text().splitlines()
    title = re.compile(rf"^## (?:{re.escape(step)}\.|{re.escape(step)}\.)")
    start = next((i for i, line in enumerate(lines) if title.match(line)), None)
    if start is None:
        raise ValueError(f"plan step not found: {step}")
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))


def packet(step: str, question: str) -> str:
    if step not in {"1", "F-A", "F-B", *[str(i) for i in range(2, 13)]}:
        raise ValueError("unknown plan step")
    sections = [
        "Use only these sources. Cite path:line. Give status, evidence gaps, the next available offline action, and verification. Mention later car requirements only if they block that action. Do not claim a step passed without exit evidence; do not infer raw iAP2 payloads from ordinary runtime snapshots.\n",
        numbered_excerpt(BRIEF, 6500),
        numbered_excerpt(STATUS, 6500),
        numbered_excerpt(POLICY, 6500),
        f"SOURCE {PLAN.relative_to(ROOT)}\n{plan_section(step)}\n",
    ]
    for relative in SOURCES.get(step, []):
        path = ROOT / relative
        if path.is_file():
            sections.append(numbered_excerpt(path, 12000))
    sections.append(f"USER TASK: {question or 'Assess this step and give the next concrete offline action.'}")
    result = "\n".join(sections)
    if len(result) > MAX_CHARS:
        raise ValueError("packet exceeds conservative context budget; narrow the sources")
    return result


def ask_local(prompt: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
    }).encode()
    request = urllib.request.Request("http://127.0.0.1:11434/api/chat", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    print(f"ollama_done_reason={result.get('done_reason')} prompt_tokens={result.get('prompt_eval_count')} output_tokens={result.get('eval_count')}", file=sys.stderr)
    if result.get("done_reason") == "length":
        raise RuntimeError("local model hit its output cap; narrow the question or increase reviewed output budget")
    return result["message"]["content"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--step", required=True)
    parser.add_argument("--question", default="")
    parser.add_argument("--show-prompt", action="store_true")
    args = parser.parse_args()
    prompt = packet(args.step, args.question)
    print(f"packet_chars={len(prompt)} conservative_input_token_estimate={(len(prompt)+2)//3} model={MODEL}")
    print(prompt if args.show_prompt else ask_local(prompt))
