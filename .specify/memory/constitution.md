# ClarityLink Constitution

## Authority

`AGENTS.md` and the repository safety policy (including `docs/safety/vehicle-testing.md`) are authoritative. This constitution is a Spec Kit supplement: it restates and narrows those rules for specs, plans, and tasks, and it never overrides, relaxes, or waives them. Any conflict is resolved in favor of `AGENTS.md` and the safety policy.

## Core Principles

### I. Evidence Before Interfaces
No interface, protocol, or contract is specified or implemented on assumption. Every interface claim cites reviewed evidence (decompiled code, documentation, or a captured and approved source). Claims without evidence are recorded as unknown, not guessed.

### II. `safeForHonda()` Remains False (NON-NEGOTIABLE)
`safeForHonda()` stays `false`. Offline permission is never represented as vehicle permission. No spec, plan, or task may set it true or weaken a Honda safety gate.

### III. No Vehicle or Connected-iPhone Operations
No Honda ADB, vehicle access, CAN transmission, installation, firmware or service replacement, or connected-iPhone integration. Work is limited to offline research, synthetic simulation, API 17 emulator work, and separately approved bench-only experiments. Publication and CI never connect to the car.

### IV. No Authentication Bypass or Secrets
No authentication bypass, secret extraction or disclosure, warning suppression, or review/safety-gate bypass. Credentials, signing material, and tokens never appear in files, commands, logs, or commits.

### V. Unknown Interfaces Fail Closed
Unknown or unverified Honda receiver and Display 1 interfaces fail closed: on any unexpected state or exception, behavior reverts to factory. Design target (a goal needing evidence, not a proven property): `CARPLAY_DISCONNECTED => FACTORY_BEHAVIOR_ONLY`.

### VI. Type110 Continuity
Type110 behavior must be preserved. Any change touching Type111 or shared paths needs regression evidence that Type110 is unaffected, and Type111 changes stay reversible.

### VII. Genuine iPhone Evidence Is Never Simulated
Synthetic or simulated data may exercise logic but must be labeled synthetic. It must never be presented as, or substitute for, genuine iPhone evidence. Missing genuine evidence is reported as missing.

### VIII. Tests Run on the Claimed Exact SHA
A unit is "tested" or PASS only if the relevant tests ran on the exact commit or working tree being claimed, with runtime evidence. Mandatory tests are not weakened and are not replaced by static validation or simulation. Failures get root-cause fixes and regression coverage.

### IX. Public/Private Evidence Separation
This repository is public. Raw or derived vehicle data, private Honda evidence, firmware, captures, and identifying material stay outside public Git. Ignored status is not safe storage. Review ignore rules when adding source; verify with `git check-ignore -v` and `git ls-files`.

### X. Protected Publication Workflow and Dirty Work
Use the existing protected-main workflow: feature branch, scoped file lists, `tools/publish_checkpoint.sh`, remote SHA verification, PR, CI and CodeQL. Never push to `main`, force-push, bypass rulesets, or auto-merge Honda, receiver authentication/security, vehicle-control, factory-warning, or `safeForHonda()` changes. Preserve unrelated, untracked, and other sessions' work; never stage repository-wide, reset, or delete worktrees.

## Spec Kit Requirements

- Every spec and plan lists evidence sources, unknowns, and the fail-closed behavior for each unknown.
- Every plan includes a gate check against Principles I-X before design and after.
- Tasks that require runtime proof, genuine iPhone evidence, or independent review state that requirement explicitly; missing review is documented, never fabricated.

## Governance

Amendments must keep this document consistent with `AGENTS.md` and may only tighten, never loosen, its rules. Specs and plans must cite the principle they rely on when granting any exception, and exceptions to Principles II-V are not permitted.

**Version**: 1.0.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
