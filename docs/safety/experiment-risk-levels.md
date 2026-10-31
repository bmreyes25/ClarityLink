# ClarityLink experiment workflow

Use the lowest-risk method that can answer a named engineering question. A
session-level approval covers the reviewed actions as a group; unchanged
phases do not need duplicate approvals. Approval does not prove feasibility or
restoration.

| Level | Examples | Before a live session |
|---|---|---|
| **1 — Routine** | Previously reviewed fixed diagnostics; ordinary ADB reads; offline and synthetic work | Current owner-approved session scope, exact target/endpoint, readiness check, fixed actions, private evidence, and stop/recovery plan |
| **2 — Controlled diagnostic** | New unprivileged reads, justified privileged metadata reads, ordinary HondaHack Start/Stop UI observation, including its normal resulting display transition | Exact question and output, brief method-specific risk note, technical review proportionate to side effects, one session-level owner approval, target binding, stop/recovery plan; qualified review is still required for this Display 1 observation |
| **3 — High risk** | Receiver patch/injection, experimental Display 1 ownership reassignment outside existing feature behavior, firmware or persistent changes, warning/control impact | Separate technical and qualified safety review as appropriate, explicit owner approval for the exact change, and independent recovery evidence |

Privileged access is a method to evaluate, not blanket permission. Record
what the exact implementation may log, write, prompt, start, or change. The
read target does not make an invocation read-only. If effects are unresolved,
investigate offline or select another method; do not execute it to discover its
side effects.

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
- No arbitrary shell or privilege escalation. No unreviewed attachment,
  injection, receiver/display change, or persistent installation.
- Stop immediately on an abnormal warning, engine/READY change, unexpected
  process or factory display/audio behavior, identity mismatch, or uncertain
  restoration.
- High-risk changes require independent recovery evidence. Owner acceptance
  does not create recovery capability or establish technical feasibility.
- Maintain `safeForHonda() == false` until separate deployment requirements
  pass. A diagnostic session does not enable deployment.

Historical C-P and other campaign approval packets remain valid only for their
original scope and are not templates for repetitive approval of ordinary new
engineering. See [vehicle-testing.md](vehicle-testing.md) for project-specific
limits and the [Type111 evidence priorities](../diagnostics/comprehensive-runtime-campaign.md).
