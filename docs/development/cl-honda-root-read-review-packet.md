# CL-HONDA-ROOT-READ-EVIDENCE — independent review packet

**Decision:** review pending. No target operation is authorized by this packet. The live runner remains disabled.

## A. Purpose

Obtain current `jmcs` process identity, mappings, optional `smaps` page data, executable/library mappings, and bounded process-owned descriptor links. Correlate descriptors to `/proc/net/{tcp,tcp6,udp,udp6,unix}` only when a parsed socket inode from a `jmcs` FD exactly matches a network-table inode. This closes the current evidence gap left by Step 40E, where UID 2000 received permission denied for maps, smaps, and FD enumeration. Static ELF dependencies remain distinct from runtime mappings.

The target is a Honda Clarity MY16ADA, Android 4.2.2/API 17, ARMv7. The executable is expected to be `/system/bin/jmcs`. The exact device serial is supplied only in the private authorization artifact.

## B. Exact profile and commands

The machine-readable manifest is [`privileged_campaign_profile.json`](../../tools/honda-readonly-preflight/privileged_campaign_profile.json), SHA-256 `74b37c720fbe4b40d7e39b75a27bb951dd68c90d67965f95c98b60f7dd893f64`. The committed source lock covers:

| Source | SHA-256 |
|---|---|
| `analyze.py` | `d134e466e26b49d17e97332ee1ec610332bd37b9a5f1823c659840a859652f82` |
| `privileged.py` | `2b92cf5ba79de5e0a252eb5f73db03c15421ba4adb6c8bf82250256090406e51` |
| `privileged_campaign.py` | `061a5fd595c4100e12e499c31865a05575811c59bf65f1dbeaa6825689fdb084` |
| `collector.py` | `55dd87677ca9f3c2a2609f1a7df2f242140f7dbd110356ed7865d40127df91f9` |
| `parsers.py` | `75976f12fe81f92a73f30e137d5f0544cf9cad124d23d4f9ea7080b0fbdfb85c` |
| `privileged_campaign_static_dependencies.json` | `68d6234246b90522da0f76569cd67156e38b0d4e9a824b0091ada22cc6c27658` |

The profile also pins the SHA-256 of that source-lock JSON. The dry run emits every argv, timeout, output ceiling, stage and phase without locating ADB or querying devices. PID, FD and serial values in examples are placeholders.

R0 uses the existing ADB shell without `su`:

```text
adb -s <EXACT_SERIAL> shell id
adb -s <EXACT_SERIAL> shell cat /proc/version
adb -s <EXACT_SERIAL> shell getprop ro.build.version.release
adb -s <EXACT_SERIAL> shell getprop ro.build.version.sdk
adb -s <EXACT_SERIAL> shell getprop ro.product.device
adb -s <EXACT_SERIAL> shell getprop ro.product.board
adb -s <EXACT_SERIAL> shell getprop ro.hardware
adb -s <EXACT_SERIAL> shell sha256sum /system/xbin/su
adb -s <EXACT_SERIAL> shell ls -l /system/xbin/su
```

Each R0 command is limited to 5 seconds. `id`, each property, and the `su` hash/metadata reads have 16 KiB/64 KiB caps as pinned; `/proc/version` is capped at 64 KiB. The R0 total ceiling is 9 commands, 45 seconds and 442,368 bytes. `su` is not executed in R0. The archived expected SHA-256 is `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`. The acceptance rule requires root ownership, setuid, and no group/other write bits. The archived mode is `06777`, which fails that rule. A mismatch is a stop; no repair is allowed.

R1 is the only minimum privilege check:

```text
adb -s <EXACT_SERIAL> shell /system/xbin/su -c id
```

Limit: 5 seconds, 16 KiB. Expected result is exit 0 and UID 0. This command may initialize SuperSU daemon/request/log state; approval must explicitly accept that unresolved risk. Any prompt, unexpected output, timeout, or state change stops the session.

For each R2/R3 phase, after resolving exactly one `jmcs` PID from bounded `ps`, verify the same PID, start time, UID/GID, status name, command line and `/proc/<PID>/exe` target before and after collection. UID/GID must match the saved expected root identity. Each remote command is passed as a separate fixed argv to `adb -s <EXACT_SERIAL> shell /system/xbin/su -c <REMOTE_COMMAND>`; no string from the owner or reviewer is assembled into a shell program. The operation sequence is:

| Fixed operation | Exact remote argv under `/system/xbin/su -c` | Timeout | Output cap |
|---|---|---:|---:|
| Root identity | `id` | 5 s | 16 KiB |
| Process table | `ps` | 10 s | 2 MiB |
| Process start identity | `cat /proc/<PID>/stat` | 5 s | 64 KiB |
| UID/GID and process identity | `cat /proc/<PID>/status` | 5 s | 256 KiB |
| Command line identity | `cat /proc/<PID>/cmdline` | 5 s | 64 KiB |
| Executable link | `ls -l /proc/<PID>/exe` | 5 s | 64 KiB |
| Memory maps | `cat /proc/<PID>/maps` | 10 s | 4 MiB |
| Mapping/page details | `cat /proc/<PID>/smaps` | 30 s | 16 MiB |
| FD listing | `ls -l /proc/<PID>/fd` | 10 s | 2 MiB; at most 256 parsed descriptors |
| FD target, once per validated nonnegative 32-bit FD; at most 256 descriptors per phase | `ls -l /proc/<PID>/fd/<FD>` | 5 s each | 64 KiB each |
| Socket tables | `cat /proc/net/tcp`, `tcp6`, `udp`, `udp6`, `unix` | 10 s each | 2 MiB each |

R2 is one iPhone-disconnected phase. R3 is separately authorized baseline/normal stock CarPlay connected/post-disconnect correlation. R3 uses only ordinary owner-guided connect/disconnect; it does not trigger negotiation or alter receiver state. R2's worst-case ceiling is 274 commands, 1,435 seconds and 53,362,688 bytes. R3's three phases have a combined worst-case ceiling of 822 commands, 4,305 seconds and 160,088,064 bytes. These bounds assume the maximum 256 FD entries in each phase and exclude owner transition/wait time. All timeouts, output excess, parse failures, permission denial, unexpected identity or SuperSU behavior stop without retry or fallback. Raw output is written only to a new mode-0700 host directory outside Git; files are mode 0600 and the final manifest covers all artifacts.

The proposed manifest contains no command for `/proc/<PID>/mem`, environ, credentials, secrets, keys, signals, ptrace, debugger attachment, process stop, helper upload/execution, memory permission change, property/settings/mount update, `adb root`, CAN, install or receiver modification.

## C. Privilege risk assessment

- The archived `/system/xbin/su` is a 75,348-byte ARM EABI5 Chainfire SuperSU-family binary, marker `2.77:SUPERSU`, archived SHA above, root:root, mode `06777`. Its provenance and the reason for world/group write bits are unknown. The archives are of an already modified unit, not a factory image.
- The existing validator rejects the archived mode. Do not change the binary, owner, mode or contents to pass the check.
- Static evidence shows SuperSU command/log/request/daemon and filesystem capabilities. The stripped binary's exact `-c` branches and write flags remain unresolved; successful historic `su -c id` does not establish a zero-write path.
- R1 may cause a root authorization prompt, request record, command log, daemon activation, or persistent state. Do not approve unless those possible side effects and the stopping/recovery boundary are acceptable. There is no no-log switch or zero-write claim in this proposal.
- Root is limited by `PrivilegedRead` enum operations and fixed leaves/tables. It does not expose an arbitrary shell string. The new profile and source hashes are independent of C-P; no root command is added to its manifest.
- No safer existing root-free interface has been demonstrated for the denied process maps/smaps/fd. Step 40E already collected useful shell-readable identity, display state and global network data; repeating it would not answer the denied fields. Historical mappings belong to different process epochs and cannot replace current maps.

## D. Vehicle risk and stop/recovery

The proposal is parked-only. The reviewer must name the exact acceptable PHEV electrical power state and assess Type110 continuity, center-display responsiveness, instrument-cluster behavior, warning priority, audio/navigation continuity, resource load, ADB/root prompt behavior, and the risk of a command timeout or connection/power interruption. `smaps` and network tables are bounded but may still consume CPU, memory bandwidth and I/O. Capture uses no intentional target write, but SuperSU setup writes are not ruled out.

Before any later stage, define exact factory baseline checks and owner-controlled power/connection steps. On any warning, abnormal display/cluster/audio/navigation, unapproved prompt, target/process mismatch, denial, timeout, limit, or lost connection: stop, preserve already written host evidence, do not retry or switch methods, and let the owner assess factory behavior. Do not turn off or cycle power until the owner confirms ordinary restoration is safe. No automated recovery is proposed; a qualified independent reviewer must define what recovery is required for an unexpected SuperSU daemon/request or head-unit interruption. A successful dry run is not vehicle restoration evidence.

## E. Privacy

Raw `maps`/`smaps`, command line, descriptor targets, process credentials/metadata and network endpoints may identify applications, services, addresses, ports, users or session timing. Keep the raw capture and review/authorization artifacts owner-only and outside Git. Do not copy raw output, device serials, endpoint values or reviewer identity into public reports. Publish only a minimized, reviewed summary and evidence hashes.

## F. Independent human decision

Request a qualified independent reviewer with demonstrated Android 4.2/API-17 or legacy ADB privilege expertise and automotive diagnostic/vehicle-safety competence. The reviewer must inspect the exact profile JSON, profile SHA, source lock, source hashes, this packet, archived `06777` finding, existing SU provenance/side-effect record, exact vehicle power-state proposal, data handling, stop and recovery behavior. Record reviewer identity, competence, independence attestation, decision and artifact SHA in private storage. AI review is not human approval.

After an approval for a specific stage is present, obtain separate owner authorization bound to that stage, exact profile/source hashes, exact serial, phase list and power state. R0, R1, R2 and R3 are separate gates; approval for one does not authorize the next. This packet does not authorize a run. Current decision: **review pending; owner authorization pending; live execution disabled**.
