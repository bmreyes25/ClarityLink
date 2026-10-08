# R7E Test C — Presentation admission and Surface acquisition

**Plan state:** `BLOCKED_BY_PRIOR_TEST` / `NOT_AUTHORIZED`  
**Risk:** Tier 3, temporary display state change.

**Objective:** After separately authorized A and B passes, determine whether a project-owned API17 `Presentation` can be constructed and admitted to the independently observed candidate display, and whether a Surface/ANativeWindow is acquired. Record each distinct state: `DISPLAY_ENUMERATED`, `DISPLAY_CONTEXT_CREATED`, `PRESENTATION_CONSTRUCTED`, `PRESENTATION_SHOW_REQUESTED`, `PRESENTATION_SHOWN`, `SURFACE_CREATED`, `ANATIVEWINDOW_READY`. Never infer a later state from an earlier one.

**PROPOSED — NOT EXECUTED:** run only the audited `--presentation-preflight` mode against the previously recorded candidate display ID, with blank/cleared neutral content, no frame posting, and no loop. Candidate ID is runtime evidence and must be confirmed in the future run record; none is supplied now.

**Write/resource audit:** display/window state changes temporarily; Presentation, Surface and native window may be created; no persistent files or network listener; no USB/iAP2/authentication. Least privilege only. Exact command remains dependent on a built artifact and separately approved A/B outcomes.

**Safety/stop/rollback:** safe area, crop and warning z-order remain UNKNOWN. No geometry claims or screenshot-derived bounds. Stop immediately on unexpected visible content, warning/cluster change, instability, or resource cleanup failure. Dismiss Presentation, release Surface/ANativeWindow, stop process, verify no owner remains and check normal center UI, cluster, warnings and audio.

**Success:** explicit state diagnostics reach only the individually recorded admission/Surface stages. It does not prove safe region or visible rendering. **Readiness:** `BLOCKED_BY_PRIOR_TEST`; requires separately authorized Test A and Test B passes. No current authorization.
