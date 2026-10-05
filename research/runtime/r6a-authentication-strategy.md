# R6A authentication strategy

No route is currently proven usable. MFi authentication is mandatory; no bypass, private-key extraction, fake signature or disabled verification is an option.

| Route | Evidence | Required interface | Host / target feasibility and blocker |
|---|---|---|---|
| A. Reuse installed Honda MFi subsystem | stock CarPlay works; exact owner unknown | challenge/sign operation mediated by installed hardware, lifecycle and permission contract | target plausible but EVIDENCE_REQUIRED; host unavailable |
| B. Reuse Honda transport + auth libraries | `jmcs` DT_NEEDED does not identify MFi API | stable library calls plus transport handoff | target unknown, ABI and ownership blocked; host unlikely |
| C. Reuse existing lawful PlayPort host auth | 43P authenticated current iPhone in separate host lab | documented adapter/session context handoff | host possible only after explicit code/interface review; Python receiver has none today |
| D. Independent standards-compatible auth | public implementations are prior art | legitimate certified hardware/service and complete protocol | unknown; no credential substitution or restricted material |

Immediate work: trace lawful host lab's auth provider boundary and Honda's preserved auth call graph separately. Log metadata only, never challenges, certificates or keys.
