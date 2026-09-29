# Next action

**Offline: resolve Honda's display capability advertisement and alternate-screen request gating, then determine whether the phone can request Type 111.** Step 27 proves Setup's exact mutable response reaches binary-plist serialization and the HTTP send path, and recovers the caller-owned response lifetime. The latest structural mutation candidate is immediately after Setup and before `_requestSendPlistResponse`; do not implement a live hook or negotiation until capability signaling, Type-111 schema/security, and request gating are evidenced. Keep the `mc_dev_attach("CarPlay Screen")` registry fallback-only and keep ptrace paused.

See `research/carplay/honda-altscreen-gap-analysis.md`, `research/carplay/claritylink-display-b-architecture.md`, and `step-reports/25-altscreen-prior-art-pivot.md`.


Registry observation remains paused: do not retry `process_vm_readv` (ENOSYS), and do not use the ptrace reader until its single-thread pause, sibling-thread race, signal-forwarding, and detach-failure limits receive a separate review. See `research/carplay/ptrace-registry-reader.md` and `step-reports/24-ptrace-registry-reader.md`.
