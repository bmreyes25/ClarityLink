# 43T1-R6C — Honda authentication substrate reuse

## Scope and provenance

- Starting main HEAD: `b46af76e0466f93e8cae9ae8c2293b5a692da510` (PR #5 merge, includes R6B `1a1f584`).
- Branch: `architecture/r6c-honda-auth-substrate`; worktree: `/Users/bmreyes24/ClarityLab/clarity-r6c-honda-auth`.
- Preserved `jmcs` SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; proxy SHA-256: `dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66`.
- Honda contacted: **NO**. ADB: **NO**. Vehicle connected: **NO**. Runtime reads: **NONE**. Runtime writes: **NONE**. Proprietary inputs stayed ignored outside this worktree and Git.

## Findings

| Question | R6C finding | Evidence |
|---|---|---|
| USB owner | `jmcs` includes USB host/iAP transport and links `libudev`; exact runtime fd unproven | [iAP2 owner](../research/runtime/r6c-honda-iap2-owner.md) |
| iAP2 owner | `jmcs` contains `ios_iap2`, core, auth and CarPlay attach code | [startup chain](../research/runtime/r6c-carplay-startup-chain.md) |
| MFi/accessory auth owner | `jmcs` coordinates `uwh_ipod_cp` → `os_auth_cp` and iAP2 auth state | [auth owner](../research/runtime/r6c-honda-mfi-auth-owner.md) |
| Auth hardware | Preserved config names `/dev/i2c-2`, slave address `0x10`; `os_auth_cp_obtain` calls config/open/ioctl, and release closes | [auth owner](../research/runtime/r6c-honda-mfi-auth-owner.md) |
| Auth interface/separability | Process-local proxy callback and internal functions; no independent callable factory API established | [auth reuse API](../research/runtime/r6c-auth-reuse-api.md), [proxy](../research/runtime/r6c-libcarplay-proxy-audit.md) |
| CarPlay control owner | `jmcs` AirPlay receiver/session and request/response path | [control owner](../research/runtime/r6c-honda-control-session-owner.md) |
| Authenticated-session handoff | Not identified; auth/iAP2→AirPlay object edge remains open | [handle model](../research/runtime/r6c-honda-session-handle-ownership.md) |
| Screen security | Type110 derives from AirPlay session master context and `streamConnectionID`; source of master context and Type111 relation unresolved | [security link](../research/runtime/r6c-honda-screen-security-session-link.md) |
| Audio reuse | Internal audio callback group and routing visible; independent reuse unknown | [audio](../research/runtime/r6c-stock-audio-reuse.md) |
| Controls reuse | CarPlay/iAP/HID callbacks visible; external event contract unknown | [controls](../research/runtime/r6c-stock-control-reuse.md) |
| Display0 / Display1 | Factory Type110 internal; Display1 admission and Type111 remain unproven | [reuse matrix](../research/runtime/r6c-factory-substrate-reuse-matrix.md) |

## Implementation and decision

`HondaAuthenticationProvider`, `HondaIap2Transport`, and `HondaCarPlaySessionTransport` are clean-room **fail-closed target contracts**. They have no guessed factory binding and report `EVIDENCE_REQUIRED`. `HondaOpaqueContext` models generation, close and non-serialization without secret material. See [adapter map](../research/runtime/r6c-honda-to-r6b-session-adapter-map.md) and [ABI note](../research/runtime/r6c-honda-auth-adapter-abi.md).

- Auth-owner decision: **`R6C_AUTH_INTERNAL_TO_JMCS`**.
- Factory-auth decision: **`R6C_FACTORY_AUTH_REUSE_UNKNOWN`**. The factory hardware path is established statically; independent reuse is not.
- Transport decision: **`R6C_FACTORY_TRANSPORT_PARTIAL`**. In-process stack identified; no export/handoff.
- Selected architecture: **`ARCH_UNKNOWN`**. ARCH_A remains the preferred design, but neither ARCH_A nor ARCH_B has a proven boundary. ARCH_E would exceed the scoped negative evidence.
- Independent Mac MFi for development: **UNKNOWN** availability; a genuine Mac lab authority/service plus control handoff is still needed for real-iPhone work. No extra MFi hardware is included in the desired Honda target. [Strategy](../research/runtime/r6c-auth-development-vs-target-strategy.md).
- Next recommendation: **`GO_FOR_R6D_STATIC_AUTH_CLOSURE`** focused on the `jmcs` iAP2 authenticated state → AirPlay session creation link and whether any supported external API exists.
- Future read-only observation required now: **NO**. Process maps or fd metadata alone would not expose a transferable authenticated channel; no precise one-observation closure plan is justified yet. No run plan was executed or created.

## Verification

Focused adapter tests: 2 passed. Full offline suite: 857 passed, 14 skipped; the self-locator smoke and simulator checks passed. Repository health: 604 Markdown files, 133 indexed reports, 0 broken curated links, 0 forbidden tracked extensions. `git diff --check` passed. The adapter serialization assertion was added after the first full run and is included in the final rerun. Staged-content audit covered all 26 staged paths: Markdown, Python adapter and tests only; no keys, certificates, auth blobs, VIN/MAC, Honda binaries, firmware, or restricted Apple material. No target or real-iPhone test is claimed.

## Top remaining unknowns

1. Exact authenticated iAP2 object to AirPlay control-session transition.
2. Whether a supported external factory auth or session API exists outside reviewed surfaces.
3. Control socket/security-context ownership and transfer semantics.
4. Whether factory audio/controls can remain active with a separate receiver owner.
5. Display1 admission and Type111 security/media behavior on Honda.

R6C investigated reuse of the Honda Clarity's existing USB, iAP2 and MFi/CarPlay authentication substrate so the ClarityLink custom receiver does not need to replace or bypass factory authentication. No authentication secrets were extracted and no Honda runtime or vehicle action occurred.
