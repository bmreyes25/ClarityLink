# Vehicle testing and diagnostic authorization

ClarityLink's primary goal is genuine iPhone-origin Type111 video on factory
Display 1 while factory Type110 CarPlay remains normal on Display 0 and factory
safety behavior retains priority. Offline research and prototypes are distinct
from live permission. `safeForHonda()` remains `false` and
`VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remains in force.

## Offline engineering authorization

Offline engineering on the authorized Mac is permitted without a new owner
permission request for each task. It includes archived firmware/runtime
analysis, host collectors and parsers, fixed-operation manifests, process and
socket correlation, synthetic fixtures, API 17 builds/tests, offline
instrumentation prototypes, receiver/display design, evidence review, and
public-safe pull requests. Private Honda raw or derived evidence stays outside
Git. Offline preparation never authorizes ADB, an iPhone connection, or vehicle
operation.

## Live diagnostic categories

Each category needs a separate exact-scope proposal, source/profile/manifest
binding where tooling is used, technical review, owner approval, stop rules,
private evidence handling, and restoration criteria. A category lacking an
approval remains blocked in the evidence matrix; it is not deleted from the
campaign requirements.

| Category | Permitted preparation | Live execution requirements |
|---|---|---|
| Ordinary unprivileged ADB | Fixed argv, exact identity checks, API 17 behavior tests, bounded collectors, and synthetic fixtures | New exact-run owner approval; one already-authorized endpoint; exact target identity; no scanning, endpoint fallback, transport changes, root, installation, writes, or retries; parked conditions and restoration checks. |
| Stock iPhone/CarPlay transition | Fixed ordinary user connect/disconnect sequence and no-capture transition gates | Separate exact-run owner approval for each planned phone transition; no pairing/settings changes, packet injection, or evidence collection during transition. |
| Existing privileged read | Inspect archived root/SuperSU evidence and design fixed procfs reads | Current evidence identifies no justifiable zero-write access method. Owner approval is necessary but insufficient: new technical evidence and independent side-effect/recovery review must first justify a method. No `su` invocation under the current finding. No `adb root`, new root tool, or fallback escalation. |
| Factory Navigation observation | Offline phase design and display snapshot comparator | New exact-run approval for ordinary owner-operated page select/deselect/reselect only. No private controls, warning triggers, or snapshot collection during transitions. |
| Existing HondaHack observation | Analyze retained observations and define a fixed ordinary UI sequence | Separate exact HondaHack approval, independent technical review, and qualified vehicle-safety review are mandatory because casting involves factory Display 1. Existing build/state only; casting disabled → ordinary start → Navigation deselect/reselect → ordinary stop → baseline check. No install, Xposed change, new hook, forced warning, or private API. |
| Temporary runtime instrumentation | Synthetic or bench-only compatibility prototype and risk analysis | Not authorized by the comprehensive diagnostic campaign. Requires its own exact signal, method, target compatibility proof, security/technical review, owner approval, interruption and Type110 impact analysis, bounded cleanup, and independent recovery evidence. |
| Receiver/display modification | Offline receiver, display, or binary prototype | Separate higher-risk authorization, qualified independent vehicle-safety review, legitimate protocol/security authority, exact change scope, verified independent recovery, exact owner approval, and protected deployment review. No automatic or persistent deployment. |

The October 31 `CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION` C-P campaign is
complete and historical. Its eight phases, 135-command manifest, authorization,
source lock, profile hash, and evidence are a fixed baseline. Do not extend or
reuse those pins or authorization. The distinct comprehensive campaign is
`CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031`; this document authorizes offline
engineering only, not its live execution.

## Comprehensive campaign phase policy

The full proposed sequence retains every phase:

| Phase | Evidence objective | Category and gate |
|---|---|---|
| 0 — baseline safety and identity | Parked condition, warning/display/audio baseline, phone state, shutdown route, backup inventory | Owner-attested precondition before any live category. No ADB. |
| 1 — ordinary ADB capability | Exact target identity, shell UID/groups, selected properties, receiver process identity, permitted diagnostics | Ordinary unprivileged ADB approval. |
| 2 — existing root capability review | Existing `su` presence/provenance, visible authorization state, side effects, recovery implications | Offline review first. Step 40E4 found no currently justifiable live access method; any future `su` command needs new evidence, independent review, and separate exact approval. No `adb root`. |
| 3 — receiver maps and socket ownership | PID/start-time-bound maps/smaps, executable mappings, load bias, libraries, FD/socket inode joins, `usb0` correlation | **Currently blocked:** Step 40E4 found no justified privileged access method. New evidence and independent side-effect/recovery review must establish one before a separate exact approval is requested. Denial remains `PERMISSION_DENIED`; no inferred mapping or ownership. |
| 4 — three-state CarPlay | Disconnected → connected → disconnected → reconnected → final disconnect; process/session, `/info`/SETUP/log metadata, and bounded `/proc/net` plus `usb0` state | Separate ordinary ADB and stock iPhone transition approvals. No packet injection or protocol modification. |
| 5 — Display 1 and Navigation | DisplayManager, WindowManager, SurfaceFlinger and ordinary Navigation selected/deselected/reselected states | Ordinary ADB plus separate Navigation-transition approval. Snapshots do not alone prove physical pixel ownership. |
| 6 — existing HondaHack | Existing casting off/on, Navigation transitions, stop and baseline restoration | Separate HondaHack approval, independent technical review, and qualified vehicle-safety review because Display 1 is involved. This phase remains present even when blocked. |
| 7 — recovery and restoration | Normal CarPlay, Navigation, center display, cluster, audio, process/host cleanup, evidence integrity | Approval bound to the selected preceding phases; no remote vehicle power action. An abort uses host-only cleanup; do not issue another vehicle command after a live error without a separately reviewed and authorized recovery action. |
| Post-session — instrumentation decision | Decide which exact missing signals need logs, privileged reads, helper, dynamic instrumentation, or binary experiment | Offline design/review only. No live instrumentation under this campaign. |

The scope is a staged research plan, not a single undifferentiated permission.
If a phase lacks its gate, mark it `BLOCKED_PENDING_AUTHORIZATION` and continue
only with already approved independent offline work. Do not skip it in the
requirements matrix or silently treat it as complete.

## Privileged-read and SuperSU boundary

Historical work identified a Chainfire SuperSU-like `/system/xbin/su` in an
archived rooted image and a prior successful `su -c` observation. Step 40E4
found no currently justifiable privileged path. The binary's historical mode
was unusually permissive; invocation may write authorization logs or daemon
state. Current installed state and zero-write behavior are not established.
Therefore:

- `su` is not part of ordinary ADB and must never be invoked as a fallback.
- First review archived provenance, file metadata, prior logs, current evidence
  records, and recovery implications offline.
- Reconsideration requires new offline evidence establishing a justified access
  method plus independent review of SuperSU side effects and recovery. Only
  after that finding may an exact owner approval be requested for fixed
  allowlisted reads for `jmcs` PID/start time, maps/smaps, FD links, and
  explicitly required socket tables. Do not read `/proc/<pid>/mem`,
  credentials, environment, or secrets.
- Record any SuperSU prompt, log, daemon, or other state side effect; do not
  claim target-write-free behavior unless evidence proves it.
- A denied read is not a capture and does not authorize another access method.

## Type111 and evidence limits

Existing bounded log analysis may return
`TYPE111_NOT_OBSERVED_IN_AVAILABLE_LOGS`. This describes only the captured log
source and window. It does not show the phone cannot send Type111, that Honda
cannot accept it, or that the protocol is unsupported. The separate PlayPort
Type110/Type111 lab is not Honda receiver evidence. `/info` advertisement,
Type111 negotiation, SETUP boundaries, session/stream identity, parent teardown,
and legitimate cryptographic authority remain separate questions. Do not
manufacture packet or credential evidence from logs, static addresses, or lab
fixtures.

## Stop conditions and restoration

Stop the affected phase on target mismatch, permission denial, command error,
timeout/output ceiling, identity change, unexpected warning, engine start,
READY state, display/audio/Navigation change, network or power anomaly,
controller exception, or evidence-integrity failure. Preserve already
collected private evidence. Do not retry, switch privilege, alter settings,
improvise another operation, or continue into an unapproved phase. Restore only
through an ordinary factory path already included in that phase's reviewed
plan; otherwise stop and ask the owner. Do not enter READY or power off the
vehicle remotely.

Restoration checks cover factory CarPlay, Navigation, center display, cluster,
audio, process identity, and approved host cleanup. Normal shutdown is not a
recovery method for a corrupted native executable. A backup alone is not
independent recovery proof. No warning may be induced for testing.

## Evidence and readiness states

- **ENGINEERING READY:** required offline implementation, synthetic tests,
  privacy review, and technical reviews pass for the exact source.
- **LIVE READY:** every phase has an exact fixed action list, necessary review,
  authorization, identity binding, operating conditions, recovery prerequisites,
  and a current owner approval. This task does not establish this state.
- **EVIDENCE COMPLETE:** every original objective has an actual observation or
  an explicit unresolved classification, blocker, and next action. Command
  success by itself is not evidence completeness.

Use only these observation statuses: `CONFIRMED`, `NOT_OBSERVED`,
`NOT_COLLECTED`, `PERMISSION_DENIED`, `UNSUPPORTED`,
`BLOCKED_PENDING_AUTHORIZATION`, `FAILED`, and `UNRESOLVED`. `NOT_OBSERVED`
is bounded to the named source and does not prove absence. Keep `safeForHonda()`
false. See [project status](../../PROJECT_STATE.md), [primary goal](../project/primary-goal.md),
and the [finish-line definition](../roadmap/finish-line-definition.md).

The comprehensive offline research design is in
[comprehensive-runtime-campaign.md](../diagnostics/comprehensive-runtime-campaign.md),
with a proposal-only phase profile in
[comprehensive-campaign-proposal.json](../diagnostics/comprehensive-campaign-proposal.json),
the full [evidence coverage matrix](../diagnostics/evidence-coverage.json), and
the [separate profile/source lock](../diagnostics/comprehensive-source-lock.json).
These files are not consumable by the historical C-P controller.
