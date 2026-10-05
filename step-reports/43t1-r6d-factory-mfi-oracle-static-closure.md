# 43T1-R6D factory MFi oracle static closure

## Scope and provenance

Starting main HEAD: `6d0c798f8b1f9821d0b7532a203266ab585db727` (merged PR #6). Branch: `architecture/r6d-factory-mfi-oracle`. Worktree: `../clarity-r6d-mfi`. Preserved `jmcs` SHA256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Honda contacted: NO. ADB: NO. Vehicle: NO. Runtime reads: 0. Runtime writes: 0. I²C operations: 0. Static analysis and host tests only. The user-described R6C1 patch was not available locally, so its inert architecture was implemented from the description.

## Result

The [call graph](../research/runtime/r6d-honda-mfi-oracle-callgraph.md) connects AirPlay MFi-SAP certificate/signature requests through `libcarplay_proxy.so` callbacks to `uwh_ipod_cp_*`, then `os_auth_cp_*`, then the configured factory I²C channel. The same lower primitive serves iAP2 accessory authentication. [Operation semantics](../research/runtime/r6d-honda-mfi-oracle-semantics.md) support acquire, certificate, challenge/signature, readiness and release. The configured value `0x10` reaches Linux `I2C_SLAVE` unshifted, so it is a 7-bit address in the preserved code path. The implementation uses a singleton fd and process mutex; external concurrent use is unknown.

The static oracle primitive is sufficiently established to choose **`ARCH_D_FULL_CLARITYLINK_RECEIVER_WITH_FACTORY_AUTH_ORACLE` as the target architecture**. This is not a successful Honda adapter or real-iPhone result. The host `MfiAuthOracle`, inert `HondaFactoryMfiOracle`, `SyntheticMfiOracle` and `AccessoryAuthenticator` model ownership and rollback without I²C, Honda operations or real credentials. The old R6B full-session provider remains fail-closed. No private key, certificate, signature, real challenge or Honda binary was added to Git.

## Decisions

- Honda oracle: `R6D_FACTORY_MFI_ORACLE_CONFIRMED_STATIC` (operation family and shared path; external-use ABI and runtime still open).
- Sharing: `R6D_AUTH_PRIMITIVE_SHARED` (static iAP2/AirPlay lower primitive).
- Address: `R6D_HONDA_I2C_ADDRESS_7BIT_CONFIRMED` (configured code path).
- Architecture: `ARCH_D_FULL_CLARITYLINK_RECEIVER_WITH_FACTORY_AUTH_ORACLE` as target candidate.
- Next: `GO_FOR_R6E_CUSTOM_IAP2_AUTH_STACK`; host iAP2/AirPlay orchestration is the first receiver-level gap, alongside offline Honda ABI/lifecycle refinement. No target operation is authorized.

## Limits and verification

Protocol-major mapping, reset, detailed error codes, cross-process locking, device permission and ClarityLink's wire-compatible iAP2/AirPlay authentication remain open. The factory screen key belongs to AirPlay receiver-session state; the chip-to-screen security relationship beyond MFi-SAP is not established. Mac development still needs a separate lawful authentication source to test a real iPhone. Type110/Type111 real media and Display0/Display1 target output remain unproved. [Readiness](../research/runtime/r6d-factory-oracle-readiness.md) distinguishes static findings from models. Focused tests: 8 passed. Full offline suite: 863 passed, 14 skipped, standard-library smoke and simulator checks passed. Repository health: passed. Oracle boundary check: passed. CI and CodeQL are checked on the final PR HEAD.
