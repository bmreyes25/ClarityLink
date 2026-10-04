# 43T1-R4C — Display 1 access static review

## Starting state and prohibited activity

- Starting branch: `main`; starting HEAD and `origin/main`: `80a64a96f823e43fed3cc1043d3d5b0fd9eab6bf`.
- Starting worktree: five modified current/history files (`EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, `step-reports/README.md`) and six untracked R3 draft files. These were preserved and excluded from R4C commits.
- Final research HEAD: `ce36bb39d0f0633bd826ad46e426d47a7f8b0ab6`; the report-only verification commit follows this record.
- Honda contacted: **NO**; ADB used: **NO**; runtime reads: **0**; runtime writes: **0**; vehicle connected: **NO**; APK installed: **NO**; `jmcs` used: **NO**; Type111 used: **NO**; HondaHack runtime used: **NO**. No framebuffer, USB, CAN, root, ptrace or live-listener work occurred.

## Evidence reviewed and findings

Starting from [R4B](43t1-r4b-host-turn-card-renderer-model.md), [R4A](43t1-r4a-post-interposition-architecture-pivot.md) and [R3C](43t1-r3c-static-entry-ownership-closure.md), R4C reviewed the preserved [safe-area comparison](../research/navigation-safe-area.md), [HondaHack output path](../research/hondahack/hondahack-display-path.md), [ExternalDisplay API audit](../research/display/externaldisplay-api-surface.md), [companion rendering study](../research/display/companion-rendering-path.md), relevant decoded manifests/Java/Binder interfaces, and AOSP `android-4.2.2_r1` source plus Android API references. The following research records give exact provenance and limits:

- [API-17 external-display review](../research/runtime/43t1-r4c-api17-external-display-static-review.md): public `Presentation`, display-context, display enumeration and removal lifecycle exist. **Correction to R4A:** API17's presentation category selects HDMI by *display type*; `Display.FLAG_PRESENTATION` is a later API19 concept. Public target-display Activity launch is API26, and public virtual-display creation is API19. Generic API availability is `DOCUMENTED_ANDROID`, never Honda success.
- [Honda Display 1 ownership audit](../research/runtime/43t1-r4c-honda-display1-ownership-audit.md): Honda `ExternalDisplayOutService` owns the observed full-frame main/interrupt/bottom roots on HDMI Display 1. It gets all displays, selects the last and creates a display-context WindowManager; its exported `onBind()` returns null. `ExternalDisplayApService` Binder carries control/status, not arbitrary app pixels. Navigation interfaces are semantic guidance, not a View/Surface sink.
- [Permission/signing audit](../research/runtime/43t1-r4c-display-permission-signing-audit.md): AOSP API17 classifies `SYSTEM_ALERT_WINDOW` as dangerous and `INTERNAL_SYSTEM_WINDOW` as signature; Honda's host requests both and uses type-2006 windows. A normally signed app might use a public `Presentation` without those Honda permissions in generic AOSP, but Honda window policy/grants remain `UNKNOWN`. Reviewed custom `VEHICLE_RW` and `ACCESS_MAP` definitions/grants were not recovered.
- [Physical safe-area boundary](../research/runtime/43t1-r4c-physical-safe-area-and-warning-boundary.md): Display 1 is an observed 800×480 canvas, not a full physical cluster image. Paired physical photo contains gauges/status absent from its screenshot. Downstream transform, warning regions and relative z-order are `UNKNOWN`; HondaHack's local layout dimensions are not physical safe coordinates.

The [candidate matrix](../research/runtime/43t1-r4c-display-access-matrix.md) finds **API17 `Presentation` from an ordinary app** the best independent static lead: no `jmcs`, Type111, HondaHack/Xposed, service replacement or framebuffer path is inherent to it. No preserved artifact demonstrates a separately owned ordinary app successfully rendering on Honda Display 1 or staying below warnings. The generic WindowManager overlay route has unresolved full-screen warning and Navigation displacement risk. Exported Honda services lack content APIs; semantic Navigation Binder is not a pixel API; HondaHack/in-process, framebuffer and receiver routes remain rejected.

The [independent-app feasibility gate](../research/runtime/43t1-r4c-independent-display-app-feasibility-gate.md) remains **`NOT_AUTHORIZED`**. The [renderer deployment constraints](../research/runtime/43t1-r4c-renderer-deployment-constraints.md) require display admission, signing/permissions, lifecycle, source/authentication, clearing, physical protected region, disable switch, stock coexistence, crash cleanup and long-session evidence. R4C establishes a plausible AOSP candidate and corrects API-version assumptions; it **does not** prove Honda app access, physical safe area, warning priority, driving safety or deployment readiness.

## ECC-guided review and decision

Manual @ECC-guided research/security/safety review checked source provenance, API-version drift, manifest permission versus actual grant, Binder content type, app/process ownership, HondaHack overgeneralization, warning visibility, stock center CarPlay, and authorization wording. The [R4C failure matrix rows](../docs/safety/runtime-failure-matrix.md) record the outstanding failure modes. **Manual @ECC-guided review completed; no independent ECC reviewer/service sign-off occurred.**

- Focused checks: version-correct AOSP source passages and preserved Honda manifest/Binder/window-owner references reviewed; health checker compiles; R4C document links and current-milestone sections pass repository health.
- Full suite: `PYTHON=.venv/bin/python ./tools/run_tests.sh` passed — 700 Python tests passed, 3 skipped; 3 self-locator smoke checks and configured simulator JavaScript checks passed.
- Repository health: `.venv/bin/python tools/check_repo_health.py` passed — 0 curated broken links and 0 forbidden tracked extensions.
- `git diff --check`: passed before commit.
- Hosted Offline CI: [passed](https://github.com/bmreyes25/ClarityLink/actions/runs/37213885915) on pushed research HEAD `ce36bb39d0f0633bd826ad46e426d47a7f8b0ab6`.
- Hosted CodeQL: [passed](https://github.com/bmreyes25/ClarityLink/actions/runs/37213885964) on the same pushed research HEAD. No findings were suppressed for this milestone.
- Decision: **`R4C_DISPLAY_ENTRY_POSSIBLE_BUT_UNPROVEN`**.
- Project recommendation: **`GO_FOR_R4D_MORE_STATIC_DISPLAY_RESEARCH`**.
- Next milestone: offline static search for Honda's display policy/flag behavior, package grants and a documented ordinary-app admission route, plus warning/z-order evidence. No APK, ADB, Honda, runtime or vehicle action is authorized.
