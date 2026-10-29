# Where to look: documentation map and status vocabulary

This page is the entrypoint to project status. It is deliberately short and holds no volatile numbers: PR heads, check results and counts change daily and must be read live (`gh pr list`, `gh pr checks <n>`, `tools/verify_remote_publication.py`).

## Which document is authoritative

| Question | Read | Nature |
|---|---|---|
| What is true now, and what is blocked? | [`current.md`](current.md), [`blockers.md`](blockers.md), [`milestones.json`](milestones.json) | Canonical status, edited only by the maintenance workflow |
| What may agents do, and how is work published? | [`AGENTS.md`](../../AGENTS.md) (the task-prompt checklist lives under `docs/development/` once published) | Single authoritative contract (Claude Code and Codex) |
| What is the plan and what counts as finished? | [`docs/roadmap/`](../roadmap/claritylink-master-plan.md), [`finish-line-definition.md`](../roadmap/finish-line-definition.md), [`milestone-acceptance-gates.md`](../roadmap/milestone-acceptance-gates.md) | Versioned plan and gates |
| What is safe to publish? | [`public-private-evidence-boundary.md`](../security/public-private-evidence-boundary.md), [`vehicle-safety-gates.md`](../security/vehicle-safety-gates.md) | Safety boundaries |
| What did a campaign establish? | `step-reports/`, `research/`, `docs/development/` | Dated evidence; each document says what class of evidence it holds |

These top-level files are **historical logs**, kept for provenance, not current status: `PROJECT_STATE.md`, `ROADMAP.md`, `NEXT_ACTION.md`, `EVIDENCE_INDEX.md`. They are large because they accumulate; do not read them to learn the present state, and do not delete them to shorten the repository.

## Status vocabulary

Use these words, and keep the classes apart. One passing class never promotes another.

| Status | Means | Does not mean |
|---|---|---|
| Merged and verified | On `main`, checks passed on the merge result | Reviewed by an independent human unless a review is named |
| Published, unmerged | On a branch with an open PR | Accepted |
| Synthetic lab PASS | Offline or host-side models and fixtures behave as specified | Behaviour of any real receiver, phone or vehicle |
| API17 runtime PASS | Executed on an Android 4.2.2 emulator | Honda hardware or Honda software behaviour |
| Performance FAIL / PASS | The unchanged CL-R12 gate's verdict on a named run | Anything about a different workload or environment |
| Honda receiver interface unresolved | No supported extension boundary or Type111 facts are established (`RECEIVER_AUTHORIZED_SPEC_REQUIRED`) | Offline custom receiver research is now permitted; OEM authorization and vehicle deployment remain unapproved |
| Honda display interface unresolved | No authorized frame-admission path found (`DISPLAY_SUPPORTED_PATH_NOT_FOUND`) | Offline host-owned rendering research is now permitted; vehicle deployment remains unapproved |
| Vehicle deployment NOT AUTHORIZED | No vehicle operation has been approved | Requires separate explicit owner authorization and qualified safety review |

`CUSTOM_INTEGRATION_RESEARCH_AUTHORIZED_OFFLINE` is a development-track status only. `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remains the vehicle status, and `safeForHonda()` remains `false`.

Legacy labels remain useful when qualified by scope: **Honda receiver NO-GO** and **Honda display NO-GO** mean the OEM interfaces are unresolved for vehicle deployment. They do not prohibit the newly authorized offline custom-integration research.

## Rules for updating status

- Change `current.md`, `blockers.md`, `milestones.json` and `NEXT_ACTION.md` only through the maintenance workflow, in a PR that names the evidence.
- Never write a completion percentage, an optimistic summary, or a pass for something that has not run.
- A document that records a result names the exact commit, the check, and the class of evidence.
