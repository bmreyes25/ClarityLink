# Honda `/proc` access evidence — Step 40E2

## Observed access results

The 2026-09-29 read-only Step 40E bundle contains 1,943 manifest artifacts plus the manifest. Its 1,944 expected SHA-256 entries all match. In each phase, the ADB shell (UID 2000) received `Permission denied` for root-owned `jmcs` `/proc/<pid>/maps`, `smaps`, and `fd`. This is not an empty map or an unavailable process. The saved process status reports all real/effective/saved/fs UIDs and GIDs as 0, and `TracerPid` is 0. No `Dumpable` field was captured. `/proc` mount options were recorded as `rw,relatime`, with no `hidepid` option shown.

The same PID and start-time identity persisted across baseline, stock CarPlay, and post-disconnect. `/proc/net` tables were readable, but FD denial prevents associating their rows with `jmcs`.

## Likely permission gate

**Maps/smaps denial: HIGH CONFIDENCE, mechanism not Honda-kernel-confirmed.** A closely related Android Tegra kernel implementation protects `maps` output with `maps_protect && !ptrace_may_attach(task)` and uses the same process-memory reporting machinery for `smaps`. The old Tegra procfs implementation gates `/proc/<pid>/fd` listing and symlink reads on `ptrace_may_attach(task)`. Together with the observed caller UID 2000 and target UID 0, those checks explain the denial. The precise Honda 3.1.10+ vendor kernel source/config is unavailable, so UID mismatch, dumpability, capability, an LSM hook, and vendor changes cannot be separated conclusively.

The process status does not expose dumpability in this capture. `/sys/fs/selinux/enforce` was absent, which does not prove that no vendor security hook exists. Do not infer modern `hidepid` behavior; it was not present in the captured `/proc` mount options.

Reference implementation evidence: [Tegra `task_mmu.c`](https://android.googlesource.com/kernel/tegra/%2B/36f021b579d195cdc5fa6f3e2bab198b4bf70643/fs/proc/task_mmu.c), [Tegra `base.c` FD check](https://android.googlesource.com/kernel/tegra/%2B/0119509c4fbc9adcef1472817fda295334612976/fs/proc/base.c). These are related Tegra source, not an exact Honda build match.

## Existing capture limits

- No mapping base, library load list, stack mapping, or runtime address can be inferred from the error body.
- `/proc/meminfo`, the shell’s process status, CPU topology, ASLR value `2`, and mount options were inventoried. None establishes VM page size.
- The proc config artifact begins with a gzip header but was not successfully decompressed from the legacy shell capture.
- No `pagemap`, `auxv`, environment, process memory, or secret-bearing files were read.

The detailed artifact inventory and thread/network tables are derived beside the raw bundle and outside Git. Paths in the artifact inventory have numeric process/thread IDs normalized; detailed thread and network reports remain private host-side derivatives.
