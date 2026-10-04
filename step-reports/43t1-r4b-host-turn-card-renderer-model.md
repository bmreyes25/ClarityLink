# 43T1-R4B — host-only synthetic turn-card renderer model

## Repository start and scope

- Starting branch: `main`.
- Starting HEAD and `origin/main`: `90d6ec53df5f07f43dc7d7cadd3eb7f5016ec26b`.
- Worktree: pre-existing uncommitted edits in `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`, plus six untracked R3 draft files. These were preserved and excluded from R4B commits.
- Final research HEAD: `9813a70adff5bc69d64d0f5e394e508e7177c584`; a subsequent report-only commit records hosted results.
- Honda contacted: **NO**. ADB used: **NO**. Runtime reads: **0**. Runtime writes: **0**. Vehicle connected: **NO**. `jmcs` used: **NO**. Type111 used: **NO**. RAM attachment: **NO**. Listener created: **NO**. APK installed: **NO**.

## Model and evidence

The new pure Python [turn-card model](../src/claritylink-renderer/turn_cards.py) accepts synthetic/manual `Route` and `RouteStep` records. It validates route state, generation, step index, maneuver enum, distance, street/lane text, optional ETA, update time and simulated source trust. It produces a deterministic JSON-ready `TurnCard` with current/next maneuver, distance, street, secondary hint, ETA, route progress, warning, mode and evidence label. The [requirements](../research/runtime/43t1-r4b-turn-card-renderer-requirements.md) describe the input/output contract and proof boundary.

The synthetic layout has seven nonoverlapping regions in an 800×480 canvas for primary maneuver, distance, street, secondary instruction, ETA/progress, warning banner and evidence label. The canvas dimensions are consistent with preserved `HONDA_OBSERVED` Display 1 evidence; the rectangles are `MODEL_ONLY` and do not claim the physical cluster safe area. The host [JSON preview](../tools/r4b_preview.py) reads ten invented [fixture cases](../tests/fixtures/r4b_turn_cards.json) and has no transport or device backend.

Freshness model: active guidance through age 5 s; stale warning and **no turn fields** above 5 s; lost warning above 30 s. Explicit stale/lost/error/rerouting, unknown maneuver, untrusted-source fixture state, future timestamp and manual clear also suppress turns. Arrival shows a destination-reached state. All thresholds are `MODEL_ONLY` constants, not road-safe timing decisions. The trust flag is an input branch, not actual authentication. A geographically wrong but syntactically valid maneuver cannot be detected.

Fixtures cover left/right, freeway exit, reroute, stale/lost, arrival, unknown maneuver, long/missing street and night mode. Focused tests cover those cases, every maneuver kind, schema rejection, layout bounds/nonoverlap, text budget, freshness boundaries, warning precedence, day/night projection, and a static dependency boundary excluding Honda receiver, Type111, Android, network listener and runtime backends. The stock-center-CarPlay non-interference invariant is **architectural**: this model has no path to the Honda receiver or center screen. It is not an on-car coexistence observation.

**R4B proves:** deterministic host-side validation/projection and fail-closed suppression under the tested synthetic states. **R4B does not prove:** Honda Display 1 app access, physical crop/safe area, warning visibility, display priority, Type110 runtime coexistence, route correctness, phone/source security, driving safety or deployability. R3C's runtime-interposition NO-GO remains in force. R4B does not authorize a car experiment.

## ECC-guided safety review

Manual @ECC-guided research/code/safety review checked evidence labels, schema failure behavior, warning precedence, stale data, route source spoofing limits, layout bounds, distraction, accidental receiver/Type111 dependencies, and current authorization wording. The [R4B failure rows](../docs/safety/runtime-failure-matrix.md) record remaining hazards. **Manual @ECC-guided review completed; no independent ECC reviewer/service sign-off occurred.**

## Verification and decision

- Focused tests: `.venv/bin/python -m pytest -q tests/renderer/test_turn_cards.py` — 26 passed. JSON preview generation and parsing passed for all ten fixtures.
- Full suite: `PYTHON=.venv/bin/python ./tools/run_tests.sh` — 700 Python tests passed, 3 skipped; 3 self-locator smoke tests and configured simulator JavaScript checks passed.
- Repository health: `.venv/bin/python tools/check_repo_health.py` passed with 0 curated broken links and 0 forbidden tracked extensions.
- `git diff --check`: passed before commit.
- Hosted Offline CI: [passed on research HEAD `9813a70`](https://github.com/bmreyes25/ClarityLink/actions/runs/37212421204).
- Hosted CodeQL: [passed on research HEAD `9813a70`](https://github.com/bmreyes25/ClarityLink/actions/runs/37212421265); no findings were suppressed for this milestone.
- Decision: **`R4B_HOST_RENDERER_MODEL_COMPLETE`**.
- Project recommendation: **`GO_FOR_R4C_DISPLAY_ACCESS_STATIC_REVIEW`**.
- Next milestone: offline-only static review of a supported, independently owned Display 1 app path and physical warning/safe-area boundaries. No Honda/ADB/runtime/vehicle work is authorized.
