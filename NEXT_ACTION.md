# Next action

**Build and audit the reader with a verified Android ARMv7 toolchain/sysroot.** Step 22 source and synthetic review are complete, but the target build and process_vm_readv ABI remain unverified. Do not execute on the vehicle yet. After a target binary passes static review, separately review a parked session; unsupported or denied syscall means stop, with no ptrace fallback.

Live execution is a later parked-car action after the reader and target permissions are reviewed. Initial iPhone state is disconnected. `process_vm_readv` is preferred if target support and permissions allow; otherwise stop and separately review a ptrace reader. No method has been executed for this design milestone.

See [Step 22](step-reports/22-registry-reader-implementation.md), [reader guide](research/carplay/runtime-registry-reader.md), [runtime read plan](research/carplay/runtime-registry-read-plan.md), [runtime layout](research/carplay/runtime-registry-layout.md), and [runtime registry status](research/carplay/runtime-device-registry.md).
