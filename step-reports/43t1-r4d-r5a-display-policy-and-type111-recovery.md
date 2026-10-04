# 43T1-R4D/R5A — Display 1 policy and Type111 recovery research

## Repository state and boundary

- Starting branch: `main`.
- Starting HEAD: `67a50f7444c066a44fc2074341694882873d7964`.
- Final HEAD: pending milestone commit / hosted verification.
- Starting worktree: pre-existing modifications to `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`, plus untracked R3 drafts. During this milestone additional untracked `src/claritylink-sandbox/` and `tests/sandbox/` files appeared; they were preserved and excluded as unrelated work. Only milestone-owned additions/hunks are included.
- Honda contacted: **NO**.
- ADB used: **NO**.
- Runtime reads: **0**.
- Runtime writes: **0**.
- Vehicle connected: **NO**.
- APK installed: **NO**.
- `jmcs` used: **NO**.
- Type111 used: **NO**.
- HondaHack runtime used: **NO**.
- RAM attached: **NO**. Listener created: **NO**.

This combined milestone attacks two static bottlenecks: ordinary Display 1 policy/admission and lawful Honda-descendant artifact research for Type111. No car experiment, ADB session, install, receiver modification, or runtime path is authorized.

## Rules v2 compliance

Rules v2 is already adopted and hosted-verified. The [compliance check](../research/runtime/r4d-r5a-rules-v2-compliance-check.md) makes no governance rewrite and returns **`RULES_V2_COMPLIANT`**. The milestone was offline-only. R3C remains the controlling `jmcs`/Type111 NO-GO; R4C's ordinary-app admission remains unproven. Any future car test requires an exact written run plan and explicit user authorization. **@ECC** review checked scope, provenance, preserved work, and authorization language; no independent ECC reviewer/service sign-off is claimed.

## R4D — Display 1 admission

### Framework policy

Version-matched AOSP API17 documents public `Presentation`, display enumeration/context, and type-2006 (`TYPE_SYSTEM_OVERLAY`) policy. Honda's ExternalDisplayOutService enumerates logical displays, creates a display context, and owns full-frame type-2006 bottom/main/interrupt roots. The repository lacks complete, build-matched Honda `WindowManagerService`, `DisplayManagerService`, `PhoneWindowManager`/policy, and ActivityManager policy evidence. No ordinary-app failure, trusted-process gate, Honda-specific package allowlist, or AOSP/Honda policy delta is proven. Missing framework source is **UNKNOWN**, not proof that restrictions do not exist.

### Permission and grant findings

The new static review of `research/extracted/config/data/system/packages.xml` finds standalone UID 10056 for ExternalDisplayOutService, with no shared UID. Its manifest requests `SYSTEM_ALERT_WINDOW` and `INTERNAL_SYSTEM_WINDOW`. The preserved packages.xml shows the corresponding permission items under `android.uid.phone` shared-user grants, not under the externaldisplay package/UID. HondaHack UID 10091 has a package-level `SYSTEM_ALERT_WINDOW` item, which does not establish ClarityLink access. The snapshot may be incomplete/stale and is not a current runtime permission query, so effective grants remain **UNKNOWN**. AOSP API17 classifies the former as dangerous and the latter as signature. `ACCESS_MAP` appears in HondaHack's copied `platform.xml` group mapping, but no owning permission definition/grant to an ordinary app was found. `VEHICLE_RW` definition/protection/grant likewise remains unknown. No grant establishes Display 1 admission.

### Admission and warning/z-order

The [admission matrix](../research/runtime/43t1-r4d-app-window-admission-matrix.md) distinguishes enumeration from window admission. Public API17 `Presentation` does not inherently require HondaHack, `jmcs`, or Type111 under generic AOSP. Honda compatibility, ordinary-app grant, display lifecycle, and z-order are unproven. Existing Honda full-frame bottom/main/interrupt roots are statically evidenced, but priority relative to a new window is unknown. Physical indicators absent from Display 1 capture support downstream composition as an inference, not a safe-area measurement. No warning-preserving region can be proven from repository evidence.

**R4D framework policy:** `POSSIBLE_BUT_UNPROVEN`.

The [ordinary-app gate](../research/runtime/43t1-r4d-ordinary-app-display1-admission-gate.md) remains **`NOT_AUTHORIZED`** and requires known signing/grants, Honda enumeration/window path, lifecycle/removal, z-order/warning limitations, and physical viewport before any separately authorized future experiment.

## R5A — descendant artifacts and Type111

Official Honda materials establish some later Civic/Accord configurations have CarPlay and/or instrument-cluster turn-by-turn guidance. These are route metadata/feature claims, not receiver-binary evidence: see the [2021 Civic owner's manual](https://techinfo.honda.com/rjanisis/pubs/OM/AH/BTJB2121OM/enu/BTJB2121OM.PDF), [2021 Civic Hatchback CarPlay guide](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2021%2FCivic+Hatchback%2F2021_Civic_5D_Apple_CarPlay_Integration.pdf), [2018 Accord press kit](https://hondanews.com/en-US/releases/2018-honda-accord-press-kit-overview), and [2018–2022 Accord upgrade notice](https://hondanews.com/en-US/honda-automobiles/releases/release-97d09069e73c229822892485de000817-honda-enhances-ownership-experience-with-upgrade-to-wireless-apple-carplay-and-android-auto-for-2018-2022-accord-models). The reviewed public notices do not publish receiver binaries. Model-year/trim family linkage to the preserved `vcm30t30` artifact remains unverified.

No Honda/Acura descendant binary with linked Type111 parse, response `{type:111,dataPort}`, distinct `streamConnectionID`, second screen/security/listener, and teardown was found. No additive receiver API or supported plugin loader was found. Generic Apple secondary-display evidence, current-iOS two-stream lab evidence, external legacy AES Type111 prior art, and iAP2/TBT metadata do not prove Honda Type111. The [signature checklist](../research/runtime/r5a-type111-static-signature-checklist.md) defines future positive criteria and insufficient outcomes. The [artifact rules](../research/runtime/r5a-artifact-legality-and-handling.md) prohibit committing proprietary binaries or restricted Apple/MFi code; only hashes, version/build identifiers, filenames, and derived notes belong in the repository.

## Combined path decision

The [decision matrix](../research/runtime/r4d-r5a-next-path-decision-matrix.md) keeps the host-only R4B preview as the lowest-risk immediate repository value and selects lawful public version/build/artifact research for the next milestone. Ordinary-app Display 1 remains promising but unproven. Privileged/HondaHack/receiver modification paths remain rejected or parked under current constraints.

## What was proven / unknown

**Proven within static/documentary scope:** API17 generic `Presentation` exists; Honda's preserved package records identify separate service UIDs; the package grant snapshot places relevant permission items on the phone shared UID rather than ExternalDisplayOutService's package record; Honda's renderer owns three full-frame roots; public Honda sources describe some cluster route guidance; R3C remains the receiver NO-GO.

**Unknown:** current effective OEM grants; whether Honda framework matches AOSP; ordinary app display enumeration/window admission; any package/signature or trusted UID requirement; window lifecycle, z-order, warning priority, downstream transform/safe area; exact descendant-to-vcm30t30 lineage; and any Honda descendant Type111 binary path.

## Verification and repo health

- ECC findings: manual **@ECC** evidence/safety review completed; no independent ECC service/reviewer sign-off.
- Focused checks: `.venv/bin/python -m py_compile tools/check_repo_health.py` passed; updated milestone-aware repository health and curated documentation links passed.
- Full suite: `PYTHON=.venv/bin/python ./tools/run_tests.sh` — **700 passed, 3 skipped**; 3 self-locator smoke tests passed; configured simulator JavaScript checks passed; private capture-backed replay skipped because fixtures are not CI inputs.
- Repository health: `.venv/bin/python tools/check_repo_health.py` — **passed**, 508 Markdown files, 123 indexed milestone/support reports, 0 curated broken links, 0 forbidden tracked extensions.
- Diff check: `git diff --check` — passed.
- Hosted Offline CI: pending exact pushed milestone commit.
- Hosted CodeQL: pending exact pushed milestone commit; findings will not be suppressed.

## Decisions

- Rules compliance: **`RULES_V2_COMPLIANT`**.
- R4D: **`R4D_ORDINARY_APP_DISPLAY1_POSSIBLE_BUT_UNPROVEN`**.
- R5A: **`R5A_HONDA_TYPE111_DESCENDANT_PROMISING_BUT_NO_BINARY`**.
- Project recommendation: **`GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`**.
- Next milestone: lawful public Honda/Acura version/build/artifact target research; no private binary acquisition, runtime work, or vehicle action follows automatically.

**No Honda/ADB/runtime work was performed. This milestone is offline Rules v2 compliance confirmation, static Display 1 policy research, and Honda Type111 recovery research only; it does not authorize a car experiment.**
