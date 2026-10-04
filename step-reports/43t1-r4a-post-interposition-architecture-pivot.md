# 43T1-R4A — offline architecture pivot after runtime-interposition NO-GO

## Scope and repository start

- Starting branch: `main`.
- Starting HEAD and `origin/main`: `6a6ffa4c284a1854d69ed0634e0a341d179cf223`.
- Worktree: existing uncommitted edits in `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`, plus six untracked R3 draft files. Those user edits/drafts were preserved and excluded from the R4A commit.
- Final research HEAD: `b98b073e083ee3e0b659af403d644165367eeb44` (the subsequent report-only verification commit records these hosted results).
- Honda contacted: **NO**. ADB used: **NO**. Runtime reads: **0**. Runtime writes: **0**. Vehicle connected: **NO**. RAM attachment: **NO**. Live listener: **NO**. Type111 negotiation: **NO**.

## Evidence and decision

The preserved [R3C report](43t1-r3c-static-entry-ownership-closure.md) returns `R3C_NO_SAFE_RUNTIME_EXTENSION_PATH_FOUND` and `ABANDON_RUNTIME_INTERPOSITION_UNTIL_NEW_EVIDENCE`. This remains the controlling receiver result. R4A reviewed the saved [Navigation/Display 1 evidence](../research/navigation-safe-area.md), [HondaHack output path](../research/hondahack/hondahack-display-path.md), [ExternalDisplay API surface](../research/display/externaldisplay-api-surface.md), and [companion display study](../research/display/companion-rendering-path.md). It compared own-app MapKit, Google Routes, Mapbox, OSRM, Valhalla, HERE, TomTom, manual/synthetic routes, and Shortcuts/App Intents using the official/public links and provenance in the [navigation audit](../research/runtime/43t1-r4a-navigation-data-source-audit.md).

Candidates and verdicts are in the [architecture matrix](../research/runtime/43t1-r4a-architecture-pivot-matrix.md). The **best next research path** is a host-only, turn-card-first cluster renderer model, fed initially by synthetic/manual route steps. This uses neither `jmcs` nor Type111 by design. An independently installed Android renderer's Display 1 access, physical cluster safe area, z-order, warning visibility, and stock CarPlay coexistence are still `UNKNOWN`; R4A has **not** established a deployable Honda architecture. Phone companion and external route provider remain possible later data sources, contingent on an independent display entry, permission/terms, secure channel, and privacy review. Apple Maps/Waze active-trip extraction, HondaHack/Xposed as an integration dependency, and `jmcs` interposition are rejected under current evidence.

Decision: **`R4A_PIVOT_TO_CLUSTER_NAV_RENDERER`**. Project recommendation: **`GO_FOR_R4B_OFFLINE_RENDERER_MODEL`**. The [ADR](../research/adr/43t1-r4a-post-interposition-architecture-pivot.md) and [new-evidence gate](../research/runtime/43t1-r4a-new-evidence-gate.md) keep receiver interposition, Type111 negotiation, RAM review, and car experiments **NOT AUTHORIZED**. R4B may test only synthetic frame/layout and stale-state behavior; it must not claim Honda display compatibility or real navigation safety.

## ECC-guided review and verification

Manual @ECC-guided research and safety review checked provenance labels, Android/iOS public API scope, user-controlled route data, third-party terms/keys, stale and wrong-turn failure states, distraction, stock Type110 ownership, Display 1 uncertainty, and authorization wording. The [failure matrix](../docs/safety/runtime-failure-matrix.md) records the R4A hazards. **Manual @ECC-guided review completed; no independent ECC reviewer/service sign-off occurred.**

- Focused checks: Python compilation of the repository health checker and its current-milestone/link check passed.
- Full suite: `PYTHON=.venv/bin/python ./tools/run_tests.sh` passed — 674 Python tests passed, 3 skipped; 3 self-locator checks and configured simulator JavaScript checks passed.
- Repository health: `.venv/bin/python tools/check_repo_health.py` passed — 0 curated broken links, 0 forbidden tracked extensions.
- `git diff --check`: passed before commit.
- Hosted Offline CI: [passed on research HEAD `b98b073`](https://github.com/bmreyes25/ClarityLink/actions/runs/37179969099).
- Hosted CodeQL: [passed on research HEAD `b98b073`](https://github.com/bmreyes25/ClarityLink/actions/runs/37179969047); no findings were suppressed for this milestone.

## Next milestone

43T1-R4B: host-only synthetic turn-card renderer model and evidence-focused Display 1 access review. No Honda/ADB/runtime work or vehicle experiment is authorized by R4A.
