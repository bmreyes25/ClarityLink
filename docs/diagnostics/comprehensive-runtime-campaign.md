# Type111 evidence follow-up

**Campaign:** `CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031`
**Baseline:** PR #124 at `0136ac241d94e1ebb1cc4403c07fd480728b47d6`
**Result:** Offline simulator plus a fixed, authorization-gated live backend; no current session is authorized.
**Deployment:** `safeForHonda() == false`; not authorized.

The October 31 C-P campaign is historical and is not repeated. Its 135
commands did not resolve the new Type111 questions. The comprehensive plan
retains all eight phases and 19 evidence objectives; command/test completion
never substitutes for an observed objective.

## Existing high-value runtime archive

Before proposing a new visit, the existing private 2026-09-29 disconnected
`jmcs` archive was rechecked read-only in the owner’s USB checkout. Its
70-entry `SHA256SUMS.txt` matches every retained file. The API 17 maps parser
accepts all 202 mappings, identifies the `/system/bin/jmcs` executable
mapping beginning at historical load bias `0x4008f000`, and confirms 45 unique
mapped shared-object paths. The same archive contains 10 socket FD symlinks;
exact inode joins identify two TCP and five Unix-socket rows. Network contents
and peer addresses were not exported during this verification.

This is useful historical runtime evidence and avoids recapturing an identical
disconnected baseline merely to reproduce known facts. It is not a current
process snapshot: the preserved set lacks `smaps`, `stat`, `cmdline`, and `exe`
files, and the ASLR addresses must never be reused. It cannot prove a current
process epoch, page-size fields, connected-state socket changes, `/info`
values, SETUP acceptance, or Display 1 ownership. Maps permissions and the
main executable mapping are available historically; resident-page accounting
and all smaps fields are not.

A separate 2026-09-25 CarPlay-connected private capture also contains maps,
FD symlinks, and TCP/UDP/Unix tables. Offline parsing finds 54 mapped `.so`
paths and 13 exact FD/socket inode joins among 15 socket FD links. Its manifest
records command names and byte counts but has no per-file SHA-256 inventory.
It belongs to a different process epoch and date than the disconnected
archive, so the two are not a synchronized lifecycle comparison and cannot
replace new same-session snapshots. Together they establish that previous
`su -c` reads did obtain useful receiver metadata in past sessions;
they do not justify the same invocation against the current target state.

## Current experiment view

The controller and Studio readiness JSON expose **Current objective**,
**Latest evidence**, **Experiment ready**, **Run experiment**, **Results**, and
**Next iteration**. The current objective is offline SuperSU method analysis
needed to justify (or reject) the minimum `jmcs` maps/FD observation. The live
backend is implemented, but no live session is ready; none of the 19 Honda
objectives is confirmed. A dry-run or simulation cannot set campaign success.

| Question | Shortest useful method | New evidence / limit | Current gate |
|---|---|---|---|
| `jmcs` mappings, load bias, protections | Exact PID/start-time-bound maps/smaps | Historical disconnected maps, load bias and mapped libraries are verified; no smaps or complete process-epoch bracket, so current state remains unknown | Current access blocked on justified method |
| Process-owned sockets | Numeric FD symlink inode joined to same-phase TCP/UDP/Unix inode | Ownership only on exact inode match | Blocked with maps/FD access |
| Loaded libraries | Parse actual `maps`; compare static ELF imports separately | Runtime library set, not static dependency inference | Blocked with maps access |
| `/info` advertisement | Receiver's decoded plist response/serializer boundary | Static dataflow exists; bounded logs/dumpsys do not show response values | No reviewed observer |
| SETUP and Type111 rejection | Decoded request/response boundary before private handlers | Static path is mapped; passive campaign cannot expose handler acceptance or plist values | No reviewed observer |
| Display 1 and Navigation | Bounded DisplayManager/WindowManager/SurfaceFlinger snapshots at selected/deselected/reselected states | Adds lifecycle deltas; does not prove physical pixels, z-order safety, or frame admission | Separate Level 2 review/session |
| HondaHack casting lifecycle | Ordinary existing UI Start/Stop with stable-state snapshots | Tests ordinary withdrawal/restoration, not a supported Type111 ingress | Qualified safety review and session gate |

`/info` static dataflow is `_requestProcessInfo` → `AirPlayCopyServerInfo` →
binary-plist response serialization ([source](../../research/carplay/honda-server-info.md)).
SETUP parsing and response construction are mapped in the
[43T1-R3 seam report](../../research/runtime/43t1-r3-setup-seam-map.md). A
packet capture alone cannot prove decrypted plist content or handler
acceptance. No reviewed runtime observer currently exposes either boundary
without receiver attachment, injection, or modification.

## Eight phase decisions

| Phase | Scope | Risk | Evidence value | Readiness |
|---|---|---:|---|---|
| 0 | Owner baseline and exact identity | 1 | Safe starting state and exact unit | Offline checklist only |
| 1 | Existing ordinary ADB, target identity, bounded diagnostics | 1 | Current build/shell/process identity | Owner session approval only; the 7 fixed reads are an unchanged subset of the prior routine identity surface |
| 2 | Archived SuperSU binary/policy/daemon side-effect assessment | 2 | Whether current privileged access can be justified | Static archive review complete and a historical `su -c` read is documented; exact invocation effects and current prompt/daemon/policy state remain unknown; no `su` invocation in this task |
| 3 | Maps/smaps, libraries, FD links and socket inode correlation | 2 | Current mappings and socket ownership | **Blocked for new capture:** the old disconnected archive answers historical maps/libraries and exact socket inode joins; current state needs a justified access method |
| 4 | Disconnected baseline; stock CarPlay active; Navigation selected/deselected/reselected while connected; disconnect/reconnect/final disconnect | 2 | Comparative display, bounded log, USB/network, and receiver-process lifecycle deltas; not protocol payload | Technical and qualified Display 1 safety review plus one exact session approval pending; cannot answer `/info` values |
| 5 | Navigation selected/deselected/reselected after CarPlay disconnection | 2 | Compare factory Navigation display/window/layer dumps with active-CarPlay context; View class/lifecycle remains unexposed | Technical, qualified safety review, and session approval missing |
| 6 | Existing HondaHack ordinary UI casting/withdrawal | 2 | Casting and ordinary restoration behavior | Technical and qualified Display 1 safety reviews missing; the reviewed scope is only normal existing Start/Stop behavior |
| 7 | Ordinary restoration and host evidence integrity | 1 | End-state and evidence integrity | Only with an authorized preceding session |

Phase 6 UI sequence is fixed: casting disabled baseline → ordinary Start
Casting → stable display snapshot → Navigation deselected → Navigation
reselected → ordinary Stop Casting → verify factory Display 1, Navigation,
center display, cluster and audio restored. No install, hook change, private
API, forced stop, induced warning, or retry.

Phase 4 captures the disconnected baseline, ordinary stock CarPlay active
state, Navigation selection changes while connected, normal disconnection,
reconnection, and final disconnection. Captures occur only after the owner
confirms each stable state. The separate Phase 5 Navigation pass compares the
factory Navigation display after CarPlay is disconnected. Each stable-state
capture is compared with its baseline and adjacent state; identical hashes are
reported as unchanged, not as new evidence.

## SuperSU access decision

The archived `/system/xbin/su` is a 75,348-byte ARM EABI5 Chainfire
SuperSU-family binary (SHA-256
`d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`), archived
mode 06777. Static strings/imports show daemon/autodaemon, request, log/config,
permission, mount/ioctl, process, IPC, and credential-changing capabilities.
Earlier owner records confirm a narrowly scoped `su -c` read succeeded on the
historical unit, so this is a demonstrated access path, not a hypothetical
mechanism. The read did not attach, signal, reconfigure, or replace `jmcs`;
that does not audit writes made internally by `su` or its daemon. The exact
ordinary `su -c` path, current policy/config, daemon-present/absent
behavior on API 17, actual prompt/log/write reachability, and process impact
remain unresolved. Prior `su -c id` only proves past UID 0 access. It does not
prove zero writes or harmlessness. Ordinary shell previously received
permission denied for `maps`, `smaps`, and `fd`; no less-intrusive source is
currently established. See the archived
[execution-path analysis](../../research/runtime/supersu-execution-path.md),
[write inventory](../../research/runtime/supersu-write-side-effects.md), and
[40E4 decision](../../step-reports/40E4-zero-write-privilege-path.md).

The existing `PrivilegedRead` API has enumerated identity/process/FD/network
operations and binds the installed `su` fingerprint. This fixed API does not
resolve the undocumented SuperSU behavior and is not permission to invoke it.
If that existing path is justified offline and independently reviewed, the
exact minimal read proposal is below. It is **not executable or authorized
now**. Use only enumerated operations; do not turn `su -c` into an arbitrary
shell executor. Bound every operation to 20 seconds/4 MiB and validate process
identity before and after. One FD-list read supplies all symlink targets; parse
numeric FDs and match socket inodes against tables captured in the same
bracket. Do not issue one command per FD or read process memory, environment,
credentials, or keys.

```text
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/stat"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/status"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/cmdline"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/maps"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/smaps"
adb -s <private-approved-serial> shell /system/xbin/su -c "ls -l /proc/<verified-jmcs-pid>/fd"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/net/tcp"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/net/tcp6"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/net/udp"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/net/udp6"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/net/unix"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/stat"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/status"
adb -s <private-approved-serial> shell /system/xbin/su -c "cat /proc/<verified-jmcs-pid>/cmdline"
```

The shortest blocker-resolution path is a bounded control-flow analysis of the
exact hash-matched `su` binary plus any matched daemon/config/log artifacts,
focused on the normal `-c` branch, pre/post daemon behavior, prompt handling,
files opened with write-capable flags, durable policy updates, and child
credentials. Then obtain independent technical review of that exact evidence
and fixed reader. If the matching active policy/daemon state is absent or the
branches remain unresolved, keep Phase 2/3 blocked; do not treat successful
historical commands or owner risk acceptance as proof of no side effects.
Never execute `su` to discover its effects.

## Controller, authorization and safety

`live_execution_enabled` remains false in the published proposal and unfilled
template. A qualifying one-run owner record must set it true only after its
selected phase gates pass. The record lists review types derived from phase
risk; the owner separately confirms technical reviewer independence and, for
Display 1, the safety reviewer’s qualifications. The artifact validator checks
structure and exact source pins only. It cannot prove reviewer identity,
independence, competence, or certification. Review-gated execution requires a
clean worktree at the reviewed commit. Ordinary `ps` provides PID continuity
only; the controller does not claim start-time or executable identity without
the blocked Phase 3 source.

The controller verifies eight phases and 30 fixed API-17 argv shapes. Ordinary
phases do not repeat known-inaccessible root-owned `/proc/PID` reads: they use
exact target properties, shell identity, `ps` PID continuity, and public
display/network snapshots. PID start-time, cmdline, root UID/GID, and executable
revalidation belong only to the blocked Phase 3 privileged method.
source/profile/manifest pins, per-run binding, PID/start-time identity, bounds,
private evidence requirements, abort behavior, evidence coverage, and
terminal/notification outcomes. Dry-run and fault simulation use no device,
ADB lookup, subprocess, or capture file. The live backend is fixed-operation
and one-use authorization-gated; it does not discover devices, invoke root, or
accept arbitrary commands. Proposal-level live execution remains false, and
the current readiness view correctly shows that no session is authorized.

Use one owner decision for one exact session and an explicitly listed set of
compatible phases/categories. The approval includes exact vehicle/endpoint,
fresh expiring run ID and nonce, readiness checks, source pins, stop/recovery
scope and only risk-required review artifacts. Adding a phase or action outside
that set requires a new decision. The owner physically present confirms Park,
parking brake, reviewed power state, normal displays and no abnormal warning.
One-use authorization and nonce markers are separate from historical C-P
ledger records.

Before a session, confirm the evidence destination: host-local and outside the
repository; owner-only directory and file modes; cloud sync disabled; and a
hash inventory ready. Do not put serials, raw procfs/log output, images, or
credentials in the public report. Abort cleanup is host-only; no automatic
retry, transport switch, privilege escalation, vehicle power-off, or next
session. The owner confirms the exact normal-state restoration observations
and the available manual stop route before authorizing any transition. For
Display 1/HondaHack, confirm factory Display 1 ownership, Navigation selection,
center display, cluster, and audio return to their pre-session state. If any
restoration step is unverified or unavailable, do not start that phase. See the
[three-level workflow](../../docs/safety/experiment-risk-levels.md).

**FULL CAMPAIGN LIVE READY: NO. PARTIAL CAMPAIGN LIVE READY: NONE.** Current
external gates are a justified Phase 2/3 access method or less-intrusive
source, an observer for `/info`/SETUP if those values remain required, a
technical review for Level 2 methods and qualified Display 1 safety review for
Phases 4–6. A real Claude read-only review found actionable controller issues;
they are being corrected. That review is technical input, not final approval or
qualified vehicle-safety review. No qualified safety review was obtained.
Do not prepare the Honda for this campaign.
