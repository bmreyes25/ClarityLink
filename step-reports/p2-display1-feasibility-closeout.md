# P2 Display 1 feasibility closeout (P2-C5 and P2-C6)

**Repository:** `bmreyes25/ClarityLink`
**PR:** #19 (left open; not merged)
**P2-C5 starting HEAD:** `90c3dd948b107d24b5d09d19f37e25db990ddd4d`
**P2-C6 reviewed starting HEAD:** `3df3367049e9aae18281071a3dc29b7998350d82`

## P2-C5 — no-APK read-only inventory

The previous P2 chunks establish three separate gates. API17 `DisplayManager` enumeration is available to Android application code. The existing AOSP API17 shell diagnostic identity has `DUMP` permission and can request `dumpsys display` without installing ClarityLink, subject to a future exact-Honda verification of shell UID/API level and service behavior. This query reports the logical display service inventory. It cannot create an Android application context/window token, test WindowManager admission, prove a Surface is visible, identify the physical navigation rectangle, or establish warning precedence.

The default-disabled [collector](../tools/p2c5_display1_collector.py), fixed [manifest](../research/architecture/p2c5-display1-manifest.json), private [evidence schema](../research/architecture/p2c5-display-observation.schema.json), tests, and [authorization plan](../research/architecture/p2c5-display1-diagnostic-plan.md) are scoped to four exact read-only commands: pinned target `get-state`, `shell id`, API level query, and `shell dumpsys display`. They require exact hashes and serial, shell UID 2000, API17, fresh operator confirmations, a 12-second timeout per command, zero retries, zero fallbacks, and private local evidence. Fake-ADB tests passed; no real ADB or Honda command ran.

**P2-C5 decision:** `READ_ONLY_PACKAGE_REVIEW_READY`. The package is ready for separate review/authorization. No Honda observation has been made under P2-C5.

## P2-C6 — architecture comparison and decision

| Path | Current assessment |
|---|---|
| A. Public `Presentation` | The API17 emulator demonstrated a valid app route and lifecycle. Honda caller admission, bounds, z-order, and warning behavior are unknown. A legitimate Android app context/window token is required; a temporary shell/native process does not supply one. |
| B. Existing Honda display service | Existing AP Binder is control/status only. Render host owns its roots and `onBind()` returns null. No external arbitrary-content Surface/FD/View API was identified. |
| C. Temporary no-APK native process | Can request a read-only service dump under shell identity if permitted. No supported public app WindowManager context/token or visible rendering path. Direct framebuffer/privileged compositor access is excluded. |
| D. Separately approved temporary app installation | Most direct experiment if the no-APK restriction is explicitly changed. An ordinary app package provides a legitimate UID and Activity context; Honda admission and safety remain unproven. Installation persists until separately removed and requires an explicit rollback plan. |
| E. OEM-supported display adapter | Best long-term boundary if Honda supplies a signed additive API with caller admission, bounded surface, warning precedence, and client-death cleanup. No such interface was found in reviewed artifacts. |
| F. Revised deployment mechanism | Only useful if it explicitly provides a supported app context or OEM API. Merely launching native code does not bypass Android permissions. Requires new user approval and independent proof. |

**Decision 1 — current restrictions:** `NO_GO_FOR_VISIBLE_RENDERING` / **CONDITIONAL**, never vehicle-ready. Read-only enumeration is possible to prepare without an APK, but no window is admitted and no physical safe rectangle is known.

**Decision 2 — if a restriction changes:** option D, a separately approved, temporary unprivileged APK using public API17 `Presentation`, is the most direct first admission experiment. Option E, a documented OEM additive adapter, is the preferred product integration if Honda makes one available. Neither decision authorizes installation, admission testing, or visible rendering. Explicit approvals remain separate for each step.

The [rendering contract](../research/architecture/display1-rendering-contract.md) enumerates all evidence gates. The [machine-readable option matrix](../research/architecture/p2c6-deployment-options.json) records context, UID/signature, admission, physical geometry, bounds, warning precedence, stock ownership, crash restoration, persistence, reversibility, required evidence, and approvals for all six paths.

## Validation and review

- P2-C2 existing isolated API17 emulator evidence: `API17_EMULATOR_PASS`; this is generic emulator evidence and does not prove Honda admission.
- P2-C5 fake-ADB focused tests: 11 passed; dry run returned `DRY_RUN_NO_ADB`.
- Full final offline suite after P2-C6 changes: 1,259 passed, 14 skipped; standard-library smoke checks (3) and simulator JavaScript checks passed.
- Repository health and `git diff --check` passed for final working tree before commit.
- ECC review: manual ECC-guided review of context/UID boundaries, permission assumptions, read-only command scope, evidence privacy, composition, warnings, lifecycle, and explicit approval boundaries. No independent reviewer was invoked.
- Honda ADB commands, writes, installs, display operations, and renders: **zero**.

P2-C6 changes are documentation/matrix only. PR #19 remains open; P3-C1 is not started.
