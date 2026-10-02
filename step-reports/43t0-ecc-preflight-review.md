# 43T0 — ECC preflight safety review (offline)

**Decision: `43T0_ECC_NO_GO`.** Starting HEAD: `170a41f9177bc0a8e5d5ebb9f5b21b49b224da22`. The worktree was clean. No Honda connection, ADB command, vehicle command, Type111 negotiation, or vehicle modification occurred in this review. This is a review of a proposed procedure, not authorization to collect.

## Basis and decisive finding

Reviewed `PROJECT_STATE.md`, `NEXT_ACTION.md`, `EVIDENCE_INDEX.md`, 43S/43S1/43S2 reports, the native transaction and listener contracts, the Type111 rollback contract, and the older 40E/40E3/40E4 and 40F-Lite safety evidence. 43S2 passed its offline objective; G5 and G12 pass within emulator/host bounds, G11 is partial, G19 passes for the offline seam, and G21 passes structurally. Honda Type111 acceptance, security, listener reachability, CF bridge, and media remain unknown. Runtime/deployment stays disabled.

The proposed 43T0 repeats much of [40E's completed three-phase unprivileged capture](40e-readonly-runtime-preflight.md). [40F-Lite](../research/runtime/step40f-lite.md) expressly recommends against another equivalent vehicle session. 40E already established target identity, stable `jmcs` process identity, and global socket-table changes; `jmcs` maps and FDs were permission denied. The proposal does not specify a new, answerable G11 question, exact target command sequence, or exact capture implementation that justifies another connection. The smallest change is **offline analysis of the existing host-only 40E bundle for interface/address/route evidence, followed by a narrowly scoped delta procedure only if a specific missing observation is identified**. The old bundle must be accessed locally without contacting Honda; preserve its privacy boundary. Return for another ECC review of that exact delta and collector dry run. Do not get in the car for 43T0 under this decision.

## Meaning of observational

For a later approved session, the defensible claim would be `OBSERVATIONAL_ADB_SESSION_WITH_NO_EXPLICIT_TARGET_WRITES` and, if verified, `NO_INTENTIONAL_MUTATION_OCCURRED`. It must never be `ZERO_PHYSICAL_STATE_CHANGE`. ADB starts sessions and can affect logging, counters and timing; stock CarPlay connection changes normal runtime/network state. Reads of ordinary on-device files may update access-time metadata depending on mount policy; virtual files can have read side effects. The rule is **no intentional state-changing filesystem or runtime operation issued by ClarityLink**. Do not pull or hash a live `jmcs` binary for 43T0: the preserved SHA-256 identity and stock process metadata already provide the useful static identity, while a full live read adds atime, volume, and privacy ambiguity. An inaccessible resource is `READ_BLOCKED_WITHOUT_PRIVILEGE`, never a reason to invoke `su` or SuperSU. The 40E3/40E4 reviews could not prove SuperSU invocation free of persistent side effects.

## Candidate command review

These classifications assess command *semantics*, not approval to execute now. `APPROVED_WITH_CAVEAT` always requires a fixed, literal command form, ordinary UID-2000 shell, bounded output/time, and local sanitization. Utility presence must be checked against archived evidence or a later approved run; missing utilities are reported, not replaced with privilege escalation. `uname` was unavailable and `adb exec-out` failed in 40E, so neither is a required path.

| Candidate | Class | Reads / mutation and variant boundary | Sensitive output and sanitization |
|---|---|---|---|
| `getprop` | `APPROVED_WITH_CAVEAT` | Selected **literal property keys only**; ordinary property read. Full dump is excessive; `setprop` and any setter are banned. | Device identifiers, network and build properties: retain only target identity fields already justified by 40E. |
| `uname -a` | `REMOVE_FROM_ALLOWLIST` | Host-independent read but unavailable on this target in 40E; `/proc/version` already supplies kernel identity. | Kernel/build string only, but no added value. |
| `id` | `APPROVED_READ_ONLY` | Current shell identity/groups; no intentional persistent write. Do not use `su`, `run-as`, or `adb root` as variants. | Groups/UID; retain UID and privilege-boundary result. |
| `ps`, `ps -A` | `APPROVED_WITH_CAVEAT` | Enumerates processes; `ps -A` may differ on API 17 and must not be assumed supported. No kill/signal variants. | Other apps and command lines: retain only `jmcs` PID/name and continuity facts; prefer the fixed known 40E form. |
| `cat /proc/net/dev` | `APPROVED_WITH_CAVEAT` | Global interface counters; ordinary proc read, possible kernel bookkeeping. No `cat` of arbitrary paths. | Interface names/counters: retain relevant interface names and before/after deltas only. |
| `cat /proc/net/route` | `APPROVED_WITH_CAVEAT` | IPv4 routes; global snapshot, no route change. | Addresses/gateways: keep only technically needed Honda-side route/interface association. |
| `cat /proc/net/tcp`, `tcp6`, `udp`, `udp6` | `APPROVED_WITH_CAVEAT` | Global socket tables, not process ownership; fixed paths only. | Endpoint/IP/inode data: reduce to relevant local address family, port/state and phase delta; redact unrelated peers. |
| `cat /proc/net/unix` | `REMOVE_FROM_ALLOWLIST` | Global Unix socket table; no demonstrated G11 need. | Can expose app/service paths; avoid collection. |
| `ip addr`, `ip route`, `ip link` | `UNAVAILABLE_WITHOUT_RUNTIME_TEST` | Read forms are observational, but `ip` presence/format is not established. Never append `add`, `del`, `set`, or `flush`. | Addresses/MACs/routes: keep only pertinent interface, Honda local address/family and route. |
| `ifconfig` | `UNAVAILABLE_WITHOUT_RUNTIME_TEST` | **No arguments only** is observational if installed; interface arguments can configure state. Redundant if `/proc/net/dev` and route evidence suffice. | MAC/IP data: redact unrelated interfaces and identifiers. |
| `netstat` | `UNAVAILABLE_WITHOUT_RUNTIME_TEST` | No-argument read if installed; options and broad output add little beyond fixed proc tables. | Remote endpoints/process data: omit unrelated rows. |
| `/proc/<jmcs-pid>/status` | `APPROVED_WITH_CAVEAT` | Fixed PID derived from a checked `jmcs` identity; proc metadata read. No writes or broad proc traversal. | UID/group/capability details: retain name, PID, UID and continuity only. |
| `/proc/<jmcs-pid>/maps` | `REMOVE_FROM_ALLOWLIST` | Previously permission denied; no retry via root. Address-space details do not answer this observational G11 question. | Memory map/address layout is sensitive; do not collect. |
| `/proc/<jmcs-pid>/cmdline` | `APPROVED_WITH_CAVEAT` | Fixed verified PID; NUL-delimited read, no execution. | Arguments may contain paths/secrets: keep only confirmation of expected executable name. |
| `/proc/<jmcs-pid>/fd` | `REMOVE_FROM_ALLOWLIST` | Previously permission denied; listing or link resolution is not approved, and ownership cannot be inferred from denial. | FD targets may reveal files, sockets and private paths. |
| `/proc/<jmcs-pid>/net/*` | `REMOVE_FROM_ALLOWLIST` | Wildcard and broad traversal are disallowed. Namespace tables do not by themselves establish `jmcs` socket ownership. | Global endpoints; use only fixed global tables if needed. |

No `/sys` or `/dev` path is approved by this review. The only `/proc` paths eligible for a future narrowed procedure are the fixed ones classified above; no wildcard is approved. A read-only command can still have output, timing, or virtual-file side effects, so uncertainty means stop.

## Proposed future command boundary and capture method

**No final 43T0 command allowlist is issued under NO-GO.** A revised plan must provide literal `adb shell <fixed read>` invocations for only the missing observations; 40E showed the legacy `adb shell` service worked where `exec-out` did not. `adb exec-out <fixed read>` is semantically eligible but target support is unproven and must not be used as a troubleshooting detour. `adb pull <readable stock file>` is **not approved**: it performs a target read with possible atime and potentially large output, and no necessary 43T0 fact requires it. No live binary pull.

The revised collector must run fixed commands without arbitrary shell input or `shell=True` unless separately justified; reject metacharacters, redirection and dynamic paths other than a decimal PID validated against process identity. No target temporary files. Capture bytes directly on the Mac in an owner-only directory outside Git, with bounded per-command time and output, local phase/time/command/status manifest, sanitized errors, and no write-capable target operation. Review an offline `--dry-run` showing the **exact** ADB argv and capture destinations before any live invocation. Redaction happens before anything is committed; preserve raw evidence locally only for the minimum needed period.

**Denylist:** `su`, SuperSU, `adb root`, `run-as`, `mount`, `umount`, `remount`, `setprop`, `settings put/delete`, `pm install/uninstall`, `am force-stop/startservice`, `svc`, `ifconfig <interface> ...`, `ip addr/route/link ... add|del|set|flush`, DNS/Wi-Fi/firewall changes, `iptables`, `nft`, `sysctl -w`, `chmod`, `chown`, `touch`, `mkdir` on target, `rm`, `mv`, target-directed `cp`/`dd`, `tee`, shell `>`/`>>`, `echo`/`printf` redirection, `sed -i`, `xargs` with a state-changing command, `reboot`, `stop`, `start`, `kill`, `killall`, `pkill`, `insmod`, `rmmod`, `setenforce`, `restorecon`, `adb push`, service starts, packet injection, proxy/listener, port scan/probe, `tcpdump` until independently reviewed, debugger/ptrace, `/proc/<pid>/mem`, process priority/affinity/thread changes, and any write to `/proc`, `/sys`, or `/dev`. No command may request root or a target-side confirmation to change state.

## Evidence, privacy, and G11

Every retained observation must be labeled `OBSERVED_ON_HONDA_READ_ONLY`, `HONDA_STATIC_COMPATIBILITY`, `INFERRED`, `UNRESOLVED`, or `READ_BLOCKED_WITHOUT_PRIVILEGE`. Prior 40E observations keep their provenance; static ELF imports are not live runtime proof. Network coincidence is not `jmcs` ownership, an interface is not Type111 reachability, and socket API imports are not listener ABI compatibility. Committed evidence may contain only interface name/class, necessary Honda local address/family, route-to-interface association, relevant CarPlay port/socket structure, `jmcs` process continuity, phase/time order, and the specific before/after comparison. Redact MACs, unrelated IPs, remote peers, Wi-Fi identifiers, device IDs, credentials, full command lines, and raw socket dumps. Do not commit raw capture.

The narrow G11 questions are: which interface and Honda-side address/family appear with normal stock CarPlay; which route uses that interface; whether the interface and route are stable enough to form a *candidate* future binding policy; and whether available process evidence contradicts the pinned `jmcs` identity. Existing 40E data must be checked first. Global socket tables can show topology changes only. A successful future 43T0 would not prove Type111 acceptance, listener reachability, crypto, media, CF mutation, or cluster rendering.

## Sequence, human boundary, and hard stops for any revised session

If an independently reviewed delta later receives GO, the user checklist is: (1) park and power the Honda normally; (2) use only the existing authorized ADB route; (3) leave the normal iPhone cable disconnected for the bounded baseline; (4) connect it normally when prompted; (5) confirm center CarPlay, audio, and stock cluster UI; (6) disconnect normally. Do not change pairing, receiver identity, navigation settings, or Honda features for evidence. The user must never be asked to authorize root, remount, install, patch, process restart, network change, or CarPlay configuration change.

Stop immediately on target-identity or shell-UID mismatch, unexpected mounts/configuration, a command requiring root, uncertain semantics, a modification prompt, permission denial whose only workaround is modification, unexpected ADB behavior requiring intervention, command timeout/oversize, `jmcs` identity change, abnormal center CarPlay/audio/cluster, or any loss of stock operation. Report the partial data; do not troubleshoot on Honda. Timestamp and order each phase so connection changes cannot be attributed to the wrong snapshot.

## Compact ECC threat review

| Risk | Likelihood | Impact | Mitigation | Residual risk |
|---|---|---|---|---|
| Accidental write, privilege escalation or process interruption | Low with fixed command dispatch; high if generic shell/old privileged collector is reused | High | Literal allowlist, dry run, no `su`, no target redirection, no signals/debugger | ADB/service internals may still create ordinary bookkeeping. |
| Network or CarPlay disruption from active probes or changes | Low if no active commands; ordinary cable transitions are expected | High | No bind/probe/configuration; user checks stock center/audio/cluster and stops on anomaly | Stock connection itself changes ephemeral network state. |
| False socket ownership/interface attribution | Medium | Medium to high for later design | Phase labels, PID continuity, explicit global-table provenance, infer only candidate interface | FD access denied; ownership and reachability remain unknown. |
| Baseline/connected snapshot mixing or changing vehicle state | Medium | Medium | Explicit time/order/phase manifest; parked stable condition; no unrelated settings changes | Transient sockets and timing can confound deltas. |
| Device/network/credential disclosure | Medium with broad raw dumps | High | Minimal commands, host-only private raw storage, field allowlist and redaction before commit | Necessary Honda local address may remain sensitive. |
| ADB disconnect, hang, huge output, absent utility or permission denial | Medium on API 17 | Low to medium | Time/size limits; known shell service; classify failure and stop rather than retrying with privilege | Partial evidence may not answer G11. |

## Reversibility and next gate

43T0 should issue no intentional mutation, so it has no target rollback action. Before **any later modifying** milestone, independently prove exact live target identity, original bytes, compare-before-write, RAM-only attachment without persistence, independent detector, explicit detach, exact-byte restoration and verification, reboot-to-stock and post-reboot verification, stock Type110/audio/cluster baseline, and emergency STOP behavior. A possible 43T1 is **not** authorized here. If the existing 40E data cannot answer the narrowed G11 question, first prepare the exact minimal offline collector/dry run and return to ECC review; if it can, proceed to an offline G11 reassessment and CF bridge work rather than another vehicle capture.

**Final decision: `43T0_ECC_NO_GO`.**
