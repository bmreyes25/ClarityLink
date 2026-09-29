# Next action

**Design a minimal read-only ptrace registry reader offline.** The one authorized `process_vm_readv` attempt returned `ENOSYS`, the process remained alive, the temporary executable was removed, and ADB was disconnected. Do not retry `process_vm_readv` or perform a live ptrace attach as part of the design step.

The design must specify exactly which thread(s) would stop, how reads use only PEEK operations, how every stopped thread is guaranteed resumed on success/failure/interruption, permission preconditions, a strict read budget, and a recovery path if detach/resume fails. Compare alternatives against the already captured fresh maps and `mc_devs` static offset. See [Step 24](step-reports/24-registry-reader-live-unsupported.md), [reader audit](research/carplay/registry-reader-armv7-build.md), and [local ignored capture](research/captures/registry-reader-live-20260929/).
