# Step 43P authentication and preflight

**Date:** 2026-10-01  
**Status:** Authentication handling and software preflight passed; live iPhone session not yet started.  
**Evidence class:** Authentication source `EXPERIMENTAL_LAB_ONLY`; no Honda evidence.

## Authentication source

For the bounded 43P Mac/iPhone observation, the user authorized PlayPort's documented experimental DiPlay identity. The source was the official DiPlay v0.2.6 release APK. Its published SHA-256 was verified before extracting only `assets/offline-mfi/identity.pk8` and `assets/offline-mfi/certificate.p7b`. No key or certificate contents were printed, logged, or added to either repository.

The identity files reside in an owner-only directory outside both repositories. Directories are mode `0700`; files are mode `0600`. PlayPort accesses the external directory through an ignored `identity/offline-mfi` symlink. Git confirms that link is ignored and the PlayPort working tree remains clean. PlayPort's `MfiIdentityTest` passed both tests with zero skips, including the local certificate/key signing check. This establishes local pair consistency only; it does not establish Apple certification, iPhone acceptance, or Honda compatibility. The identity is shared, extractable, experimental, and not suitable as a trusted or production credential.

## Preflight results

- ClarityLink focused ELF tests: **8 passed**.
- ClarityLink focused oracle/redaction tests: **41 passed**.
- ClarityLink full suite: **301 passed, 4 skipped**; configured offline checks passed.
- PlayPort `MfiIdentityTest`: **2 passed, 0 skipped**.
- PlayPort Gradle build: **passed**.
- PlayPort web tests and production build: **passed**.
- Diagnostics remain opt-in and allowlist-based; the existing synthetic diagnostics tests passed, including unknown secret-field rejection and Type111 lifecycle isolation.
- No phone session, Honda access, or capture artifact was created during this preflight.

## Gate

Authentication handling and software checks are ready. The live session remains pending final device/network checks: confirm no Honda ADB target, confirm the PlayPort listener will bind only to the intended lab interface, confirm the viewer port is available, and confirm the phone can use the intended Wi-Fi network. Only after those checks pass may one observational baseline session begin. Stop if any gate is unresolved. Do not start Step 43Q until a sanitized 43P trace has been collected and reviewed.

## Provenance

- [Official DiPlay v0.2.6 release](https://github.com/shihabal3amri/DiPlay/releases/tag/v0.2.6)
- [DiPlay third-party notices](https://github.com/shihabal3amri/DiPlay/blob/main/docs/THIRD_PARTY_NOTICES.md)
- [PlayPort oracle plan and handling gate](../research/lab/playport-type111-oracle-plan.md#43p-authentication-source-and-handling-gate)
