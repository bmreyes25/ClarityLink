# 43T1-R6G — LIVI authority bring-up and control-session adapter

## Canonical result — 2026-10-05

| Field | Value |
|---|---|
| R6F merge HEAD | `7fadb23b2fa599a82207ae22a2f1fc2e1a6757ee` (PR #11 merge) |
| R6G starting HEAD | `7fadb23b2fa599a82207ae22a2f1fc2e1a6757ee` |
| Branch | `architecture/r6g-livi-authority-bringup` |
| Hardware | `R6G_HARDWARE_ABSENT` (no selected CPC200 product identified) |
| LIVI seam | `R6G_LIVI_CONTROL_DELEGATION_SMALL_PATCH` |
| Authority | `R6G_AUTHORITY_NOT_TESTED` |
| Adapter | `R6G_LIVI_ADAPTER_PARTIAL` |
| Real iOS | `R6G_REAL_IOS_NOT_REACHED` |
| Highest tier | `BELOW_R6G_T0` |
| Next | `GO_FOR_R6H_LIVI_ADAPTER_COMPLETION` |

R6F PR #11 was verified at its requested exact head `e3488ed018ef4ee5d72e59800deae99cd3628aa7`, base `main`, open and mergeable with Offline CI and CodeQL passing. It was merged before R6G began. R6G worktree began cleanly from merge HEAD `7fadb23b2fa599a82207ae22a2f1fc2e1a6757ee`.

## Work completed

- Read-only Mac USB inventory did not identify the selected CPC200/LIVI authority; no VID/PID or hardware revision is claimed.
- Reviewed public upstream LIVI at exact commit `dcb78854c59ba621f4d327910dc275da386496b4`; GPL-3.0-or-later, no source copied. `CpStack.attachSocket` owns control parsing, dispatch, serialization, socket write and teardown. `/info` and SETUP currently dispatch directly to private handlers. `CpHelperSock` exposes helper/MFi signer calls but not the RTSP control channel.
- Located a narrow pre-dispatch seam before `CpStack._handle`. A small upstream `ControlSessionDelegate` patch can preserve LIVI's transport/auth/session ownership and allow one ClarityLink `/info`/SETUP owner. Stock SETUP side effects must be suppressed when delegated.
- Added `auth_providers/livi.py` against the existing R6E authority/handoff/transport contracts. It fails closed unless explicitly authorized and given a matching authenticated bridge. The actual LIVI bridge/provider factory is not implemented in upstream and remains required; the provider is therefore `PARTIAL`, not ready or live-integrated.
- Added lifecycle and 100-cycle synthetic contract tests. These prove only ClarityLink object lifecycle, bounds and error containment; they do not establish genuine authentication, LIVI integration, or iPhone progress.
- Added pinned source baseline, source architecture map, seam classification, upstream adapter design, failure attribution and receiver readiness documents.

## R6G real-iPhone ladder

No physical authority was present. No real-iPhone attempt was made and no network receiver was opened. `/info` received/sent/accepted: no. SETUP/Type110/Type111: not observed. Highest real tier remains `BELOW_R6G_T0`.

## Safety / provenance

No Honda, ADB, vehicle, Honda credential, recovered/shared MFi identity, authentication bypass, or private secret was used or logged. No private capture was created. No stock firmware was backed up or modified. No LIVI Link provisioning occurred.

## Remaining blockers

1. Implement and test the small LIVI pre-dispatch `ControlSessionDelegate`, including the process bridge needed to feed the Python provider and exclusive `/info`/SETUP ownership.
2. Obtain and verify a user-owned compatible CPC200-CCPA revision and genuine MFi coprocessor; then provision only through the documented LIVI Link path after rollback review.
3. Validate unmodified/upstream LIVI with a real iPhone, then validate ClarityLink handoff and real `/info` on one continuous session.
