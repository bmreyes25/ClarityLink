# Vehicle testing and safety boundaries

ClarityLink is an offline-first research project. The owner authorizes the offline activities below, including carefully scoped modification prototypes where technically needed for simultaneous secondary Type111 navigation. That authorization is not permission to install, connect to, or test on a Honda. `safeForHonda()` remains `false`.

## Activity levels

- **A — permitted offline:** factory APK/native-binary research; decompiled-code analysis; receiver architecture research; offline adapter and reversible modification prototypes; synthetic receiver/cluster simulation; Android API17 emulator tests; disconnect/recovery regression tests; and bench-only experiments on separately approved equipment.
- **B — offline prototype plus technical design review:** runtime hooks into factory receiver components; integrator delegate changes; display ownership/rendering changes; inter-process video delivery; in-memory receiver extensions; binary modification proposals; and custom receiver lifecycle handling. Apply safety and security review before any vehicle consideration.
- **C-P-MA-OWNER-ASSUMED-RISK — bounded passive diagnostics around owner-controlled factory transitions:** This prospective category becomes effective only after protected-main adoption. It allows only the fixed, read-only PR #118 eight-phase profile after required exact-source Codex and Claude AI engineering reviews, offline checks, and separate informed owner risk acceptance for the exact run. ECC review is recommended but optional when unavailable; record actual unavailability as `UNAVAILABLE` with a truthful reason and do not create a review artifact. If an ECC report is provided, bind it to the same commit, source and profile hashes and validate its recommendation and findings; any non-GO recommendation or unresolved critical/high finding blocks eligibility. AI review is not independent human safety certification or proof of safety. The profile includes only ordinary owner-guided CarPlay connect/disconnect and factory Navigation select/deselect/reselect transitions; those transitions temporarily change active factory infotainment state. Scope is limited to the hash-pinned profile and exact command manifest, exact target identity and serial, existing ADB authorization, unprivileged shell, stationary Park, parking brake set, owner present, normal factory operation, and private host-only evidence. Use ON mode with the brake pedal not pressed and READY absent. The [2018 Honda Clarity PHEV owner's manual](https://techinfo.honda.com/rjanisis/pubs/OM/AH/ATRW1818OM/enu/ATRW1818OM.PDF) describes automatic engine start/stop during vehicle operation and defines READY as indicating the vehicle is ready to drive. Excluding READY is the conservative procedure choice; EV-only expectations do not establish that the engine cannot start. Whether the head unit and existing ADB transport operate in ON mode is unverified; if unavailable, stop without escalation. Each command is bounded (at most 20 seconds and 4 MiB output); the fixed manifest's aggregate timeout/output ceilings remain pinned in the profile. The host campaign has a 60-minute total elapsed-time ceiling and five-minute owner-prompt idle timeout; these are software bounds and do not establish that ON operation for that duration is safe or prevent 12 V battery depletion. No collection runs during owner-operated factory transitions or waits. Before and after each collection phase, reconfirm Park, READY absent, no unexpected warning, and visibly normal center display and cluster. The controller does not stop or inspect a shared host ADB server or prove that remote child work ceased. Stop on any unexpected identity, permission, output, connectivity, power, display, process, warning, or factory behavior; do not retry, broaden scope, or change configuration. No debug setting changes, privilege escalation, installation, process attachment/modification, firmware/CAN/display changes, warning interference, or driving tests are allowed. This category does not establish OEM authorization or prove safety, and `safeForHonda()` remains `false`.
- **C — separate explicit owner authorization and qualified vehicle-safety review required:** Honda installation outside C-P; factory software replacement; persistent head-unit changes; instrument-cluster modifications; vehicle-side display experiments; connected-iPhone integration beyond the exact C-P sequence; or any operation that could alter factory display behavior. If review identifies uncertainty about power-state effects, diagnostic load, display interference, target-side changes, or recovery, the work remains Level C until those risks are resolved and reviewed.
- **D — prohibited:** CAN/control-message experiments; suppressing/intercepting safety warnings; braking, steering, airbag, or safety-critical ECU changes; unreviewed cluster firmware flashing; unrecoverable writes; authentication-secret extraction/disclosure; testing while driving; automatic deployment; or bypassing review/safety gates.

Levels A/B do not grant Level C/D permission. C-P-MA-OWNER-ASSUMED-RISK is a narrow, owner-assumed-risk category, not standing permission; it becomes usable only when adopted and its exact-source, owner and execution gates pass. It does not require an external human review, but it must never be described as human safety certification. Missing OEM authorization remains missing; private technical reachability is not OEM endorsement. Privileged reads, HondaHack observations, active instrumentation, display/firmware changes, and deployment remain outside this category and require their own review and authorization.

## Disconnect invariant and acceptance criteria

Required design target: `CARPLAY_DISCONNECTED => FACTORY_BEHAVIOR_ONLY`. It has not been demonstrated as a whole. Define and measure acceptance against a captured synthetic baseline and run each applicable disconnect/failure case through repeated cycles. After disconnect, verify:

1. No secondary navigation content or stale decoded frames remain.
2. No project-owned display views remain attached.
3. No audio routing, session, or ownership state remains attributable to ClarityLink.
4. Factory Navigation returns to its baseline behavior without ClarityLink interference.
5. Cluster controls remain responsive and unblocked.
6. Factory warning displays retain priority and are never suppressed or intercepted.
7. No ClarityLink UI or persistent display state remains.
8. Factory receiver behavior remains at baseline after disconnect.
9. With no iPhone connected, boot and normal factory operation do not depend on ClarityLink.
10. During connected operation, Display 0, audio, calls, Siri, and primary CarPlay functions remain at baseline; Display 1 carries navigation only in the appropriate factory Navigation context, subject to warning priority.

Exercise USB disconnection, unexpected iPhone disconnect, Type111 stream termination, CarPlay authentication failure, receiver-process crash, decoder crash, display-host restart, startup without an iPhone, normal power cycle, repeated connect/disconnect cycles, and incomplete initialization. Each case must reach the ten postconditions above within a declared cleanup bound, with zero residual project-owned frames/views/sessions and a recorded before/after baseline comparison. Missing or unobservable evidence is a failure or unresolved result, not a pass.

These checks require explicit observable signals, bounded cleanup times, zero residual project-owned frames/views/sessions, and baseline comparison. A clean disconnect case is not proof for untested failures or target behavior. Existing `tests/integration/test_synthetic_type111_replay.py` checks a synthetic Type111 teardown, mock renderer release, and Type110/audio preservation; it does not establish the full disconnect invariant or Honda behavior. Add offline regression coverage only where the existing simulation can represent a condition without inventing Honda behavior.

## Reversibility contract

Before any vehicle deployment proposal, identify exact original firmware/component versions and SHA-256 fingerprints; produce complete verified backups; demonstrate restoration using a recovery mechanism independent of the modified component; define containment, compatibility, abort conditions, and post-restore verification; and test rollback on non-vehicle equipment. A backup alone is not recoverability. Require independent safety review before vehicle deployment. If a path modifies safety-critical cluster firmware without a verified independent recovery mechanism, it is blocked for vehicle deployment.

## Evidence and authorization gate

- Prefer static analysis and synthetic host tests. Label evidence by source and scope.
- Before any live observation, specify the exact question, prerequisites, commands/actions, expected result, time/output limits, stop conditions, evidence handling, and recovery path in a reviewed milestone.
- A previous approval applies only to its exact procedure and boundary. A failed or ambiguous preflight is a stop, not permission to improvise or retry.
- Vehicle work is parked-only. Follow the owner's operating guidance and stop if the vehicle or stock behavior is abnormal.

## Non-negotiable scope

- No CAN writes or vehicle-control commands.
- No safety-system changes or interference with cluster warnings, gauges, or unrelated stock UI.
- No block-device writes, firmware replacement, or system/data partition changes.
- No startup persistence unless a separate milestone reviews and authorizes it.
- Preserve the factory Type110 path and center display; a project-owned secondary path must fail closed and clean up only its own resources.
- Any modifying work needs an exact rollback plan and an independent restoration check. A modeled rollback is not vehicle restoration evidence.
- No vehicle installation or experiment is authorized merely by this document. The fixed C-P profile uses the prospective multi-agent owner-assumed-risk path only after adoption, exact-source Codex and Claude reports, truthful ECC status (with a report validated if supplied), and separate exact owner authorization; other Level C work requires qualified vehicle-safety review and separate exact owner approval.

## Private evidence

Keep raw captures, firmware extracts, identifiers, credentials, and personal data outside Git. Commit only purpose-limited, sanitized summaries after privacy review. Do not attach private raw data to public issues or pull requests.

The current authorization boundary and next action are in [NEXT_ACTION.md](../../NEXT_ACTION.md) and the [project status](../../PROJECT_STATE.md). The vehicle-test proposal form is [here](../../.github/ISSUE_TEMPLATE/vehicle-test-proposal.yml).
