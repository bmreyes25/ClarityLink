# Next action

**Offline: locate the exact `jmcs` ELF matching the saved VA map, then produce complete disassembly/xref evidence for indirect references to `AirPlayReceiverSessionScreen_CopyDisplaysInfo` and for `_connectionHandleMessage` through `AirPlayReceiverSessionSetup` request reads.** Step 29 confirmed the existing evidence gap: tracked excerpts cannot establish the function-pointer table/caller or incoming stream-type parsing. Do not implement a live hook or negotiation until the phone-facing capability path and Type-111 request behavior/correlation are evidenced. Keep `mc_dev_attach` registry fallback-only and ptrace paused.

See `step-reports/29-display-caller-and-stream-parser.md`, its Step 29 notes under `research/carplay/`, and `step-reports/28-honda-display-capability-gating.md`.

Registry observation remains paused: do not retry `process_vm_readv` (ENOSYS), and do not use the ptrace reader until its single-thread pause, sibling-thread race, signal-forwarding, and detach-failure limits receive a separate review. See `research/carplay/ptrace-registry-reader.md` and `step-reports/24-ptrace-registry-reader.md`.
