# One-shot runtime registry reader

Date: 2026-09-29. The reader was built and audited offline for ARMv7/API 17. It has not been run on the vehicle.

## Implementation

Source is in [`research/tools/jmcs_registry_reader`](../tools/jmcs_registry_reader/). It accepts `--pid`, `--mc-devs-cell`, and optional `--maps`. It verifies `/proc/<pid>/cmdline` is `/system/bin/jmcs`, parses readable maps, reads only 32-bit pointer fields, and emits compact JSON. It never evaluates matcher or attach callbacks.

`process_vm_readv` uses only the ARM EABI `__NR_process_vm_readv` from NDK r23c headers. The exact header declares `__NR_SYSCALL_BASE=0` and syscall number 376; the Android ARM compile has a static assertion. This proves the build ABI, not that the likely Linux 3.1.10 Honda kernel implements or backported it. Target support remains UNKNOWN. `ENOSYS`, permission denial, missing PID, `EFAULT`, `EINVAL`, short reads, and invalid mapping are distinct failures. There is no ptrace or other fallback. A nonmatching command line aborts before memory access.

It checks node cycles and the 128-entry limit, validates every address before reading it, preserves traversal order, and compares manager/head/node/next/interface across two passes. An inconsistent snapshot gets at most one further attempt (four passes total), then is discarded. Maximum bytes are 10,272 for two maximum-sized attempts; a single complete attempt requests at most 5,136.

## Review results

Synthetic tests cover empty, one/multiple entries, insertion order, 128 and 129 entries, null manager, invalid head/interface, one- and multi-node cycles, changed snapshot, short read, `EPERM`, `ENOSYS`, and `ESRCH`. `make test safety` passes. The ARM binary contains no target write, signal, ptrace, debuggerd, injection, or `/proc/<pid>/mem` path. Its only writes are output to its own stdout/stderr. It has not been run under ARM emulation or on the vehicle.

The ARMv7/API 17 build, ELF/ISA, saved-firmware dependencies, and API symbol checks pass. Toolchain, build command, and SHA-256 values are in [`registry-reader-armv7-build.md`](registry-reader-armv7-build.md). One parked attempt was performed: current `jmcs` PID 19905's `mc_devs` cell was read-attempted once and the kernel returned `READ_STATUS=UNSUPPORTED` (`ENOSYS`). No target bytes or JSON were obtained. The process survived, the executable was removed, and ADB was disconnected. Do not retry this reader or automatically switch to another access method; see [Step 24](../../step-reports/24-registry-reader-live-unsupported.md).

## Future parked-session procedure (prepared only; not executed)

The old PID/base/cell are historical reconstruction data only. Static cell VA `0x35acbc` is supported by ELF/DWARF evidence. Historical arithmetic matches: `0x403e9cbc - 0x4008f000 = 0x35acbc`. Always derive a fresh load bias, PID, and cell using current maps and the exact saved ELF.

Set host paths and identity:

```sh
ADB=adb
SERIAL='<current approved device serial>'
JMCS_ELF='<saved exact jmcs ELF matching this vehicle build>'
READER='research/tools/jmcs_registry_reader/jmcs_registry_reader'
OUT='./registry-reader.json'
ERR='./registry-reader.stderr'
MAPS='./jmcs-maps.txt'
```

1. Connect, use the already established `su -c` root path, confirm root, rediscover the process, and require exactly one `/system/bin/jmcs` row. `pidof` was unavailable in the prior session; inspect `ps` and do not reuse PID 26577. If the known root path is unavailable, stop rather than trying another escalation.

```sh
"$ADB" connect "$SERIAL"
"$ADB" -s "$SERIAL" shell su -c id
"$ADB" -s "$SERIAL" shell su -c ps
PID='<fresh PID from current ps output>'
"$ADB" -s "$SERIAL" shell su -c "cat /proc/$PID/cmdline" > ./jmcs-cmdline.bin
"$ADB" -s "$SERIAL" shell su -c "cat /proc/$PID/maps" > "$MAPS"
```

Require the cmdline bytes to equal `/system/bin/jmcs` plus its terminal NUL. Recheck the exact ELF identity. Derive load bias from current maps and `PT_LOAD` entries (mapping file offset must match the segment's page-aligned file offset; bias is mapping start minus the segment's page-aligned virtual address). Then derive the cell:

```sh
eval "$(python3 research/tools/runtime_registry_address.py "$MAPS" "$JMCS_ELF")"
CELL="$MC_DEVS_CELL"
```

The helper must report one unique bias. Confirm `CELL` is inside a readable range in current maps. If any identity, mapping, or calculation check fails, stop.

2. Confirm the iPhone is disconnected. Push, chmod, execute exactly once and collect only the small JSON:

```sh
REMOTE=/data/local/tmp/jmcs-registry-reader
REMOTE_OUT=/data/local/tmp/jmcs-registry-reader.json
"$ADB" -s "$SERIAL" push "$READER" "$REMOTE"
"$ADB" -s "$SERIAL" shell su -c "chmod 700 $REMOTE"
"$ADB" -s "$SERIAL" shell su -c "sh -c '$REMOTE --pid $PID --mc-devs-cell $CELL > $REMOTE_OUT'" 2>"$ERR"
"$ADB" -s "$SERIAL" pull "$REMOTE_OUT" "$OUT"
cat "$OUT"
cat "$ERR"
```

3. Verify the same PID is still `/system/bin/jmcs`, remove both remote temporary files, and turn the vehicle off:

```sh
"$ADB" -s "$SERIAL" shell su -c "cat /proc/$PID/cmdline"
"$ADB" -s "$SERIAL" shell su -c "ps | grep '[j]mcs'"
"$ADB" -s "$SERIAL" shell su -c "rm -f $REMOTE $REMOTE_OUT"
```

If `/data/local/tmp` is not writable and executable, stop and review a safe location. If the syscall is unsupported or denied, stop; never switch to ptrace, suspend `jmcs`, use debuggerd, weaken kernel policy, or restart the process as part of this reader. The sequence above is a prepared plan and has not been run.

### Read outcome meanings

| Result | Meaning | Next action |
|---|---|---|
| `SUCCESS` | Complete bounded read with matching immediate snapshots | Keep JSON and resolve addresses offline. |
| `ENOSYS` / `READ_STATUS=UNSUPPORTED` | Kernel does not implement the syscall, unless vendor evidence indicates otherwise | Stop and document unsupported. |
| `EPERM` / `EACCES` | Permission or policy blocks the read | Stop; no escalation. |
| `ESRCH` | PID exited or changed | Stop; rediscovery requires a separately reviewed session. |
| `EFAULT` | Kernel rejected an address or read range | Stop; inspect address and map evidence offline. |
| Short read | Requested bytes were not fully returned | Discard snapshot and stop. |
