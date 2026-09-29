# Step 24 — one-shot live registry reader result

Date: 2026-09-29
Source/build: Step 23, ARMv7/API17 reader SHA-256 `c418c8622e6d2a490f5a53074a0364fdbffcd8ff12ce3c7f061eadf5d442e8ec`
Scope: one parked attempt; iPhone disconnected; no fallback.

## Preflight

- ADB endpoint: `192.168.86.102:5555`, connected device reported as Honda Andromeda / MY16ADA.
- Root confirmed: `uid=0(root) gid=0(root)`.
- Fresh `ps` identified `/system/bin/jmcs`, PID `19905`.
- `/proc/19905/cmdline` matched exactly `/system/bin/jmcs` plus NUL, both before and after the attempt.
- Fresh maps captured locally. The saved exact ELF matched a unique current load bias of `0x40001000`.
- Static `mc_devs` VA `0x35acbc` produced current cell `0x4035bcbc`, inside readable mapping `40353000-40371000 rw-p`.
- Local reader hash matched the audited expected SHA-256.
- `/data` was mounted `rw`; `/data/local/tmp` existed.

## One invocation

Only the reader executable was pushed to `/data/local/tmp/jmcs-registry-reader` and chmodded 700. It was invoked once for PID 19905 and cell `0x4035bcbc`.

Observed output:

```text
ADB shell/su wrapper status: 0 (legacy wrapper status is not treated as the reader result)
stdout: READ_STATUS=UNSUPPORTED
stderr: [empty]
```

`READ_STATUS=UNSUPPORTED` is the reader's `ENOSYS` branch. It occurred on the first 4-byte syscall request for the `mc_devs` cell. No target bytes were returned; no registry JSON was produced. This records that the running system reports the syscall unsupported. It does not distinguish an absent kernel implementation from a policy layer returning `ENOSYS`.

## Cleanup and process check

- PID 19905 remained `/system/bin/jmcs` after the reader exited.
- `/data/local/tmp/jmcs-registry-reader` was removed and confirmed absent.
- No JSON file was created on the head unit.
- ADB was disconnected immediately after cleanup.
- No second syscall attempt, ptrace, debugger, process suspension, target write, or CarPlay connection occurred.
- Per the required parked-session scope, the iPhone remained disconnected. The car-off control is physical; it could not be operated remotely and must be completed by the user.

Local ignored captures are under `research/captures/registry-reader-live-20260929/`: pre/post cmdline, current maps, stdout (`registry-reader.json`, containing the status text rather than JSON), and stderr. There is no registry snapshot to resolve.

## Decision

`process_vm_readv`: **STOP; observed ENOSYS**. Do not retry this binary or fall back automatically. `mc_devs` head, registry entries, matcher, attach callback, and media pipeline remain unresolved. Next work is offline design/review of a separate read-only ptrace reader, with explicit thread stop/resume and failure-recovery analysis. No live ptrace attempt is authorized by this result.
