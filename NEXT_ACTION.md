# Next action

**Implement and review a one-shot ARMv7 bounded reader for the `mc_devs` registry.** Step 21's offline ARM disassembly confirms node `+0x04` is list bookkeeping; callback context aliases the interface pointer, and tail append means traversal order is insertion order. The first observation remains registry-only: no live scores initially; resolve slot `+0/+4` offline and evaluate the matcher before considering any second-stage observation. Do not connect to port 5000, alter logging/configuration, or instrument/patch `jmcs`.

Live execution is a later parked-car action after the reader and target permissions are reviewed. Initial iPhone state is disconnected. `process_vm_readv` is preferred if target support and permissions allow; otherwise stop and separately review a ptrace reader. No method has been executed for this design milestone.

See [Step 21](step-reports/21-runtime-read-design.md), [runtime read plan](research/carplay/runtime-registry-read-plan.md), [runtime layout](research/carplay/runtime-registry-layout.md), and [runtime registry status](research/carplay/runtime-device-registry.md).
