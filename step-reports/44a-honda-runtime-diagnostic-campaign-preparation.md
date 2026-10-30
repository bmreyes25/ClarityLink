# CL-HONDA-RUNTIME-EVIDENCE-20261030 — offline preparation

**Decision:** `OFFLINE_PREPARATION_REVIEWED`; `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`; `safeForHonda() == false`.

This report prepares a bounded diagnostic proposal. It records no Honda/ADB/vehicle/iPhone operation, issues no live command, and does not authorize the parked session. The existing policy requires exact owner approval and qualified independent safety review for Level C activity. The current integration-readiness record also says Honda ADB observation is not authorized. Neither AI review in this preparation is qualified vehicle-safety approval.

## Evidence reconciliation

| Source | Established | Still unknown or out of scope |
|---|---|---|
| [Step 40E](40e-readonly-runtime-preflight.md) and [40E2](40e2-privileged-read-preparation.md) | Android 4.2.2/API 17, ARMv7, ordinary ADB shell UID 2000, `jmcs` identity continuity through normal CarPlay connect/disconnect, and increased connected thread population. Ordinary shell could not read `jmcs` maps, smaps, or FD directory. | Current process epoch, mappings, load bias, page size, executable permissions, and process-owned sockets. Do not repeat the full 40E capture. |
| [40E3/40E4 privilege findings](40E4-zero-write-privilege-path.md), [root-path report](../research/platform/honda-root-path.md), and [privilege matrix](../research/runtime/collector-privilege-matrix.md) | A SuperSU-family `/system/xbin/su` existed in archived images and `su -c id` succeeded historically. | Its live identity/state is not established. The archived file mode is `06777`; no zero-persistent-write privileged path is established. No `su`, `adb root`, setting change, helper, or alternate privilege route belongs in this plan. The privileged live CLI remains disabled. |
| [43T0-D4](43t0d4-netcfg-live-network-delta.md) | A phase-correlated CarPlay `usb0` IPv6 link-local/network-route delta reversed after disconnect. | D4 did not associate any socket with `jmcs`. Do not repeat broad interface enumeration. |
| [43P](43p-current-ios-type111-oracle.md) | Separate PlayPort lab saw Type111 requested before Type110, distinct stream identity/ports, VideoConfig, and sustained media events. | This is third-party lab evidence, not Honda behavior, Honda authority, or a Honda key-context contract. |
| [43S](43s-honda-runtime-readiness-review.md), [43S1](43s1-executable-trampoline-listener-proof.md), [43S2](43s2-native-helper-reentrancy-readiness.md), and [PR #117](https://github.com/bmreyes25/ClarityLink/pull/117) | Static callsites and offline pass-through/trampoline models are known. PR #117 changes the offline stock-pass-through assembly/rewrite experiment and its tests. | No code execution inside Honda, Type111 acceptance, supported runtime loader seam, or receiver modification recovery is proven. PR #117 was open with no review decision; Offline CI and CodeQL passed while its API 17 navigation check failed at review time. It is not runtime evidence. |
| CL-HH-02/03, CL-HH-06 summaries, [CL-R10B](../research/hondahack/cl-r10b-display-ownership.md), [CL-DISP-02](../docs/research/cl-disp-02-host-contract-discovery.md), [Display 1 diagnostics](05b-display-diagnostics.md), and [HondaHack path](../research/hondahack/hondahack-display-path.md) | Logical Display 1 is the separate 800×480 external/HDMI layer. `ExternalDisplayOutService` owns its Android windows; HondaHack 7.7.7 uses an Xposed-injected View path. Casting has appeared on the physical cluster; one Door Open recording showed preemption and restoration. | Accurate physical Navigation aperture, page exit/re-entry withdrawal, guaranteed Stop Casting restore, all warning classes, and any supported arbitrary-frame ingress. Do not trigger warnings or modify hooks. |

The requested September 29 bundle was present only in the private host capture directory. Its existing baseline and connected `logcat` samples were processed locally by the new content-discarding event summarizer. Both returned `TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS`, with no matched event markers. This is a bounded result about those two log samples only; it does not mean the phone cannot send Type111.

## Evidence coverage and next decision

| Question | Current result | Proposed evidence and limit |
|---|---|---|
| Q1. Current ADB/root/debug state | Historical ordinary shell UID 2000 is established; present state is unknown. Historical SuperSU is unsafe to invoke based on current evidence. | After separate approval, the owner must privately provide/confirm the exact existing ADB serial; the collector rejects live `auto` selection before ADB initialization. Observe selected build/debug properties and any already-visible UI state without launching a privileged app or changing settings. No `su` attempt. |
| Q2. Current maps/load bias/page protections | Not readable from ordinary shell in 40E. | Keep unknown. Revisit only after a separately reviewed, non-escalating source of read access is demonstrated. Do not probe again with a repeated broad capture. |
| Q3. `jmcs` socket endpoints | D4 is system-wide only. | The new offline join reports endpoints only on exact `jmcs` FD-symlink inode equality. No FD read is currently approved or known to be available; no global socket will be attributed to `jmcs`. |
| Q4. Loaded native libraries | Static ELF dependencies are available; current mappings are not. | Loaded-library claims require a permitted current maps source. Static dependencies remain labeled static. |
| Q5. `/info` and SETUP logs | Two old bounded log samples contained no recognized event markers. | On a separately approved observation, summarize only existing bounded log output. Logs do not prove complete plist/payload visibility. |
| Q6. Type111 request | `TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS` in those two 40E samples. | Keep that exact status if absent in future available logs. It cannot show phone incapability or protocol incompatibility. |
| Q7. Display 1 ownership | External-display host and HondaHack path are established statically and in prior observations. | Recheck only ordinary display/window/layer snapshots around the selected page. A snapshot cannot prove physical crop or supported frame admission. |
| Q8. Navigation transitions | Synchronized page deselect/reselect lifecycle is missing. | If separately approved, use ordinary factory Navigation controls and record selected → deselected → reselected, with bounded display diagnostics and observer notes. HondaHack casting is a separate gate. |
| Q9. Recovery | Ordinary disconnect/shutdown has prior normal behavior evidence; no native-corruption recovery is established. | Before any session, record the normal factory shutdown route and baseline. Post-test check only ordinary stock behavior. This is not rollback proof for corrupted native code. |
| Q10. Active instrumentation need | Existing logs and display diagnostics are the least intrusive first step. | Defer instrumentation until passive results are reviewed. No helper, ptrace, Frida, Xposed hook change, receiver patch, listener, or target-side code is included. |

## Proposed parked observation checklist — not yet authorized

Each live action below is Level C under the repository policy and must wait for both (1) qualified independent safety review of this exact procedure and (2) a separate explicit owner approval. Keep `safeForHonda() == false` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` throughout preparation.

### Scope and fixed collection surface

- Vehicle stationary in Park, outside an enclosed garage if READY power is needed. Follow Honda operating guidance for 12 V power; account for possible automatic engine start. Keep stock displays and audio. A second person may observe only.
- No Honda ADB is performed in this preparation. If later approved, use only the already-authorized, explicitly named ADB serial with `-s <exact-serial>`; do not use `--serial auto`, enumerate devices, scan a network, enable a new ADB transport, or retry through another endpoint.
- Use the existing `tools/honda-readonly-preflight/collector.py` fixed-operation interface and legacy `adb shell` service. Do not use `exec-out`. The planned fixed operations are `id`, `ps`, `getprop` for only `ro.build.version.release`, `ro.build.version.sdk`, `ro.product.device`, `ro.product.board`, `ro.hardware`, `ro.secure`, and `ro.debuggable`; process identity reads of `/proc/<pid>/stat`, `cmdline`, and `status`; `dumpsys display`, `dumpsys SurfaceFlinger`, `dumpsys window`; and bounded `logcat -d -t 500`. Existing limits are 5 seconds/64 KiB for `id` and each property read; 20 seconds/32 MiB for `ps`; 10 seconds/4 MiB for process identity reads; 15 seconds/4 MiB for each display diagnostic; and 15 seconds/4 MiB for logcat. Target paths and arguments must be passed as direct argument arrays from the existing allowlist; no shell program construction or interpolation. The endpoint stays private and is not written to the public plan.
- Output must go to a new host-only directory outside the repository, mode `0700`; files and manifest mode `0600`; source/operation manifest and SHA-256 inventory retained privately. New captures summarize bounded logcat in memory and persist only allowlisted event categories/counts/timestamps, result status, and digest; neither raw log lines nor stderr are stored. Do not copy endpoints, identifiers, photos, or derived private evidence into Git.
- The existing collector's broad 40E three-phase profile is not the proposed capture: do not repeat its CPU, network, thread, or full platform inventory. A campaign-specific, human-marked display-phase controller now defines the Navigation transition order and an optional separately gated HondaHack sequence. It is not wired to a live collection profile and must not be used for field work.

### Ordered phases

| Phase | Human action / observation | Fixed host evidence | Stop rule |
|---|---|---|---|
| 0 — baseline | Confirm Park/stationary, normal cluster and center display/audio, phone disconnected, no warning or abnormal behavior. Record existing debugging state without changing it. | None. Record host monotonic marker and checklist. | Any abnormal baseline is no-go; do not connect ADB. |
| 1 — target identity | Only after separate approval, use the exact existing ADB serial. | `id`; selected identity/debug properties; `ps` and the `jmcs` PID/start-time identity using existing parser. | Any target mismatch, timeout, transport error, unexpected command output, or process ambiguity: stop. No alternate endpoint. |
| 2 — no privilege escalation | Observe only an already-visible authorization prompt/state; do not launch SuperSU or issue `su`. | No privileged command. Record “not checked” if no state is already visible. | No attempt to change access. Maps/FD access remains unknown for this session unless a separately reviewed source exists before approval. |
| 3 — stock CarPlay connected | Connect iPhone through its normal physical USB flow and wait for ordinary stock CarPlay. | Reconfirm `jmcs` identity; bounded `dumpsys display`, `SurfaceFlinger`, `window`, and log tail. No broad network capture. | Stop on any factory behavior change or identity instability. |
| 4 — factory Navigation selected | Use ordinary factory controls to select Navigation; observer records physical cluster and host timestamp. | Same bounded display/window/layer/log snapshot. | Do not invoke private Binder/control APIs or trigger warnings. |
| 5 — Navigation deselected | Use ordinary factory controls to leave Navigation; observer records withdrawal/page ownership. | Same bounded snapshot. | Stop if another factory page or warning behaves unexpectedly. |
| 6 — Navigation reselected | Re-select Navigation; record restoration. | Same bounded snapshot. | Stop if Navigation does not return normally. |
| 7 — HondaHack, optional separate approval | Only if its separate gate is explicitly approved and existing casting is already functional: disabled → ordinary Start Casting → Navigation deselect/reselect → ordinary Stop Casting. | Same bounded snapshots and observer-only physical record. No installation, hook edits, warning triggers, or forced process actions. | Any unexpected display, warning, navigation, or audio behavior: stop; do not continue to Stop Casting unless ordinary UI remains responsive and the safety reviewer approved that recovery action. |
| 8 — normal disconnect | Disconnect CarPlay through the ordinary phone/user flow. | Reconfirm process identity/restart status and bounded display/window/layer/log snapshot. | No new network scan or repeated baseline inventory. |
| 9 — restoration | Verify phone disconnected, stock center display, cluster, Navigation, and audio normal; end the authorized ADB session. | Host-only completion record and hashes. No target changes are expected. | If restoration is unclear, stop and ask the owner; no additional device command. |

The new controller cannot yet run these human-marked phases as a single immutable capture: it has no campaign-specific fixed operation profile, immutable per-phase manifest, or source-hash pin. Those pieces and their exact offline dry-run review are required before a field-ready harness or execution-authorization request can be claimed. Therefore this document requests commissioning an independent review, not a command to execute the session.

## Failure card — mandatory owner decision

On any unplanned failure, stop the affected phase, retain completed host output, and make no retry, privilege change, command substitution, or transition to another active phase. First assess stock factory behavior. Present this record and await the owner's direction:

**Phase:**

**Action attempted:**

**Expected result:**

**Actual result:**

**Risk to stock behavior:**

**Evidence preserved:**

**Possible next actions:** stop and close session; resume only a previously approved independent phase; or request a new reviewed plan.
**Recommended safest action:** stop the session and preserve current factory behavior.
**Owner decision required:** whether to stop, or which separately approved next phase to consider.

No tool or process should automatically continue after a failure.

## Instrumentation decision matrix — separate future proposal

| Method | Missing datum | Passive ADB/logs sufficient? | Target change / privilege | Interruption and compatibility | Cleanup / recovery | Decision |
|---|---|---|---|---|---|---|
| A — existing diagnostics | Page transitions, display/window/layers, existing event markers | Likely sufficient for those visible events; not payloads, current maps, or FD ownership | No target modification; ordinary ADB would still need Level C approval | Low interruption expected; API 17 commands are already used by the existing collector | Close ADB; ordinary stock restoration only | First choice after approval; a human phase controller exists, but the capture profile is not field-ready. |
| B — existing privileged read | `jmcs` maps/smaps/FDs | Ordinary shell already denied these in 40E | Uses SuperSU path; may create daemon/log state; zero-write behavior unproven | Process interruption unknown; historical root success is not a safety case | No proven cleanup or independent recovery | Excluded. New safety/recovery review and exact owner approval required before reconsideration. |
| C — temporary helper | A precise datum unavailable from existing diagnostics | No | Installs or executes new code, likely privilege required | API 17/ARMv7 compatibility and process effects unproven | Must prove removal and no persistence; not established | No helper prepared for vehicle use. Offline-only design study can follow a concrete missing datum. |
| D — dynamic instrumentation | In-process `/info`, SETUP or lifecycle values | No | ptrace/injection or hook/runtime changes likely | Receiver suspension, crash/deadlock, Type110 disruption, and version compatibility risks; historical Android 4.2/ARMv7 support must be demonstrated | Cleanup/recovery not established | Do not select Frida/ptrace/Xposed by popularity. Require a separately reviewed evidence-based proposal. |
| E — receiver binary instrumentation | Exact receiver boundary values | No | Code patch/loader change | Highest; stock path and Type110 behavior could be affected | Ordinary shutdown is not recovery from native corruption; independent restore proof absent | Rejected for this campaign. PR #117 is not proof of safe execution or recovery. |

## Offline tooling and verification status

The existing collector already provides direct argv execution, fixed operation/path allowlists, target identity checks, bounded time/output, host-only capture files, hashes, and an aborting three-phase session. The existing analyzer already parses maps/smaps, derives load bias from mapping evidence, tracks process identity, and checks FD/socket inode overlap.

This preparation adds two offline analysis details: exact `jmcs` FD-inode to socket-endpoint joins, and a bounded log marker summary which returns event categories/counts/timestamp bounds without returning source log lines. New captures discard log text in memory before writing any artifact; stderr is represented by size/hash metadata only. It does not capture, decrypt, or expose plist values, credentials, or media. New synthetic tests cover exact inode ownership, collection-time log filtering, Type111 status wording, and input caps.

The five private Type111 reference notes and private deep-diagnostics blueprint were reviewed from the owner-only research tree. Their detailed contents remain there; this public report carries forward only the already-published conclusions and no private binary values or captured evidence. Independent AI reviewers found no basis for live execution, confirmed that the current SuperSU route must stay excluded, and identified the missing field-ready capture profile and qualified safety review; the human phase controller added afterward remains offline-only. Their reviews are not qualified vehicle-safety approval. No raw or derived Honda capture is included in this report or the source changes.

## Owner authorization request

Please decide whether to commission a **qualified independent vehicle-safety review** of this exact checklist and the incomplete human-marked capture profile. Do not authorize live execution yet: the current repository gate prohibits Honda ADB, the capture profile is not field-ready, there is no safe privileged path, and qualified review is outstanding. If those prerequisites are later closed, I will present the final, hash-pinned procedure and ask for a separate explicit owner authorization covering the exact phases (with HondaHack as a separate optional authorization). Until then, no Honda, ADB, iPhone, root, or instrumentation operation is authorized.
