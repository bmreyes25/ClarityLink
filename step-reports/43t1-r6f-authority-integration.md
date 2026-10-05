# 43T1-R6F — authentication authority selection and complete Mac receiver Gate 1

Date: 2026-10-05. R6E PR #9 merged at `9ab9d77a00d85b361342804cad6de41df732653e`. R6F Starting HEAD: `9ab9d77a00d85b361342804cad6de41df732653e`. Branch: `architecture/r6f-authority-integration`. Worktree: `/Users/bmreyes24/ClarityLab/clarity-r6f-authority`.

## Decision

- Authority decision: **`R6F_AUTHORITY_SELECTED_ACQUISITION_REQUIRED`**.
- Integration decision: **`R6F_ACQUISITION_REQUIRED`**.
- Primary acquisition target: a user-owned, authentic **Carlinkit CPC200-CCPA**, hardware revision confirmed compatible by the LIVI Link provisioner, used with the public **LIVI Link + LIVI macOS receiver stack**. Current online listings were about USD $65 (sale price) and AUD $94.95; plan USD $65–$100 plus tax/shipping and verify stock, source, MFi provenance, revision and return terms before purchase.
- Classification: combined LIVI runtime + LIVI Link is a `CARPLAY_SESSION_OWNER` candidate. CPC200-CCPA alone is only the MFi/radio endpoint. The ClarityLink `CARPLAY_CONTROL_SESSION_PROVIDER` handoff is not implemented or documented yet.
- Backup: none. OCBM's adapter-owned session does not expose the phone-facing `/info`/SETUP control channel to ClarityLink. xcertplay remains signer-only / Mac-host-incomplete.
- Provider: no real provider was fabricated or integrated. R6E's fail-closed boundary remains. Once hardware is acquired, a narrow LIVI session/control adapter must be implemented under `auth_providers/` and provide the single authenticated handoff to `ReceiverSession`.

The exact purchase, provisioning, host connection, API gap, and first test are in [the acquisition specification](../research/runtime/r6f-authority-acquisition-specification.md). Local inventory found no USB authority, receiver accessory, configured service, or receiver CLI. Public documentation supports LIVI's genuine-coprocessor requirement, Mac support, and LIVI Link network authentication; it does not prove any specific retail unit's provenance, expose a stable ClarityLink control API, or establish Type111. The [candidate matrix](../research/runtime/r6f-authority-candidate-matrix.md), [selection decision](../research/runtime/r6f-authority-selection-decision.md), [inventory](../research/runtime/r6f-local-authority-inventory.md), and [third-party review](../research/runtime/r6f-third-party-dependency-review.md) preserve the evidence and limitations.

## Real-iPhone result

- Real-iOS decision: **`R6F_REAL_IOS_NOT_REACHED`**.
- Highest tier: **`BELOW_R6F_T0`**.
- `/info` received / sent / accepted: NO / NO / NO.
- SETUP received / Type110 observed / Type111 observed: NO / NO / NO.
- Authenticated handoff/control transport: no physical authority or real session; no real handoff.
- No real-iPhone observation file was created because no session occurred. Synthetic results count toward none of R6F-T0 through T9.

## Readiness and tooling

`/info` builder shape and evidence are audited in [R6F info readiness](../research/runtime/r6f-info-readiness.md). The R6F lab CLI is [tools/r6f_carplay_lab.py](../../tools/r6f_carplay_lab.py), with `inventory`, `preflight`, `authority-check`, `info-only`, `serve`, and `shutdown` modes. Real serving remains fail-closed while authority/provider/control handoff are absent. The cumulative [Mac readiness matrix](../research/runtime/r6f-mac-receiver-readiness.md) and [R6F–R6J roadmap](../research/runtime/r6f-complete-mac-receiver-roadmap.md) set the next real gates.

R6G recommendation: **`GO_FOR_R6G_AUTHORITY_BRINGUP`**. The selected target is concrete; R6G should acquire/verify the unit and establish the genuine authority path and ClarityLink control handoff, then immediately pursue real `/info`, SETUP, and Type111 milestones. No generic authority-model milestone should repeat.

## ECC security review

ECC review covered provider trust, authorization state, exception containment, nonserializable private handoff state, repr/log redaction, generation/stale-session handling, bounded request parsing, loopback-only default preflight, finite timeouts, single ownership, idempotent close, dependency license/source, and firmware provisioning risk. The R6F tests extend provider lifecycle/redaction checks and preserve the 100-cycle synthetic lifecycle test. Synthetic provider tests validate interface behavior only; they do not establish lawful authority or real authentication. No authority secrets, keys, certificates, auth blobs, pairing material, private captures, Honda binaries or firmware were added. Honda contacted: NO; ADB used: NO; vehicle connected: NO; restricted identity used: NO; secrets extracted/logged: NO.

## Verification

Focused provider/transport conformance: **16 passed** when run with R6E transport tests; dedicated 100-cycle test: **passed** (100 synthetic generations, closes to zero sessions). Full `PYTHON=.venv/bin/python ./tools/run_tests.sh`: **873 passed, 14 skipped**, self-locator smoke **3 passed**, simulator checks passed. `tools/check_repo_health.py`: **passed**, 633 Markdown files, 136 indexed reports, 0 broken curated links, 0 forbidden tracked extensions. `git diff --check`: passed. Offline CI and CodeQL exact-head results will be recorded after pushing the implementation head and opening the PR.
