# R7E3 A0-R collector design (ECC)

**State:** implemented and fixture-tested; never run against Honda. **Tier:** A0-R is Tier 1 `HONDA_READ_ONLY`, and this implementation is preparation only. **Starting HEAD:** `fc2eceef2ab53c0d8ea3141f24f1571aee3802e8`.

## Gate and target selection

The default invocation prints `NOT_AUTHORIZED`, exits nonzero, and makes no ADB call. `--dry-run` prints the fixed sequence with `TARGET_REDACTED` and makes neither discovery nor ADB calls. The exact `--execute-authorized-a0-readonly` flag is only a local runtime guard. It is not user authorization. A future run also requires a local authorization reference, exact observed power-state text, affirmative stationary/parked/display/cluster/warning confirmations, and intended-Honda confirmation before inventory.

Inventory is the only initial ADB operation. It must return exactly one listed target and that entry must be in `device` state. Zero, multiple, offline, unauthorized, or malformed entries stop before any `shell` command. The target selector is pinned from this one inventory result and passed as the quoted `-s` argument on every subsequent call. There is no rescan, reconnect, retry, or transport assumption.

## Command and ECC audit

Each command uses fixed `argv` elements and a 15-second host timeout. No shell command string, `eval`, target-side redirection, pipes, or dynamic operator input is used. ADB's legacy `shell` service starts the named read utility; intended target process effect is one transient shell/utility, no persistent process. No privilege escalation is requested. Target write is **NONE** for every command. Expected target persistence/side effects are **NONE**. Host evidence writes are local and mode restricted.

| ID | Target operation | Read | Write | Process effect | Persistence / privilege | Side effect and failure policy |
|---|---|---|---|---|---|---|
| A0R-00 | local `adb devices` | Host ADB inventory | None | Host ADB client only | No target command; existing server state untouched | Require exactly one `device`; otherwise stop |
| A0R-01 | `id` | Shell identity | None | Transient shell + `id` | No persistence; ordinary shell expected | Require UID 2000; root/elevated/unknown stops |
| A0R-02 | `getprop ro.build.version.release` | Android release property | None | Transient shell + property read | No persistence; ordinary shell | Require `4.2.2`; failure/mismatch stops |
| A0R-03 | `getprop ro.build.version.sdk` | SDK property | None | Transient shell + property read | No persistence; ordinary shell | Require API 17; failure/mismatch stops |
| A0R-04 | `getprop ro.product.cpu.abi` | Primary ABI property | None | Transient shell + property read | No persistence; ordinary shell | Require `armeabi-v7a`; failure/mismatch stops |
| A0R-05 | `pwd` | Shell working directory | None | Transient shell + builtin/utility | No persistence; ordinary shell | Failure stops |
| A0R-06 | `ls -ld /data` | Directory metadata | None | Transient shell + `ls` | No persistence; ordinary shell | Failure stops; no substitute |
| A0R-07 | `ls -ld /data/local` | Directory metadata | None | Transient shell + `ls` | No persistence; ordinary shell | Failure stops; no substitute |
| A0R-08 | `ls -ld /data/local/tmp` | Directory metadata | None | Transient shell + `ls` | No persistence; ordinary shell | Failure records destination metadata blocker and stops; `LS_LD_UNAVAILABLE` |
| A0R-09 | `cat /proc/mounts` | Complete mount table | None | Transient shell + `cat` | No persistence; ordinary shell | Failure/missing `/data` mount stops; `/data` `noexec` classifies blocker |
| A0R-10 | `cat /proc/self/status` | Current shell process status | None | Transient shell + `cat` | No persistence; ordinary shell | Failure stops |
| A0R-11 | `cat /sys/fs/selinux/enforce` | Visible enforcement file, if readable | None | Transient shell + `cat` | No persistence; ordinary shell | Missing/denied/unreadable becomes `SELINUX_STATE_UNAVAILABLE`; no fallback |

`ls -ld` compatibility is not assumed. A rejection is recorded and ends destination inspection; there is no `stat`, `busybox`, `toybox`, or flag variation. SELinux failure is unavailable, never disabled/permissive, and does not trigger `getenforce`.

## Output and stop behavior

Every invoked command records ID, exact operation label, UTC and monotonic start/end, exit status, classification, stdout, and stderr. Evidence is local under ignored `build/r7e/a0r/<run-id>/`; run directory and files are private. The raw selector is stored only in `target-identity.local.txt` in that package. Metadata/summaries contain `REDACTED` and a run-local one-way SHA-256. No VIN is collected. Operator power and before-audio text are host metadata only and cannot enter a target command; the exact after-run stock-state observation is also retained.

`/proc/mounts` is saved in full. The structured `/data` record includes filesystem/options and explicit `rw`, `ro`, `noexec`, `nosuid`, and `nodev` booleans. Absence of `noexec` is only `NO_NOEXEC_FLAG_OBSERVED`; `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT` remains in force.

Ordinary shell is UID 2000 only. Unexpected root/elevation stops immediately. Platform mismatch stops before `pwd` and destination reads. A command timeout/failure stops without retry, except SELinux read failure, which is retained as unavailable. `/data` noexec stops and cannot promote Test A readiness. Operator reports stock UI/cluster/warnings/audio unchanged after the read sequence; an anomaly is `A0R_STOP_CONDITION`.

Target rollback commands: **NONE**. Any unexpected target mutation is a STOP/INCIDENT; no cleanup command is improvised. The collector cannot execute A0-W, transfer/chmod/execute/remove an artifact, or start Test A. Even `A0R_PASS_FOR_REVIEW` means only that captured evidence is ready for human review.

## Freeze identity

The canonical allowlist, stop policy, and redaction policy are [the plan manifest](r7e3-a0r-plan-manifest.json). Its SHA-256 and the collector source SHA-256 are recorded in the authorization packet and readiness decision. Any source or manifest change requires a new hash and a new authorization decision. The exact commit SHA must be filled only after the implementation commit exists.
