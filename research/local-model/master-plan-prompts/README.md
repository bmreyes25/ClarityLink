# Master plan Steps 1–5: standalone execution prompts

Use one fresh Ollama-backed Codex task per offline step, with local shell/file tools. Plain Ollama chat only produces advice. Copy the entire linked prompt, not the long project conversation. Preserve the 65,536-token configuration; keep initial context around 16,000 tokens or less and use targeted excerpts. These prompts map to the numbered master plan, unlike the older post-acquisition prompt sheet.

| Step | Work | Assigned model |
|---|---|---|
| [1](STEP_01.md) | Audit existing Git/evidence baseline (already complete; reconcile) | Local Ollama |
| [2](STEP_02.md) | Infotainment twin and replay checks | Local Ollama |
| [3](STEP_03.md) | Prepare and bench-test coexistence probe | Local Ollama |
| [4](STEP_04.md) | Reviewed parked-car coexistence measurement | GPT-6 Sol Codex |
| [5](STEP_05.md) | Static Identification reconstruction and capture design | Local Ollama |

Every step requires a detailed sanitized change log, actual checks, GitHub checkpoint/push verification and supervising Codex acceptance review. Pending/failure checkpoints must say so. All future vehicle work, including capture proposed in Step 5, belongs to GPT-6 Sol Codex with the applicable approval/recovery gates. No prompt grants blanket vehicle-write permission. Steps 2, 3 and 5 can proceed offline; Step 4 waits for its exact reviewed artifact and parked session. No firmware original may be changed; modifications use separate ignored derivative copies.
