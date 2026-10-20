# Active blockers

This page records current evidence and open gates. Historical reports remain unchanged.

| Blocker | State | Evidence or required resolution | Milestone |
|---|---|---|---|
| CL-R4 reliability acceptance | Complete in laboratory | Final API17 run passed all 12 required cases and 12 priority combinations on one source fingerprint/APK. See `build/cl-r4-acceptance-20261019-234709-22337/` locally; generated evidence is not published. | CL-R4 |
| PR #38 publication | Complete | Merged to online `main` on 2026-10-20 as `fadcdad7654683c6c94ba341ab77d47843e14863`. Offline CI and configured CodeQL checks passed on PR head `425193360f36b23ae9ac9f5b8b092503e3d50449`. | Publication |
| Genuine authenticated Honda Type111 receiver contract | Unknown | No documented supported capability advertisement, Honda SETUP schema, receiver-session authority, stream-delegation, or same-session transport contract has been established. Keep production adapter disabled. | CL-R5 |
| Honda Display 1 frame-admission contract | Unknown | No supported OEM-owned frame input, display ownership, geometry, warning precedence, or restoration contract has been established. Do not write the cluster framebuffer or patch factory binaries. | CL-R6 |
| Hardware validation | Not started | No Honda ADB, installation, firmware operation, live iPhone experiment, or physical vehicle test is authorized by this campaign. Any future vehicle test requires separate specific authorization, preconditions, equipment, stop conditions, evidence capture, restoration, and independent safety review. | CL-R7+ |
| License choice | Owner decision | The repository has no selected license. Do not add a license or imply open-source reuse permission until the owner chooses one. | Repository |

Historical FinalizerWatchdogDaemon behavior remains **NOT REPRODUCED** and unattributed. The laboratory does not establish vehicle compatibility or hardware safety. `safeForHonda()` remains `false`.
