# CL-FACTORY-01 / M9 — Read-only parked-car ADB collection plan (PROPOSAL — NOT EXECUTED)

Status: PROPOSAL for separate approval. **No ADB is run; no vehicle is accessed by this document.**
`safeForHonda() == false`. Requires explicit owner approval of this exact allowlist before any execution.
Parked only; never while driving. No `su`/root. No writes, installs, mounts, injection, Binder control, CAN, or
CarPlay configuration changes. No automatic escalation or fallback to broader commands.

## Purpose
Answer only the questions that offline analysis of the preserved image cannot resolve, using the minimum
read-only observation. Each command is justified, bounded, and has a stop condition.

## Preconditions (manual, operator-confirmed)
- Vehicle parked, transmission in Park, parking brake set; a dedicated test session; no personal phone paired.
- ADB authorized interactively by the operator on the unit; `adb` connects read-only; session is logged with
  redaction. Stop immediately if any prompt requests elevation or if unexpected processes appear.

## Allowlist (read-only)
| # | Question (offline cannot resolve) | Exact command | API17 support | Access | Expected output | Side effects | Output bound | Stop condition |
|---|---|---|---|---|---|---|---|---|
| 1 | Is the live build identical to the preserved image? | `adb shell getprop ro.build.fingerprint` | yes (getprop) | shell | one fingerprint string | none | 1 line | mismatch → stop, re-baseline |
| 2 | Build id / patch level | `adb shell getprop ro.build.id` | yes | shell | one string | none | 1 line | — |
| 3 | Logical display topology (Display 0/1) | `adb shell dumpsys display` | yes (dumpsys) | shell | display list + sizes | none | truncate ≤ 2000 lines | — |
| 4 | Which CarPlay/ExternalDisplay/Navigation processes run | `adb shell ps` | yes | shell | process list | none | ≤ 500 lines | — |
| 5 | Registered services present | `adb shell service list` | yes | shell | service names | none | ≤ 500 lines | — |
| 6 | Window/layer ownership of Display 1 | `adb shell dumpsys SurfaceFlinger` | yes | shell | layer/display info | none | truncate ≤ 3000 lines | redact if personal content |
| 7 | Which process owns the active navigation host | `adb shell dumpsys activity services` (filter to the external-display/navigation packages only) | yes | shell | service records | none | ≤ 1000 lines | — |
| 8 | External display density/size | `adb shell wm size` and `adb shell wm density` | yes | shell | size/density | none | 2 lines | — |

Notes: commands are scoped reads; no `-d`/root flags; no `pull` of proprietary files; no package data. Items 6/7
output is filtered to the components under study and redacted of any personal data before storage.

## Explicitly excluded (NOT in this plan)
`su`, `pm install`/`uninstall`, `mount`, `setprop`, `service call`, `screencap`/`screenrecord` of personal content,
CAN/bus tools, iAP2/CarPlay negotiation, logcat of unrelated apps, any write, any firmware operation.

## Storage & redaction
Raw outputs are stored **private** (encrypted), redacted of identifiers/personal data; only sanitized,
question-scoped summaries would be published. A public-safe receipt records date, scope, and outcome only.

## Why these are necessary
They distinguish competing static hypotheses that the preserved image cannot settle: live-vs-preserved build
identity (1,2), real Display 0/1 topology and ownership (3,6,7,8), and which receiver/navigation/external-display
processes and services are actually active (4,5). Nothing here modifies the vehicle or reads personal data.

## Approval gate
This plan is inert until the owner approves this exact allowlist. Execution, scheduling, and any deviation require
separate explicit authorization and an independent safety check.
