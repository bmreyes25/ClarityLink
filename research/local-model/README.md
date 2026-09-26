# Local ClarityLab research model

`clarity-research:latest` is an Ollama profile built from the already-installed `qwen3.6:35b-coding`. It uses the existing model layers and sets a 65,536-token context, 4,096-token response cap, and low temperature. The model metadata advertises a 262,144-token architectural limit, but the **loaded configuration** on this 36 GiB Mac was 65,536; that is the operational limit used here. A larger setting has not been benchmarked and is unnecessary for the current research packets.

The profile's system prompt requires source-linked claims, observed/inferred/unknown separation, offline-first work, and explicit change/recovery gates. It does not give the model filesystem or car access. The `run_step.py` client calls only `http://127.0.0.1:11434/api/chat`; it sends curated text from this repository, not raw firmware, `/data`, screenshots, account data, or entire logs. Its packet is capped at 48,000 characters, a conservative estimate of at most roughly 16,000 input tokens, leaving ample room within the configured context for a response and dialogue. Exact token count varies by text; the printed character-based estimate is only a planning bound.

The client requests `think: false` so hidden reasoning does not consume the 4,096-token response cap. It rejects a response that ends because of the length cap. The first verified F-B run used 4,380 input tokens and 747 output tokens and ended normally. This is a tested prompt size, not a claim that every future packet fits or that the model can retain the whole project across sessions.

From the analysis root:

```sh
ollama create clarity-research:latest -f research/local-model/Modelfile
ollama list
python3 research/local-model/run_step.py --step F-B --show-prompt
python3 research/local-model/run_step.py --step F-B
python3 research/local-model/run_step.py --step 2 --question "What simulator fixture should we add next?"
```

Use one plan step per prompt. Give the model the current plan section, the concise brief, and one or two relevant sanitized evidence documents. For a native symbol question, prepare a short path/offset/function excerpt and verify the answer against the working binary yourself; do not paste gigabytes of disassembly or assume the model remembers earlier chats. Copy a verified finding into the relevant research document before moving to the next step. The CLI response is advice, not an executed plan or a passed gate.

The next practical sequence is: finish F-B when the car is available; meanwhile run Step 2 simulator checks and Step 3 decoder-probe preparation offline; continue Step 5 static Identification analysis in parallel where it does not depend on the missing capture. Do not advance Steps 10–12 on the live car without their separate reviewed artifacts and recovery gates.

Review model suggestions against the cited files before turning them into tasks. During setup, an early Step 2 response incorrectly treated ordinary runtime snapshots as a source of raw iAP2 payloads, and another inferred display bounds from the GPT partition map. The prompts and system profile now state both limits explicitly. The client never executes the model's directions or writes to the vehicle.
