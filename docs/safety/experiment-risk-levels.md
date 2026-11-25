# ClarityLink experiment workflow

Use the lowest-risk method that can answer a named engineering question. A
session-level approval covers the reviewed actions as a group; unchanged
phases do not need duplicate approvals. Approval does not prove feasibility or
restoration.

## Policy version CL-HONDA-DIAGNOSTICS-V2

This policy separates three authorization classes. Routine offline engineering
(source review, synthetic tests, emulators, and host-only prototypes) needs no
vehicle approval and remains available while `safeForHonda() == false`.
Owner-approved controlled diagnostics use one exact, bounded parked session
approval with technical checks proportionate to the method. The versioned
`CL-HONDA-ROOT-ACCESS-V2` profile is the only proposed legacy-SuperSU route.
High-risk vehicle changes, including native injection, receiver modification,
display ownership changes, firmware changes, and any possible factory-warning
interference, retain separate safety, technical, and recovery requirements.
`safeForHonda() == false` blocks deployment; it does not block offline work or
a properly approved controlled diagnostic.

| Level | Examples | Before a live session |
|---|---|---|
| **1 — Routine** | Previously reviewed fixed diagnostics; ordinary ADB reads; offline and synthetic work | Current owner-approved session scope, exact target/endpoint, readiness check, fixed actions, private evidence, and stop/recovery plan |
| **2 — Controlled diagnostic** | New unprivileged reads, justified privileged metadata reads, ordinary HondaHack Start/Stop UI observation, including its normal resulting display transition | Exact question and output, brief method-specific risk note, technical review proportionate to side effects, one session-level owner approval, target binding, stop/recovery plan; qualified review is still required for this Display 1 observation |
| **3 — High risk** | Receiver patch/injection, experimental Display 1 ownership reassignment outside existing feature behavior, firmware or persistent changes, warning/control impact | Separate technical and qualified safety review as appropriate, explicit owner approval for the exact change, and independent recovery evidence |

Privileged access is a method to evaluate, not blanket permission. Record
what the exact implementation may log, write, prompt, start, or change. The
read target does not make an invocation read-only. A Level 2 privileged
diagnostic can proceed when a fixed runner has checked the exact executable,
owner, path, symlink chain, mount and effective unprivileged writeability; the
owner explicitly accepts the named residual effects for one bounded session;
and current target and source pins match. A hash alone never establishes
immutability. If the executable is writable or replaceable by an unprivileged
actor, the mount/path view is ambiguous, or the owner has not accepted possible
privilege-daemon, policy, request, logging or persistent-write effects, refuse
that privileged method and continue independent work.

## One session

1. **Select:** state the experiment, concrete question, exact permitted
   actions, expected data, known risks, stop conditions, and restoration route.
2. **Ready:** ask once, “Is the Honda ready for this experiment?” Choices are
   YES, NOT YET, and CANCEL. YES confirms stationary Park, parking brake,
   owner present, approved power state, normal factory displays, and no
   abnormal warning.
3. **Authorize:** record the selected scope, exact vehicle/target and existing
   endpoint, owner decision, expiry, and a fresh one-use run ID/nonce. Lower
   levels do not authorize higher-level work. A material scope change needs a
   new decision.
4. **Run:** execute only the reviewed fixed actions. Stop on identity mismatch,
   unexpected privilege or persistence, command failure, or abnormal vehicle
   behavior. Do not retry or escalate automatically.
5. **Finish:** perform only the approved cleanup/restoration. Report whether
   normal power-off is appropriate. Notify the owner; do not start the next
   session automatically.
6. **Learn:** analyze evidence offline and record
   `QUESTION → METHOD → OBSERVATION → CONCLUSION → NEXT ACTION`.

Raw and derived Honda evidence stays in an owner-only location outside Git.
Record its integrity and evidence quality, not sensitive content in the public
report.

## Non-negotiable boundaries

- No driving tests, CAN/control transmission, deliberate warning interference,
  or vehicle-control changes.
- No arbitrary shell, privilege fallback, device scan or escalation. A reviewed
  fixed-operation `su -c` profile is allowed only under its exact session
  authorization and legacy-binary integrity checks. No unreviewed attachment,
  injection, receiver/display change, or persistent installation.
- Stop immediately on an abnormal warning, loss of the exact power state bound
  to the session, unexpected engine/exhaust behavior, unexpected process or
  factory display/audio behavior, identity mismatch, or uncertain restoration.
- For the comprehensive Honda capture, the approved state is stationary in
  Park with the parking brake set and power system ON with READY active. READY
  means the vehicle is capable of movement; do not shift or release the
  parking brake. Keep the vehicle outdoors. For this narrowly scoped,
  owner-operated, ordinary-read READY-active campaign, the owner's documented
  self-assessment and explicit one-session responsibility acknowledgment
  replace a separate qualified human vehicle-safety review. This is not
  independent certification and does not remove physical readiness checks,
  abnormal-warning/engine/exhaust stop conditions, normal-control restoration,
  or the qualified-review requirements that apply to other campaigns and
  privileged or higher-risk testing. Historical assessment dates do not expire
  solely because of age, but the assessment must still bind to the exact current
  source commit and source pins; future dates are rejected.
- High-risk changes require independent recovery evidence. Owner acceptance
  does not create recovery capability or establish technical feasibility.
- Maintain `safeForHonda() == false` until separate deployment requirements
  pass. A diagnostic session does not enable deployment.

Historical C-P and other campaign approval packets remain valid only for their
original scope and are not templates for repetitive approval of ordinary new
engineering. See [vehicle-testing.md](vehicle-testing.md) for project-specific
limits and the [Type111 evidence priorities](../diagnostics/comprehensive-runtime-campaign.md).
