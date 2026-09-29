# Next action

**Provide an existing ptrace-capable, read-only memory inspection endpoint for the head unit, or an approved equivalent that does not install software or write a tombstone.** ADB/root confirmed `jmcs` PID 26577 and load base `0x4008f000`; the DWARF-derived manager-handle cell is runtime `0x403e9cbc`, but the kernel denies `/proc/26577/mem` reads. No debugger server is installed, and current logs expose no registry data. The iPhone remains disconnected; do not connect it until this access blocker is resolved.

See [Step 18](step-reports/18-runtime-registration-resolution.md) and [runtime registry evidence](research/carplay/runtime-device-registry.md).
