# Vehicle testing and safety boundaries

ClarityLink is an offline-first research project. Vehicle work must have a separate, explicit scope and review; this guide does not authorize a test or provide instructions to bypass a safety mechanism.

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

## Private evidence

Keep raw captures, firmware extracts, identifiers, credentials, and personal data outside Git. Commit only purpose-limited, sanitized summaries after privacy review. Do not attach private raw data to public issues or pull requests.

The current authorization boundary and next action are in [NEXT_ACTION.md](../../NEXT_ACTION.md) and the [project status](../../PROJECT_STATE.md). The vehicle-test proposal form is [here](../../.github/ISSUE_TEMPLATE/vehicle-test-proposal.yml).
