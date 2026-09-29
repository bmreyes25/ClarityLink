# Next action

**Offline: recover the indirect caller/function-pointer path for `AirPlayReceiverSessionScreen_CopyDisplaysInfo`, then trace its returned dictionary to a parent, serializer, and protocol phase.** Step 28 recovered the literal local fields, but phone-facing capability signaling remains unproven. In parallel, recover the request-side `streams[].type` parser and display-to-stream correlation from the Setup dispatcher evidence. Do not implement a live hook or negotiation until both capability and Type-111 routing are evidenced. Keep `mc_dev_attach` registry fallback-only and ptrace paused.

See `step-reports/28-honda-display-capability-gating.md` and the Step 28 notes under `research/carplay/`.

Registry observation remains paused: do not retry `process_vm_readv` (ENOSYS), and do not use the ptrace reader until its single-thread pause, sibling-thread race, signal-forwarding, and detach-failure limits receive a separate review. See `research/carplay/ptrace-registry-reader.md` and `step-reports/24-ptrace-registry-reader.md`.
