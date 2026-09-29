# Next action

**Offline: trace the caller and registered session delegate for `AirPlayReceiverSessionSetup` through the actual phone-facing serializer and network send.** Step 26 recovered Honda's mutable SETUP response dictionary, `streams` CFArray, stock `type=110`, and per-entry dynamic `dataPort`; it did not identify the transport encoder, out-object ownership, or safe hook ABI. Recover those exact edges before choosing or implementing any interposer. Keep the `mc_dev_attach("CarPlay Screen")` registry fallback-only and keep ptrace paused.

See `research/carplay/honda-altscreen-gap-analysis.md`, `research/carplay/claritylink-display-b-architecture.md`, and `step-reports/25-altscreen-prior-art-pivot.md`.


Registry observation remains paused: do not retry `process_vm_readv` (ENOSYS), and do not use the ptrace reader until its single-thread pause, sibling-thread race, signal-forwarding, and detach-failure limits receive a separate review. See `research/carplay/ptrace-registry-reader.md` and `step-reports/24-ptrace-registry-reader.md`.
