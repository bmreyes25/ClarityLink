# 43T1-R6H1 — Gate 1 CPC200/LIVI Link hardware authority bring-up

**R6H merge HEAD:** `6f9234dc08800fc6a3cd05e2971913ebb1cc488c`

**R6H1 starting HEAD:** `6f9234dc08800fc6a3cd05e2971913ebb1cc488c`

**Branch:** `architecture/r6h1-hardware-authority-bringup`

**Worktree:** `clarity-r6h1-hardware`

## Outcome

Safe read-only Mac USB inventory and filtered IOKit metadata searches found no CPC200-CCPA, Carlinkit, or LIVI device. No physical hardware was presented for ownership/revision inspection. In accordance with the hardware gate, hardware work stopped here: no provisioning tool was downloaded or run, no firmware was backed up or written, no auth request was sent, no LIVI app was launched, and no phone session was attempted.

Public LIVI Link docs currently support macOS and specify that its provisioner probes the device, backs up vendor firmware before writing, and provides a documented restore path for i.MX6UL devices. LIVI v9.2.0 is pinned as the candidate toolchain; its named firmware families include i.MX6UL + IW416/RTL8822BS/RTL8822CS. This does not certify an absent retail unit or prove its MFi provenance. Exact hardware compatibility remains untested until the actual unit passes the provisioner's read-only probe. R6H's separate LIVI code patch remains pinned to commit `dcb78854c59ba621f4d327910dc275da386496b4`; LIVI v9.2.0 is four commits ahead, so that patch requires deliberate compatibility review before use with the newer app release.

## Software readiness and ECC

ECC review covered model/device identity evidence, provisioner/source pinning, backup and rollback requirements, wrong-device risk, listener/network containment, private socket ownership, secret handling, logging, no Honda/vehicle scope, and fail-closed stop conditions. Since the unit is absent, device compatibility, power/data stability, ownership, backup, authority and actual firewall containment for LIVI are not inferred.

The existing ClarityLink LIVI adapter/provider and IPC tests passed (`18 passed`); the repository full offline test suite passed (`886 passed, 14 skipped`), repository health passed, and `git diff --check` passed. These establish host software readiness only. They count for none of the real-session tiers. The prior R6H report's LIVI typecheck and 20 focused upstream tests are inherited historical evidence; no LIVI upstream source or executable was run in R6H1.

The macOS firewall is enabled with stealth mode off. Read-only listener inventory found no LIVI/ClarityLink listener; unrelated pre-existing system/development listeners were not changed. No LIVI network interface exists in the observed inventory.

## Decisions

- Hardware: `R6H1_HARDWARE_ABSENT`
- Compatibility: `R6H1_COMPATIBILITY_NOT_TESTED`
- Provisioning: `R6H1_PROVISIONING_NOT_ATTEMPTED`
- Provisioning preflight: `R6H1_PROVISIONING_BLOCKED`
- Genuine authority: `R6H1_AUTHORITY_NOT_TESTED`
- LIVI upstream baseline: `R6H1_LIVI_BASELINE_NOT_REACHED`
- Highest real tier: `BELOW_G1_T0`
- Gate 1 result: `GATE1_BLOCKED_WAITING_FOR_CPC200`
- Gate 1 canonical state: `SOFTWARE_READY_HARDWARE_REQUIRED`
- Gate 2: `NOT_STARTED`
- Next: `GO_FOR_GATE1_HARDWARE_AUTHORITY_BRINGUP`

No Honda, ADB, vehicle, restricted identity, phone data, credentials, or secrets were used. No secret material was extracted or logged. Hardware must be available and pass the published compatibility/provenance/backup gates before any provisioning or real-phone attempt.

See [toolchain baseline](../research/runtime/r6h1-hardware-toolchain-baseline.md), [provisioning preflight](../research/runtime/r6h1-provisioning-preflight.md), [network containment](../research/runtime/r6h1-network-containment.md), and [readiness](../research/runtime/r6h1-gate1-real-readiness.md).
