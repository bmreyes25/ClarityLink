# ClarityLink agent instructions

These instructions apply to Codex, Claude, and other automated contributors in
this repository. They distinguish offline engineering permission from live
vehicle authorization.

## 1. Authorized offline engineering

Offline work needed to advance the primary goal is authorized without asking
the owner for a new permission each time. This includes:

- Analyze archived firmware, binaries, decompilations, and privately retained
  runtime evidence on the authorized Mac.
- Build host-side collectors, fixed-operation manifests, parsers, correlation
  tools, synthetic fixtures, and offline instrumentation prototypes.
- Design read-only privileged diagnostic candidates and assess existing
  SuperSU behavior from archived evidence. Design is not permission to invoke
  `su` on a vehicle.
- Examine binary callsites offline and prepare Type111 receiver experiments on
  synthetic or separately approved bench equipment.
- Analyze Display 1 ownership, Navigation lifecycle, and existing HondaHack
  behavior from retained evidence.
- Generate source/profile pins, add regression tests, run repository checks,
  obtain technical reviews, and publish public-safe tooling through protected
  pull requests.
- Write or revise campaign plans and evidence matrices. A plan is not live
  authorization.

Keep raw or derived vehicle evidence, identifiers, credentials, authentication
material, private blueprints, and firmware outside public Git. Commit only
sanitized, purpose-limited results after a privacy review.

## 2. Separate live diagnostic categories

Every live category requires a new exact-scope owner authorization and its own
review record. Authorization for one category does not authorize another.
Preparation may continue offline while a live gate is pending.

| Category | Offline preparation | Live gate and limit |
|---|---|---|
| Ordinary unprivileged ADB | Authorized | New exact-run owner approval, exact identity, existing ADB authorization, fixed argv, bounds, parked conditions, stop rules, private evidence, and restoration plan. No device scan or transport changes. |
| Stock iPhone/CarPlay transition | Authorized | Separate exact-run owner approval for each planned ordinary connect/disconnect transition and the phone state. No capture during transition, pairing/settings change, or protocol injection. |
| Existing privileged read | Authorized | Current evidence finds no justifiable zero-write privileged path. A separate exact approval is necessary but not sufficient: first obtain an independently reviewed access method and SuperSU side-effect/recovery assessment. No `su` invocation under the current finding. Never describe it as zero-write unless proven. No `adb root`, replacement root solution, or escalation fallback. |
| Factory Navigation observation | Authorized | New exact-run approval for ordinary owner-operated select/deselect transitions. No private controls, warning triggers, or evidence capture during transitions. |
| Existing HondaHack observation | Authorized | Separate HondaHack approval and exact ordinary UI action list, baseline, observer, stop conditions, and restoration plan. Require independent technical review and qualified vehicle-safety review because the casting observation involves factory Display 1. No install, Xposed changes, new hooks, or induced warnings. |
| Temporary runtime instrumentation | Authorized for design and synthetic/bench prototype | **Not authorized by the comprehensive diagnostic campaign.** Requires a separate exact proposal, compatibility and interruption assessment, technical/security review, owner approval, bounded cleanup, and independent recovery evidence. |
| Receiver or display modification | Authorized for offline research/prototype | Separate higher-risk proposal, qualified independent vehicle-safety review, legitimate protocol/security authority, verified independent recovery, exact owner approval, and protected deployment review. No deployment by default. |

The completed `CL-HONDA-RUNTIME-DIAGNOSTIC-EXECUTION` C-P session is a frozen,
historical, hash-bound baseline. It contained eight phases and 135 operations.
Do not extend, relabel, or reuse its consumed authorization, profile, source
pins, or manifest for the comprehensive follow-up.

## 3. Prohibited and higher-risk operations

- No driving during testing; no CAN/control-message transmission.
- Never interfere with, suppress, or deliberately trigger factory warnings.
- No unreviewed firmware, system, receiver, cluster, or display modification.
- No unapproved persistent software installation or startup change.
- No unreviewed debugger attachment, ptrace, process injection, or live code
  patching.
- No credential, authentication-secret, or protected process-memory
  extraction.
- No unauthorized privilege escalation, branch-protection bypass, or
  authorization-check bypass.
- Vehicle-related policy, receiver authentication/security, factory-warning,
  `safeForHonda()`, and deployment changes must not be auto-merged. Follow the
  protected-main review process.
- Publication and CI must never connect to or issue commands to the Honda.
- No vehicle operation under this engineering task. `safeForHonda()` remains
  `false`; `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remains in force.

## 4. Execution behavior

- An unavailable live-vehicle authorization must not prevent independently
  permitted offline engineering. Complete authorized implementation, testing,
  documentation, and publication, then name the exact live gate that remains.
- Continue after routine patch failures, test failures, races, and review
  findings. Diagnose causes, use smaller edits when broad patches fail, repair
  defects, and rerun affected checks.
- Avoid repeated audits that do not answer a new question. Preserve existing
  worktrees, unrelated changes, and private research.
- Ask the owner only for decisions that cannot be resolved from the repository
  or existing authorization. Do not treat a missing live permission as a
  reason to stop unrelated offline work.
- Never treat an unattempted objective as completed. Never equate command
  success with evidence success. Label `CONFIRMED`, `NOT_OBSERVED`,
  `NOT_COLLECTED`, `PERMISSION_DENIED`, `UNSUPPORTED`,
  `BLOCKED_PENDING_AUTHORIZATION`, `FAILED`, and `UNRESOLVED` accurately.
- Separate `ENGINEERING READY`, `LIVE READY`, and `EVIDENCE COMPLETE`. AI
  review is technical review, not qualified vehicle-safety certification.
- Do not weaken tests, safety gates, evidence requirements, or privacy controls
  to make a report pass.

## 5. Repository and publication workflow

- At task start, read this file, identify repository/worktree/branch/HEAD,
  fetch `origin`, record local and untracked changes, unpublished commits,
  related worktrees, and relevant GitHub protection. Preserve unrelated work.
- Execute ClarityLink work locally on the authorized Mac. `origin` must be
  `bmreyes25/ClarityLink`; use the configured `gh` credential helper and never
  put credentials in commands, files, or logs.
- Keep each development unit focused. Run its relevant checks, inspect every
  scoped file for privacy and public safety, and commit verified work before
  starting unrelated work. Do not claim verification for another tree or
  commit.
- For public-safe verified changes, use
  `tools/publish_checkpoint.sh` with an explicit task, branch, file list,
  message, and verification command. Never stage repository-wide or unknown
  files. Do not push directly to protected `main`, force-push, auto-merge
  vehicle-related policy changes, or remove existing worktrees.
- Check current rulesets, remote SHA, PR checks, CI, and CodeQL. A local commit
  is not publication. Never publish private vehicle evidence or a branch
  containing private material.
- Never invent or overstate Claude, ECC, independent technical, or qualified
  vehicle-safety reviews. If a reviewer is unavailable, report that fact and
  leave any required review gate open. AI review is not vehicle-safety
  certification.
- `tools/check_source_discovery.py` results require manual review. Never
  auto-add ignored files.
- Final reports give repository, branch, local/remote SHA, commit and PR links,
  tests, worktree state, unpushed/uncommitted counts, review/CI status, and
  blockers. Unknown values must be stated as unverified.

## 6. Primary goal and invariant

The goal is genuine iPhone-origin Type111 video on factory Display 1 while
factory Type110 CarPlay remains normal on Display 0 and all factory safety
behavior retains priority. Synthetic, third-party, static, and Honda evidence
are distinct and must not be conflated. Maintain:

`safeForHonda() == false`

`VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`
