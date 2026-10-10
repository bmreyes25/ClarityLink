# R7E Test B — display enumeration only

**Plan state:** `BLOCKED_BY_PRIOR_TEST` / `NOT_AUTHORIZED`  
**Risk:** Tier 1, read-only target inventory.  
**Prerequisite:** separately authorized Test A pass; exact diagnostic and output schema established.

**Objective:** Have project-owned API17 code enumerate logical displays and report ID, type, dimensions, API17-exposed refresh information, and validity. The likely Display0/Display1 and observed logical 800×480 dimensions are contextual `HONDA_STATIC` evidence only; the test must independently record what it sees.

**PROPOSED — NOT EXECUTED:** invoke only the audited `--enumerate-displays` diagnostic mode after confirming the artifact hash and foreground process. The literal transport/invocation command is not yet reviewable because Test A artifact and destination do not exist; no placeholder command is treated as executable.

**Write audit:** intended reads are Android display inventory and runtime diagnostics. No file modification, package install, Surface, Presentation, frame, listener, USB/iAP2, or authentication. Process is transient; privilege is least-privilege ordinary app/shell if supported, otherwise stop and re-review. Classification if later performed: `HONDA_READ_ONLY` except any required temporary artifact transfer already authorized under Test A.

**Stop/rollback:** global stop conditions apply. Terminate the diagnostic and verify no process/resource remains; verify normal center UI, cluster, warnings, and audio. Do not proceed to C on a mere second-display listing.

**Success:** candidate secondary display properties are captured with provenance and classified `HONDA_PROTOTYPE_OBSERVED`; this means enumeration only. **Failure:** no candidate, unstable data, or unexpected side effects; stop. **Readiness:** `BLOCKED_BY_PRIOR_TEST`; Test A has not passed and is not authorized.


## R7E1 update

Separate B–D artifact: `claritylink-r7e1-display-diagnostic.apk`, SHA-256 `c92f103b49fae2cfd6aa8863a27448042d282708ffec3f5f5c4000c0e6528f5c`, min/target SDK 17. Explicit mode: `DISPLAY_ENUMERATION`. API17 emulator enumeration passed. Honda package installation and Test B remain `NOT_AUTHORIZED`; package installation mechanism and all prior-test gates remain unresolved. See R7E1 manifest.
