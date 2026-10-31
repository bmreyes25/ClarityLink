# ClarityLink engineering workflow

Work in short cycles: **build → test → measure → learn → iterate**. Offline
engineering is the default; a car session always has a separate, explicit
scope and readiness check.

## Work freely offline

Codex may inspect archived evidence, develop tools and prototypes, run
synthetic/emulator tests, investigate failures, revise experiments, and publish
tested public-safe changes without asking again. Keep raw or derived Honda
evidence, identifiers, credentials, keys, firmware, and private captures out of
public Git. Preserve existing worktrees and unrelated changes.

For each experiment, state briefly:

`QUESTION → METHOD → OBSERVATION → CONCLUSION → NEXT ACTION`

Measure whether the method answers the question. Command or test counts alone
are not success. Do not repeat a campaign when its evidence source cannot
provide the missing datum.

## Three risk levels

- **Level 1 — Routine:** offline engineering, analysis of existing evidence,
  synthetic/emulator work, and an unchanged fixed diagnostic procedure. Live
  Level 1 still needs one current owner-approved session scope, exact target
  binding, and readiness confirmation. Do not repeat confirmation at every
  unchanged phase.
- **Level 2 — Controlled diagnostic:** new unprivileged commands, justified
  privileged metadata reads, or ordinary operation of an existing HondaHack
  UI. State expected evidence, side effects, stop conditions, and restoration;
  obtain proportionate technical review and one session-level owner approval.
  Group compatible actions under that approval. A new or materially different
  action needs new scope approval. Privilege must be justified from evidence;
  intended read-only data does not make `su` zero-write.
- **Level 3 — High risk:** receiver/runtime injection or patching, display
  ownership changes, firmware or persistent changes, and actions that could
  affect factory warnings or controls. Require suitable technical and safety
  review, exact owner approval, and independent recovery evidence. Do not
  trigger warnings, transmit CAN/control messages, or test while driving.

If a method is unjustified, block that method and continue independent offline
work. Do not turn an engineering uncertainty into a blanket project blocker.
Stop a live operation on a real hazard, identity mismatch, privilege surprise,
or behavior outside its approved scope.

## Vehicle session basics

Before live diagnostics, present the experiment name, question, exact actions,
expected data, known risks, stop conditions, and restoration route. Ask once:
**“Is the Honda ready for this experiment?”** The owner chooses YES, NOT YET,
or CANCEL. YES confirms stationary Park, parking brake, owner present, the
reviewed power state, no abnormal warnings, and normal factory displays. Use
only an already authorized endpoint and exact target identity. Do not scan,
select another device, retry by changing transport, escalate privilege, or
expand scope. Stop on abnormal vehicle behavior. Preserve raw evidence
privately; cleanup and notification must say whether ordinary power-off is
appropriate. Never automatically start another experiment.

`safeForHonda()` remains `false`; it is a deployment gate, not a veto on
authorized offline engineering or a properly approved diagnostic. Deployment
still requires its separate evidence and review.

## Verification and publication

Run focused tests while developing. Before a coherent public milestone, run
the relevant broader regression, privacy/security, source-integrity, and
repository checks. Do not weaken a test or claim a check ran when it did not.
Documentation-only work does not need the full suite unless a genuine
integrity dependency requires it.

Review the exact public diff and stage only its explicit files. Never publish
private or uncertain material, push directly to protected `main`, force-push,
or auto-merge safety-sensitive policy, receiver, authentication, warning,
vehicle-control, or `safeForHonda()` changes. Verify the published commit and
PR checks. Keep old campaign approvals and evidence immutable; they do not
authorize a new session.

Technical review should match risk and can cover one coherent change set.
Claude/ECC review is used when useful or required by the experiment; never
invent a review. AI review is not qualified vehicle-safety certification.
Use concise closeout: what we tried, what happened, what we learned, what
remains unknown, and the next experiment. Include commit/PR and relevant test
results without repeating audits that do not change the decision.
