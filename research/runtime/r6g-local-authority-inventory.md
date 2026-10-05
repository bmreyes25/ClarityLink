# R6G local Mac authority inventory

Inventory performed 2026-10-05 before any provisioning or authentication traffic. Read-only metadata only; no arbitrary device interfaces were opened.

| Candidate | Vendor / model | VID/PID | Connected / Mac-visible | MFi authority | CarPlay receiver | iAP2 owner | Control owner / API | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| Selected Carlinkit CPC200-CCPA + compatible genuine MFi coprocessor | Carlinkit; CPC200-CCPA is the R6F-selected family; no device label available | Not available | No matching USB product/vendor string; no CPC200 device identified | Not present/validated | Not present | None locally identified | None locally identified | `NOT_PRESENT` | `system_profiler -detailLevel mini SPUSBDataType` exited 0 but returned an empty report; filtered `ioreg -p IOUSB` fields contained no CPC200/Carlinkit/LIVI product/vendor match. No VID/PID inferred. |
| LIVI Link service/helper | f-io LIVI public software; no helper/dongle found | N/A | No local hardware endpoint identified | Service not available | No session owner running | None confirmed | Public source owns its internal control stack; no installed local bridge found | `NOT_PRESENT` | R6F documented no unit; current USB metadata has no selected device; no LIVI process/config endpoint identified in this read-only check. |

No MFi command, iAP2 traffic, authentication attempt, or network discovery was performed. A blank `system_profiler` report is not positive evidence for unrelated hardware being absent; this inventory conclusion is limited to the selected CPC200/LIVI authority candidate. Status for that candidate is `NOT_PRESENT`.
