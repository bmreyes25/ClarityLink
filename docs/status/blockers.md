# Active blockers

This page records current evidence and open gates. Historical reports remain unchanged.

| Blocker | State | Evidence or required resolution | Milestone |
|---|---|---|---|
| Complete final-source CL-R4 matrix | Open | CL-R4-01 and CL-R4-04 have passed on separate candidate fingerprints; CL-R4-07 and P02/P03 have also passed on an earlier focused candidate. The full 12-case matrix has not passed on one frozen source/APK. P04 View death during teardown, P05 compositor-owner death during child cleanup, P06 decoder shutdown during active delivery, P08 multiple consecutive View replacements, and aggregate cleanup P12 remain unverified. | CL-R4 |
| CL-R4 race fixes | Focused fixes verified; final acceptance pending | The crash-recovery assertion now uses the generation reported by the actual death/detach callback, fixing a stale initial-registration match. Parent teardown completion is idempotent when an asynchronous close acknowledgement completes immediately before the synchronous owner check. API17 CL-R4-04 passed after this correction; rerun the complete matrix and CL-R7 on the same final source. | CL-R4 |
| PR #37 Offline CI | Open | The observed Offline CI failure was `tools/check_repo_health.py` rejecting stale pinned hashes in `docs/status/cl-r0-review-scope.json`; pytest did not run in that failed job. Refresh scope hashes only after the changed source and documentation receive exact-source review, then rerun Offline CI. CodeQL success does not satisfy this gate. | Publication |
| PR #37 approving review | Required | No approving GitHub review was recorded at the last check. Obtain the required human approval and merge only through protected-main requirements. | Publication |
| Genuine authenticated Honda Type111 receiver contract | Unknown | No documented supported capability advertisement, Honda SETUP schema, receiver-session authority, stream-delegation, or same-session transport contract has been established. Keep production adapter disabled. | CL-R5 |
| Honda Display 1 frame-admission contract | Unknown | No supported OEM-owned frame input, display ownership, geometry, warning precedence, or restoration contract has been established. Do not write the cluster framebuffer or patch factory binaries. | CL-R6 |
| Hardware validation | Not started | No Honda ADB, installation, firmware operation, live iPhone experiment, or physical vehicle test is authorized by the current campaign. Any future vehicle test requires separate specific authorization, preconditions, equipment, stop conditions, evidence capture, restoration, and independent safety review. | CL-R7+ |
| License choice | Owner decision | The repository has no selected license. Do not add a license or imply open-source reuse permission until the owner chooses one. | Repository |

Historical FinalizerWatchdogDaemon behavior remains **NOT REPRODUCED** and unattributed. The laboratory does not establish vehicle compatibility or hardware safety. `safeForHonda()` remains `false`.
