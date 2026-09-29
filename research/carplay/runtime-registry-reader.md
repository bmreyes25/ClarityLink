# One-shot runtime registry reader

Date: 2026-09-29. Implementation and offline review only. The binary has not been built for the target ABI or run on the vehicle.

## Implementation

Source is in [`research/tools/jmcs_registry_reader`](../tools/jmcs_registry_reader/). It accepts `--pid`, `--mc-devs-cell`, and optional `--maps`. It verifies `/proc/<pid>/cmdline` is `/system/bin/jmcs`, parses readable maps, reads only 32-bit pointer fields, and emits compact JSON. It never evaluates matcher or attach callbacks.

`process_vm_readv` uses only `SYS_process_vm_readv`/`__NR_process_vm_readv` from the build headers. Missing definitions stop the build; no number is hardcoded. `ENOSYS`, permission denial, missing PID, `EFAULT`, `EINVAL`, short reads, and invalid mapping are distinct failures. There is no ptrace or other fallback. A nonmatching command line aborts before memory access.

It checks node cycles and the 128-entry limit, validates every address before reading it, preserves traversal order, and compares manager/head/node/next/interface across two passes. An inconsistent snapshot gets at most one further attempt (four passes total), then is discarded. Maximum bytes are 10,272 for two maximum-sized attempts; a single complete attempt requests at most 5,136.

## Review results

Synthetic tests cover empty, one/multiple entries, insertion order, 128 and 129 entries, null manager, invalid head/interface, one- and multi-node cycles, changed snapshot, short read, `EPERM`, `ENOSYS`, and `ESRCH`. `make safety` on the synthetic binary found no forbidden imports. Source has no `process_vm_writev`, ptrace, signal, debuggerd, `/proc/<pid>/mem`, or memory-write path. Its only writes are diagnostic/JSON output to its own stdout/stderr.

Host system is macOS and has no Android ARMv7 sysroot/compiler. A cross-build attempt failed at missing target headers; the reader deliberately refuses a syscall number unavailable from those headers. Consequently ARMv7 build is FAIL/unverified, process_vm_readv ABI is unverified here, and target syscall availability is UNKNOWN (the likely 3.1-era kernel may predate mainline support). The vehicle gate is NO.

The likely future temporary directory is `/data/local/tmp`, based on Android convention only; writable/executable policy is not established from available evidence. Verify that during a separately authorized parked session. Never use `/system`.

## Future parked-session procedure (not executed)

The addresses and PID must be rediscovered every time. Set the Mac-side paths first:

```sh
ADB=adb
SERIAL='<approved-device-serial>'
JMCS_ELF='<saved exact jmcs ELF matching this vehicle build>'
READER='./jmcs-registry-reader-armv7'
OUT='./registry-reader.json'
```

1. Rediscover and verify the process:

```sh
PID="$($ADB -s "$SERIAL" shell pidof jmcs | tr -d '\r')"
test -n "$PID"
$ADB -s "$SERIAL" shell "tr '\000' '\n' < /proc/$PID/cmdline"
$ADB -s "$SERIAL" shell "cat /proc/$PID/maps" > jmcs-maps.txt
```

Confirm the cmdline is exactly `/system/bin/jmcs`. Derive the load bias from the current maps and `PT_LOAD` entries in the exact ELF (map file offset must match the segment's page-aligned file offset; bias is mapping start minus the segment's page-aligned virtual address). Recheck the ELF build identity. Calculate `CELL = LOAD_BIAS + 0x35acbc`; `0x35acbc` is the proven static VA. Do not reuse any old PID/base/cell. Confirm the cell lies in a readable current mapping.

Use the checked-in address helper to derive the current load bias and cell from that exact ELF and maps snapshot:

```sh
eval "$(python3 research/tools/runtime_registry_address.py jmcs-maps.txt "$JMCS_ELF")"
CELL="$MC_DEVS_CELL"
```

The helper must report one unique bias; otherwise stop and resolve the ELF/maps mismatch offline. Confirm `CELL` lies in a readable range in `jmcs-maps.txt` before continuing.

2. Push and execute once, then collect only JSON:

```sh
REMOTE=/data/local/tmp/jmcs-registry-reader
REMOTE_OUT=/data/local/tmp/jmcs-registry-reader.json
$ADB -s "$SERIAL" push "$READER" "$REMOTE"
$ADB -s "$SERIAL" shell chmod 700 "$REMOTE"
$ADB -s "$SERIAL" shell "sh -c '$REMOTE --pid $PID --mc-devs-cell $CELL > $REMOTE_OUT'"
$ADB -s "$SERIAL" pull "$REMOTE_OUT" "$OUT"
```

The executable is invoked once; then:

```sh
$ADB -s "$SERIAL" shell rm -f "$REMOTE" "$REMOTE_OUT"
$ADB -s "$SERIAL" shell pidof jmcs
```

Verify the final `pidof` reports the same still-running process. If `/data/local/tmp` is not both writable and executable, stop and review a safe location. If the syscall is unsupported/denied, stop; never switch to ptrace, suspend jmcs, use debuggerd, weaken kernel policy, or restart the process as part of this reader.
