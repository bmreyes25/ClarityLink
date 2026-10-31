# Comprehensive Honda runtime evidence campaign

**Campaign:** `CL-HONDA-RUNTIME-EVIDENCE-FOLLOWUP-20261031`
**Requirements baseline:** `CL-HONDA-RUNTIME-EVIDENCE-20261030`
**Vehicle target:** 2018 Honda Clarity PHEV Touring, MY16ADA
**Engineering state:** ENGINEERING READY (offline only)
**Live state:** NOT AUTHORIZED
**Evidence state:** INCOMPLETE — 19/19 objectives classified; campaign success remains false
**Safety state:** `safeForHonda() == false`; `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`

This is a comprehensive research design. It does not authorize a new vehicle,
ADB, iPhone, HondaHack, privileged, instrumentation, or receiver-modification
operation. The completed C-P campaign remains a separate, historical,
hash-bound baseline and is not repeated or extended here.

## Objective and baseline reconciliation

The project goal remains genuine iPhone-origin Type111 secondary CarPlay video
on factory Display 1 while normal Type110 CarPlay remains on Display 0, with
factory safety and warning behavior retained. A successful command is not a
successful evidence objective. The machine-readable row for each objective is
in [evidence-coverage.json](evidence-coverage.json); its checker refuses an
empty or unclassified objective and does not equate `NOT_OBSERVED` with proof
of absence.

The original requirements are reconciled with existing evidence as follows:

| Original question | Current evidence and limit | Campaign objective |
|---|---|---|
| Ordinary ADB and privilege state | Historical private C-P material was reviewed offline. Its target-specific details are retained outside public Git and do not establish current access or authorization. | Revalidate only under a new exact-run approval; retain process start-time checks. |
| Existing root/SuperSU | Archived project research was reviewed. Current access method and side effects are not approved by this proposal. | Offline assessment first. No `su` invocation unless new evidence and independent review establish a justified method; owner approval alone is insufficient. |
| `jmcs` identity and memory map | Historical private process observations were reviewed; target-specific values remain private. | Bind any future map/FD observation to PID plus start time; never read process memory. |
| Native loader, libraries, executable pages | Static project research and private runtime evidence are separate evidence classes; no runtime claim is published here. | Parse actual maps only if a separately accepted access method exists; keep static and runtime claims distinct. |
| `jmcs` descriptor/socket ownership | Historical network and receiver research does not establish process-owned sockets. Detailed private observations are not published. | Join exact FD symlink inode to same-phase socket-table inode. Timing alone is not ownership. |
| CarPlay `/info` and SETUP | Prior campaign material did not fulfill the follow-up's runtime negotiation evidence objective. Exact private log results remain outside Git. | Do not repeat unchanged passive logging; identify the precise source and boundary before proposing another capture. |
| Type110/Type111 lifecycle | Prior campaign material does not establish genuine Honda Type111 negotiation or session authority. Non-Honda lab evidence is kept distinct. | Keep UI lifecycle, logs, protocol exchange, stream identity, and cryptographic authority as separate evidence. |
| Display 1 and Navigation | A private phase-by-phase comparison was completed offline; its derived vehicle observations remain in owner-private storage. | Use the reviewed comparator on future authorized evidence; do not infer physical pixel contribution or OEM frame admission. |
| HondaHack | Project research was reviewed, but this task and the historical C-P session did not perform a HondaHack observation. | Retain a separate, independently gated ordinary UI observation phase. |
| Recovery and instrumentation | Prior restoration and recovery evidence were reviewed offline. Detailed vehicle-derived observations remain private; native receiver recovery remains a separate requirement. | Prove ordinary restoration separately from native-code recovery; rank instrumentation by least risk. |

The original source set and relevant records include `AGENTS.md`,
`docs/safety/vehicle-testing.md`, `docs/project/primary-goal.md`,
`docs/roadmap/finish-line-definition.md`, Steps 40E, 40E3, 40E4, 43T0-D4,
43P, 43S and PR #117, CL-HH-02 through CL-HH-06, CL-R10B, CL-DISP-02,
`research/plans/DEEP_DIAGNOSTICS_BLUEPRINT.md`, and the private October 31
C-P summary. PR #117 is still an offline modification experiment; its API17
check was failing at the time of inspection, and it is not receiver execution
evidence.

The owner-private report retains the phase-by-phase DisplayManager,
WindowManager, and SurfaceFlinger delta table and its limitations. It is not
copied into this public repository because it is derived private Honda
evidence. The public comparator only describes its parsing contract and does
not include any capture-specific result.

## Full staged design

All eight phases remain in the requirements whether or not a live gate passes.
No phase is silently removed. The future controller must use exact target
identity (PID, start-time ticks, and resolved `/proc/PID/exe` path), direct argv
vectors, fixed paths, per-command output/time ceilings, private host-only files,
SHA-256 inventories, process start-time revalidation, no
automatic retry, and immediate abort on unexpected behavior. The C-P command
manifest and source/profile pins are not inherited.

### Phase 0 — baseline safety and identity

Owner confirms the car is stationary in a safe outdoor location, Park, parking
brake engaged, the exact reviewed power state, READY absent, engine not
running, no warning or abnormal behavior, normal center display/cluster/audio/
Navigation, owner physically present, and known ordinary shutdown/recovery
route. Verify retained backups and hashes offline. Record phone and debugging
state without changing either. No ADB command runs in this phase.

**Stop:** any abnormal baseline, identity uncertainty, warning, unexpected
power state, or missing recovery precondition. Record `PHASE0_BASELINE_VERIFIED`
only if every baseline check is explicitly confirmed.

### Phase 1 — ordinary ADB capability

After a new exact-run approval, use only one owner-approved existing ADB
endpoint; no scan, serial auto-selection, network probing, `adb root`, TCP
enablement, or endpoint fallback. Fixed read set:

- `id` and `ps`;
- selected properties only: Android release/SDK, product device/board,
  hardware, `ro.secure`, and `ro.debuggable`;
- verified receiver `stat`, `cmdline`, `status`, and fixed `ls -l
  /proc/PID/exe` symlink inspection to bind PID to start time and executable
  path using the existing API 17-compatible toolbox operation;
- the reviewed bounded `dumpsys display`, `dumpsys SurfaceFlinger`, and
  `dumpsys window` operations when present in the new exact manifest.

The old C-P profile proves neither the exact action list nor authorization for
this follow-up. API 17 support for every selected utility must be established
from prior evidence or the first approved fixed call; unsupported output is a
stop, not a substitution.

**Stop:** unexpected target/build/process identity, permission, transport,
timeout, malformed output, warning, or factory behavior. Record privilege
status as observed, not inferred from `su` file presence.

### Phase 2 — existing root capability review

Offline, inspect the archived binary fingerprint, mode/owner provenance,
SuperSU version/behavior, historical prompts/logs, daemon effects, and
recovery records. Do not install or configure a root solution. Do not invoke
`su` in this task.

No live `su` command is proposed under the current evidence decision. A future
separate proposal may be written only after new offline evidence and an
independent technical review establish a justified access method and assess
SuperSU prompts, possible log/daemon writes, and recovery. Owner approval alone
is insufficient. The existing `privileged.py` command builder is not evidence
that `su` is safe or approved. A successful prior `su -c` does not prove
harmlessness. No claim of zero target writes is permitted without direct
evidence.

**No automatic fallback:** no `adb root`, debug property change, alternate
daemon, replacement root tool, or setting change. If no acceptable method is
approved, Phase 3 remains `BLOCKED_PENDING_AUTHORIZATION` or
`PERMISSION_DENIED`; independent offline work continues.

### Phase 3 — `jmcs` maps and socket ownership

Prerequisites: exact process identity and start time; independent approval for
the access method; reviewed fixed path allowlist; no process attachment or
memory read. A proposed minimally scoped read set, only if approved, is:

- `/proc/<verified-pid>/stat`, `cmdline`, `status`, `maps`, and `smaps`;
- `/proc/<verified-pid>/fd` symlink targets for numeric FDs;
- `/proc/net/tcp`, `tcp6`, `udp`, `udp6`, and `unix` tables required for inode
  joins. These procfs items remain blocked unless Phase 2 access criteria pass.

Revalidate PID plus start time after capture. Report maps availability,
executable mappings, page size evidence, `r/w/x` protections, path/library
inventory, load bias and callsite translations independently. Report FD
ownership only for exact same-phase inode matches. No `/proc/<pid>/mem`,
environment, credential, key, or signal operation. No `ptrace`, stopping,
killing, attach, or code modification.

**Independent result fields:** `JMCS_RUNTIME_MAP_CAPTURED`,
`JMCS_LOAD_BIAS_CONFIRMED`, and `JMCS_SOCKET_OWNER_CONFIRMED`; each can instead
be `PERMISSION_DENIED`, `NOT_COLLECTED`, or `UNRESOLVED`. Do not collapse them
into a single success bit.

### Phase 4 — three-state CarPlay observation with one reconnect cycle

Under separate new ordinary ADB and stock iPhone/CarPlay transition approvals,
record: disconnected baseline; ordinary owner-operated iPhone connection with
stock CarPlay active; ordinary disconnect; reconnect; and final disconnect.
No command or evidence capture during transition/wait. At each steady state,
bracket capture with the same PID/start-time, cmdline, UID/GID, and
`/proc/PID/exe` checks against `/system/bin/jmcs`. Capture only the reviewed
existing log markers, display data, `/proc/net/{tcp,tcp6,udp,udp6,unix}`, and
`/sys/class/net/usb0/operstate`. These ordinary reads support a timestamped
phase comparison; they do not establish `jmcs` socket ownership, which remains
in the separate blocked Phase 3 objective. A bounded `logcat -d -t 500`
snapshot is taken only at each steady-state boundary to compare lifecycle
deltas, not to repeat a marker search. Raw output remains private. Do not
expect logs to contain full plist values; missing `/info` or SETUP markers
remains `NOT_OBSERVED` for that source and is not evidence of Type111 support
or absence.

Record ordinary Type110 visual lifecycle separately from any `/info`, SETUP,
Type111, socket, or cryptographic fact. The separate PlayPort result is a
comparison source, never Honda evidence. The stock Honda receiver's lack of a
known secondary advertisement may mean no Type111 request is triggered at all.

**Stop:** factory CarPlay, audio, calls, display, warning, or identity behaves
unexpectedly; no retry or alternate transport.

### Phase 5 — factory Display 1 ownership and Navigation lifecycle

With its own approved ordinary Navigation transition scope, capture bounded
DisplayManager, WindowManager, and SurfaceFlinger snapshots in the following
states: factory Navigation selected, deselected, then reselected. A phase
controller records host monotonic markers; the owner performs the ordinary UI
transition; capture begins only after owner confirmation. Revalidate the
verified `jmcs` PID/start-time, `/system/bin/jmcs` cmdline, root UID/GID, and
executable symlink immediately before and after each state capture. Compare
stable
device inventory and WindowManager display-section window names for a reviewed
Android display ID mapped to factory Display 1. If that mapping is unavailable
or the ID is absent in any phase, the comparator reports incomplete. Compare
normalized SurfaceFlinger layer names. Preserve anonymous-layer counts
without inventing an owner. Record physical observer evidence separately from
Android metadata.

**Interpretation limit:** matching phase names or timing is not causal proof.
Even a WindowManager Display 1 assignment and similarly named SurfaceFlinger
layer do not establish exact physical aperture, frame contribution, warning
priority, or a supported Honda frame-admission contract.

### Phase 6 — existing HondaHack casting and withdrawal

This phase stays in the full plan but is **separately gated**. Only if the
existing HondaHack state is already present and a new exact HondaHack approval,
independent technical review, and qualified vehicle-safety review pass because
casting involves factory Display 1: casting off → ordinary Start Casting → ordinary Navigation deselect
→ Navigation reselect → ordinary Stop Casting → stock baseline check. No
installation, Xposed module or hook change, private control API, warning
induction, or forced process action. Keep an observer and stop if factory
warning, cluster, audio, display, or Navigation behavior changes.
Require ordinary unprivileged ADB, factory Navigation, and HondaHack approvals
for their respective actions. Revalidate the verified `jmcs` PID/start-time,
`/system/bin/jmcs` cmdline, root UID/GID, and executable symlink before and
after each stable-state capture.

If ordinary Stop Casting is unavailable or restoration is uncertain, stop the
campaign and follow only the reviewed safe factory restoration route. The
previous Door Open warning preemption is not permission to induce another
warning and does not establish all-warning priority.

### Phase 7 — recovery and restoration

Verify ordinary iPhone disconnect, stock CarPlay behavior, factory Navigation,
center display, cluster, audio, expected process state, host ADB client exit,
approved cleanup, evidence hashes/permissions, and baseline restoration. Do
not stop or inspect a shared host ADB server if the approved procedure says it
may be shared. Report that uncertainty. No vehicle power-off action is
automated.

Phase 7 vehicle reads are only part of the normally completed exact campaign.
After any live abort, cleanup is host-only; no further ADB/vehicle command is
issued unless a new exact recovery action has independent review and owner
authorization.

Normal shutdown/restoration evidence is not recovery proof for corrupted
receiver code. A future modification phase needs exact original version/hash,
complete backup, independent recovery on non-vehicle equipment, qualified
review, and exact approval before it can become live-ready.

### Post-session — instrumentation decision, not execution

After evidence is saved, review offline and classify each missing datum. Do
not activate instrumentation automatically. Rank methods as follows:

| Method | Target change / privilege | Evidence value | Risk and decision |
|---|---|---|---|
| A. Existing logs and system diagnostics | No planned target change; ordinary ADB gate | Low-to-moderate for lifecycle markers; cannot guarantee plist/payload or absent-trigger visibility | Lowest risk. Use only for a named, bounded observation; do not repeat unchanged passive logs. |
| B. Archived binary/static analysis | None | High for exact stock branches and static boundaries; cannot establish runtime values or mapped address | Continue offline. Step 43S addresses remain static VAs until proven against actual mappings. |
| C. Existing privileged read | `su` may prompt, log, or affect daemon state | High for PID-bound maps, libraries, protections, FD/socket identity; low for protocol payloads | Medium-to-high access uncertainty. Requires separate SuperSU side-effect and approval review; no zero-write claim. |
| D. Synthetic/bench observer or helper | Bench code only; no Honda target | Medium for proving parser, event schema, and instrumentation compatibility; not Honda behavior | Preferred next instrumentation work. Fixed signal, no credentials, no vehicle interface. |
| E. Temporary on-target helper | Installs/runs target code; may need privilege | Potentially high for selected diagnostics but not automatically for private protocol buffers | High. No live use under this campaign; separate compatibility, cleanup, and recovery review required. |
| F. Dynamic instrumentation (ptrace/Frida/Xposed hook) | Attach/injection or hook changes; likely privilege | Potentially highest for `/info`, SETUP and teardown values | Very high crash, deadlock, receiver suspension, Type110 impact, and Android 4.2/ARMv7 compatibility risk. Research only until proven on matched offline target. |
| G. Receiver binary modification | Code/loader change | May expose exact branch values or enable a controlled experiment | Highest. PR #117 is stock pass-through offline only; no active patch without qualified review and independent recovery. |

Protocol questions that need exact answers include: `/info` secondary-display
advertisement, Type111 trigger, SETUP request/response boundary and values,
stream/session identities, parent/child teardown, Type110 coexistence, and
legitimate session/cryptographic authority. Do not extract secrets. Existing
lab Type111 keys or credentials are not Honda authority.

Private Step 43S research identifies a static `/info` response-construction
site and a stock branch that skips unsupported Type111. Exact binary
locations remain outside public Git; any static address is not a runtime
address until ELF load bias is established from an actual mapping. The current missing observations are the runtime
`/info` advertisement value, whether the phone sends a Type111 request, exact
SETUP request/response boundary and values, negotiated session/stream identity,
parent teardown behavior, Type110 continuity under any Type111 session, and
legitimate session authority. Static analysis can locate control-flow sites;
existing logs can only report markers present in their bounded window; a
privileged maps read could bind a mapping but cannot reveal packet values; a
synthetic/bench observer can validate a future event parser but cannot prove
Honda behavior. Dynamic receiver observation remains a distinct high-risk
future proposal.

## Failure handling and exact stop behavior

On any unexpected result, stop the affected live phase immediately, preserve
permitted partial evidence, do not retry or escalate, and ask the owner before
any new active action. Report phase, action, expected/actual outcome, factory
behavior risk, evidence retained, cleanup result, safe-power guidance, and
possible decisions. A permission denial, unsupported utility, or missing
marker remains a classified blocker, not proof that the component is absent.

## Approval and review state

- Codex engineering checks: complete on the exact locked source and profile;
  the comprehensive profile remains proposal-only with no live controller.
- Claude independent technical review: final review of the corrected evidence
  category map and authorization gate returned no actionable findings. Earlier
  findings were resolved and covered by regression tests. The review did not
  provide vehicle-safety certification.
- Offline suite: 2,367 passed, 29 skipped, 41 subtests; self-locator and
  simulator checks passed. The publisher will rerun the complete suite on the
  final publication tree.
- API 17 scope: the repository's API 17 command/parser compatibility tests ran
  in that suite. No Android target source changed, so no API 17 APK build or
  emulator runtime was applicable to these host-side tools.
- ECC: `UNAVAILABLE`; no ECC review was performed and none is claimed.
- Qualified independent vehicle-safety review: not performed; still required
  before HondaHack/Display 1 observation or any modification/live action that
  could affect factory display or warning behavior.
- Owner: new exact authorization for each live category and every live phase
  that the owner elects to include. The prior C-P authorization is consumed and
  applies only to its historical pinned run.

## Readiness and milestone reporting

This campaign supplements the existing CL-R5/CL-R6 roadmap; it does not
replace or redefine either milestone. The canonical milestone record retains
CL-R5 as in progress and tracks this campaign as offline-ready, with live work
blocked. Evidence classification is structurally complete, but the campaign
is not evidence-complete: required observations remain uncollected or
unresolved with a blocker and next action. It is not live-ready until every
selected phase has its own current approval and recovery conditions.
