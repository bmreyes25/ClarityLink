# Prompting the local model through the 12-step plan

The installed model's metadata reports a 262,144-token architectural limit, but Ollama currently loads it at **65,536 tokens** on this 36 GiB Mac. Use 65,536 as the real session limit. The tested F-B packet used 4,380 input tokens and 747 output tokens; a Step 2 packet used about 6,700 input tokens. Keep normal input packets below about 16,000 tokens so there is room for tool outputs, analysis, and a response. Character count divided by three is a conservative rough estimate, not a tokenizer. The model does not retain prior sessions: the files below are its durable memory.

For each step, provide only:

1. [current status](../plans/STEP_STATUS.md) and [brief](PROJECT_BRIEF.md);
2. the single selected section of [the plan](../plans/CARPLAY_SECOND_DISPLAY_REVIEW.plan.md);
3. at most two or three relevant sanitized evidence files or short function/offset excerpts;
4. a single concrete deliverable with an acceptance test.

The `run_step.py` tool builds these packets automatically for advice-only Ollama calls. `--show-prompt` lets a human inspect the exact packet before using it in a tool-capable local coding agent. Never supply an entire disk image, `/data`, route history, account material, or a large disassembly dump as prompt context. Give precise file/function offsets and let the agent inspect only the needed local working copy. Keep raw artifacts outside Git and do not upload them.

For a tool-capable local coding model, a useful first message is:

> Work in `/Users/bmreyes24/ClarityLab/clarity-analysis`. Read `research/plans/STEP_STATUS.md`, `research/local-model/PROJECT_BRIEF.md`, and only the current plan section. Your current task is Step 2: extend the Mac twin from the verified working forensic copy. Do not touch the pristine September 18 backup or any vehicle device. First inspect existing tests and fixtures, then implement one missing offline behavior, run its acceptance test, and update the status index with observed evidence. Keep raw firmware and private data outside Git. State unknowns rather than inferring protocol support or display bounds from storage partitions.

After a step, ask the model to produce a compact handoff: changed paths, test command/result, observed facts, open unknowns, and the next plan gate. Review and write that handoff into the research documents. Start a fresh packet for the next step; do not rely on chat history as persistent memory.

The local model is an assistant, not a source of truth. Early setup runs wrongly inferred that runtime snapshots would reveal raw iAP2 packets, that GPT partitions revealed display bounds, and that 28/30 frames met a 95% threshold. All three were corrected in the profile and brief; the numeric rule is now covered by the offline trace-scorer tests. Validate every causal claim and calculation against captures, firmware functions, or tests before allowing it to guide a car experiment.
