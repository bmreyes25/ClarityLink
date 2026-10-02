# Step 43T0-B — ECC review of exact G11 network delta

**Decision: `43T0_DELTA_ECC_NO_GO` for the current 43T0-A dry-run plan.** Starting HEAD `f4f01c8360c35766e5cbbbd892fa9acb7435d52d` on clean `main`. `HONDA_CONTACTED = NO`; `ADB_USED = NO`; `TARGET_WRITES = 0`. No proposed collector was executed, and this review authorizes no car visit, 43T0/43T1, Type111, listener, or attachment.

## Review basis and evidence boundary

Reviewed `NEXT_ACTION.md`, `PROJECT_STATE.md`, `EVIDENCE_INDEX.md`, the [40E report](40e-readonly-runtime-preflight.md), [43T0 preflight](43t0-ecc-preflight-review.md), [43T0-A report](43t0a-40e-network-evidence-reanalysis.md), 43S2, the 43T0-A dry-run source, the host-only 40E manifest, and preserved firmware files. 40E is real Honda/stock CarPlay with no Type111; 43P is Mac/iPhone/PlayPort with no Honda. The prior socket rows are global tables, not `jmcs` ownership. This review applies ECC evidence-first, command-safety, privacy, and final-decision discipline; it does **not** claim an independent external ECC reviewer ran.

The key defect is concrete: the dry run obtains `adb_serial` from the old 40E manifest and prints network-read argv without a current-target identity gate. That serial was an ADB-over-Wi-Fi endpoint, not proof that a presently connected target is the same unit. The current script is safe to run offline because it never invokes ADB, but its printed plan is not ready to become a live collector. A second unresolved item is the no-argument `ifconfig` output contract. The preserved firmware tree has `system/bin/ifconfig -> toolbox` and a toolbox `ifconfig` applet string, supporting static availability for that image; neither the 40E manifest nor its artifacts show a live no-argument invocation. Static presence is not current runtime availability or proof of its exact output. The four proposed proc paths were also not captured by 40E; do not assert their current availability.

## Exact read review

| Proposed target read | Need | Semantics | ECC finding |
|---|---|---|---|
| `cat /proc/net/dev` | `NECESSARY` | `READ_ONLY_SEMANTICS_ACCEPTABLE` | Global interface names and RX/TX counters; no address mapping. Fixed ordinary proc read. Keep. |
| `cat /proc/net/route` | `NECESSARY` | `READ_ONLY_SEMANTICS_ACCEPTABLE` | IPv4 destination/gateway/mask/flags/metric and interface. Keep because IPv4 path remains unresolved. |
| `cat /proc/net/ipv6_route` | `NECESSARY` | `READ_ONLY_SEMANTICS_ACCEPTABLE` if path exists | IPv6 route/interface association matters for the link-local candidate. Kernel IPv6 sockets in 40E support IPv6 availability, but this exact proc file was not captured. No path-availability claim; fail closed if absent. |
| `cat /proc/net/if_inet6` | `NECESSARY` | `READ_ONLY_SEMANTICS_ACCEPTABLE` if path exists | Direct IPv6 address, interface index/name, prefix, scope and flags. Critical for link-local scope. No path-availability claim; fail closed if absent. |
| `ifconfig` with **zero arguments** | `NECESSARY` for IPv4 address-to-interface mapping | `READ_ONLY_SEMANTICS_ACCEPTABLE` only in the zero-argument form; runtime output contract `UNRESOLVED` | Preserved image has a toolbox symlink, but live behavior/output was not observed. Keep as the only proposed IPv4 mapping source, with no automatic `ip`, `netcfg`, BusyBox, or other fallback. Stop and return partial if unavailable, malformed, or apparently configuration-seeking. |

No fixed `/proc` file among the proposed reads directly substitutes for IPv4 interface addresses: `/proc/net/route` gives routes, and `/proc/net/dev` gives interfaces/counters. `ifconfig` arguments can configure interfaces and remain prohibited. `/proc/net/tcp*`, `/proc/net/udp*`, Unix sockets, `jmcs` maps/FD, live binary pulls, active probes, and packet capture are **`REDUNDANT` or `REMOVE`** for this delta.

## Phase count and bounds

**Retain three phases**: disconnected baseline, stock CarPlay connected, and post-disconnect. The third phase is five short reads and tests whether a candidate interface/address/route disappears after unplugging; that reversal materially strengthens attribution because 40E did not capture these network fields. Two phases might identify a candidate but cannot distinguish a persistent or coincidental change as well. Do not collect extra time-series samples. The fixed order within each phase should be `/proc/net/dev`, `/proc/net/route`, `/proc/net/ipv6_route`, `/proc/net/if_inet6`, then zero-argument `ifconfig`. Missing or failed reads yield partial evidence; they do not trigger substitutions.

The proposed **5-second timeout and 64-KiB combined output cap per read** are acceptable fail-closed bounds, not guarantees. In 40E, 17 fixed network reads had a maximum observed duration of 0.244 seconds and the largest network artifact was 9,196 bytes. The new files could differ; timeout or oversize means stop and retain a bounded partial record. Never silently truncate and analyze it as complete. Check output format and exit status before proceeding. If Android shell transport returns status ambiguously, classify from bounded stdout/stderr and the transport result, mark uncertainty, and stop. A normal proc read may affect kernel counters or timing; the defensible later claim is `NO_INTENTIONAL_MUTATION_OCCURRED`, never `ZERO_PHYSICAL_STATE_CHANGE`.

## Required current-target identity correction

The old serial may select the historical dry-run template and may be compared to a current ADB endpoint, but it is **not** an identity credential. Before any *network* reads in a future separately initiated session:

1. Human confirms the parked, normally powered Honda and the intended existing ADB-over-Wi-Fi connection. Do not scan or auto-connect to a different endpoint.
2. Host enumerates ADB targets once and requires exactly one expected `device` target; reject multiple, offline, unauthorized, or unexpected targets. Do not automatically choose one. This enumeration is future ADB use, **not performed here**.
3. On the selected current target, issue only fixed identity reads: `id`; `cat /proc/version`; and `getprop` separately for `ro.build.version.release`, `ro.build.version.sdk`, `ro.product.device`, `ro.product.board`, and `ro.hardware`. Compare every result against the trusted 40E preflight values. Require shell UID 2000 and no unexpected privilege boundary. This is the minimal already-established 40E fingerprint, not a device-ID dump or full `getprop`.
4. Fail closed on any mismatch, missing value, ambiguity, or transport error **before `/proc/net/*` or `ifconfig`**. Retain only match/mismatch and redacted diagnostics in committed evidence. Even all matching model/build fields establish target-class consistency plus human confirmation, not cryptographic proof of a unique physical unit; never claim stronger identity.

The five property reads, kernel read, and `id` are identity-gate reads, not part of the 15 network delta reads. A future executable collector must print these in its dry run **ahead of** all phase reads and enforce the comparison. The current 43T0-A script does not do so; this is the primary NO-GO reason. The serial must never enter Git evidence, and the collector must not derive current identity solely from the old manifest.

## Collector, failure, privacy, and parsing contract for offline correction

A corrected dry-run plan must show literal ordered argv arrays for host enumeration, the seven identity reads, and the 15 network reads, plus private host destinations. Future execution must use direct argv (`shell=False`), a fixed table, no host shell, no target command-string interpolation, no arbitrary input, no redirection, no target files, no fallback, and no privilege path. Place raw bytes only in a mode-0700 Mac directory outside Git, with bounded stdout/stderr, UTC start/end, phase, argv, status, and SHA-256 in a host manifest. Dry-run and execution must be mechanically separate; an explicit execution flag would be needed later. The dry run must remain incapable of contacting Honda in this milestone.

Classify every future result as `SUCCESS`, `COMMAND_UNAVAILABLE`, `PERMISSION_DENIED`, `TIMEOUT`, `OUTPUT_LIMIT_EXCEEDED`, `UNEXPECTED_FORMAT`, or `ADB_TRANSPORT_FAILURE`. For any non-success: stop immediately, retain bounded host-only partial evidence, and perform no troubleshooting on Honda. `ifconfig` unavailable means `STOP_AND_RETURN_PARTIAL`; do not install or substitute `ip`, `netcfg`, or BusyBox. No root, `su`, SuperSU, `adb root`, `run-as`, service start/stop, network configuration, file writes, `adb pull/push`, process signals, ptrace, listeners, port probes, packet injection, or Type111 activity.

Offline Mac-side post-processing should parse sanitized fixtures deterministically: `/proc/net/dev` interface RX/TX bytes and packets; IPv4 route little-endian destination/gateway/mask, flags and metric; `/proc/net/ipv6_route` destination/source prefixes, next hop, metric, flags and interface only after its exact kernel format is validated; `/proc/net/if_inet6` address, index, prefix, scope, flags and interface; `ifconfig` interface, IPv4 address and relevant state. No extra target parse commands. Raw output may contain MACs, unrelated local addresses, gateways, counters, and device/network details. Commit only relevant interface name, family, required Honda local address/scope, route association and phase relationship; redact MACs, unrelated peers/interfaces, Wi-Fi data, device serial, and credentials.

## G11 promotion and user boundary

G11-A can become `YES_OBSERVED` only with a directly identified relevant interface. G11-B can become `YES_OBSERVED` only when its Honda local address maps directly to that interface. G11-C may become `IPv4`, `IPv6`, or `DUAL` only from observed path evidence. G11-D becomes `YES` only with a route supporting the identified interface/address path. G11-E remains `NO / READ_BLOCKED_WITHOUT_PRIVILEGE`; G11-F remains `NO`. No observational delta proves a new listener can bind or be reached from an iPhone.

If a later review approves a live procedure, the user's actions are limited to parking/powering the Honda normally, connecting the Mac via the existing route, leaving the iPhone disconnected for baseline, connecting normal wired CarPlay for the connected phase, confirming center/audio/cluster operation, disconnecting normally for the final phase, and confirming stock behavior. Stop on identity or UID mismatch, ambiguous target, unavailable/denied/oversize/timed-out/malformed read, ADB instability, any requested command deviation or privilege, or abnormal center CarPlay/audio/cluster. No vehicle troubleshooting or modification. No Honda rollback is planned because no ClarityLink target mutation is proposed.

## Final ECC decision and next milestone

**`43T0_DELTA_ECC_NO_GO`.** The current five-read content and three-phase structure are narrowly justified, but the printed plan lacks current-target identity validation and its no-argument `ifconfig` output remains a runtime unknown. The smallest offline correction is a revised dry run that lists and gates the fixed current-target identity checks before the same 15 network reads, documents fail-closed `ifconfig` behavior, and is reviewed again. Do not implement a live execution path or contact Honda under this decision. **Next milestone: 43T0-C — offline identity-gated delta dry run and ECC re-review.**

## Offline verification

The existing dry-run source was parsed statically: exactly five fixed reads and three phases (15 proposed reads), with no process-execution import. The collector itself was **not executed**, honoring this milestone's explicit boundary. Relative Markdown links, scoped secret/redaction pattern scan, and `git diff --check` passed. No production code or parser was changed, so no production suite or parser tests were required. No raw 40E capture was staged.
