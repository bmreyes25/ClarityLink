# R7E2 Test A evidence gap table (ECC)

| Fact | Existing evidence | Exact source | Evidence class | Sufficient for Test A plan? | Target observation? | Write? | Execution? |
|---|---|---|---|---|---|---|---|
| `/data/local/tmp` exists | UDA archive maps `/local/tmp` to target path | `step-reports/41d-selinux-load-environment.md` | HONDA_STATIC | Candidate only | Yes, A0-R | No | No |
| Ownership | owner/group 2000:2000 (`shell:shell`) in archive | same | HONDA_STATIC | Static only | Yes, A0-R | No | No |
| Permissions | mode 0771 in archive | same | HONDA_STATIC | Static only | Yes, A0-R | No | No |
| Writable by shell | Not demonstrated | `research/runtime/r7e1-test-a-target-evidence-review.md` | UNKNOWN | No | A0-W if needed | Yes | No |
| Removable by shell | Not demonstrated | same | UNKNOWN | No | A0-W if needed | Yes | No |
| `/data` mount flags | Historical `/proc/mounts`: `rw,nosuid,nodev`, no `noexec` | `step-reports/41f-honda-linker-preload-fingerprint.md`; capture path named there | HONDA_READ_ONLY_OBSERVED (historical) | Only historical context | Yes, A0-R | No | No |
| Candidate noexec restriction | Absent in historical capture; current runtime unknown | same | HONDA_READ_ONLY_OBSERVED (historical) | No current conclusion | Yes, A0-R | No | No |
| SELinux state | `/sys/fs/selinux/enforce` absent; `getenforce` unavailable historically; mode/domain unknown | `step-reports/41d-selinux-load-environment.md`; `research/platform/honda-live-runtime.md` | HONDA_READ_ONLY_OBSERVED / HONDA_STATIC | No | A0-R read if present | No | No |
| Shell UID/GID | UID 2000 shell observed; prior records support legacy `adb shell id`; GIDs are to capture on next observation | `step-reports/40e-readonly-runtime-preflight.md`; `research/platform/honda-live-runtime.md` | HONDA_READ_ONLY_OBSERVED | No, capture current | A0-R | No | No |
| Ordinary-shell sufficiency | UID 2000 known; path write/delete and executable acceptance unknown | `step-reports/40E4-zero-write-privilege-path.md`; target evidence review | UNKNOWN | Root not justified; write sufficiency open | A0-R then conditional A0-W | Conditional | Test A only for actual exec |
| Executable invocation permission | Noexec absent historically; SELinux/mmap behavior unknown | 41D/41F reports | STATIC + historical | Must be a measured result, once known hazards screened | A0-R for policy, Test A for actual result | No before Test A | Yes (Test A measurement) |
| Chosen vehicle state | Prior 43T0-D4: parked/stationary/normally powered; mode label absent | `step-reports/43t0d-read-only-honda-network-delta.md` | HONDA_OBSERVED, state detail partial | No named state | A0-R operator record | No | No |
| ADB reachability in chosen state | 43T0-D enumeration returned zero targets; no target commands; later operator said connected after stop boundary | same | HOST_ONLY_OBSERVED / unresolved Honda | No | A0-R identity gate | No | No |

ECC disposition: A0-R is required first. It may establish current identity, path metadata, mount flags, visible SELinux state, and operator-observed power state. It cannot prove write/delete or exec. If write/delete remain open, A0-W is a separate future authorization. Executable permission is measured by Test A.
