# CL-AUTH-01 LIVI upstream currency check

Checked 2026-10-21 against public GitHub metadata for `f-io/LIVI` (licence GPL-3.0). No LIVI code was built or run, and no hardware, phone or authentication exchange was involved.

## Findings

| Item | Result | Evidence class |
|---|---|---|
| Recorded pin `dcb78854c59ba621f4d327910dc275da386496b4` | Exists upstream (commit dated 2026-10-04). | SOURCE_VERIFIED_EXTERNAL |
| Patch `0001-control-delegate-dispatch-and-bounds.patch` | SHA-256 matches [`r6h-livi-patch-contract.md`](r6h-livi-patch-contract.md). It modifies only TypeScript files under `src/main/services/projection/driver/cp/`. | Local |
| `cpStack.ts`, `CpSession.ts` (the patched seam) | Present at the pin and at `v9.2.0`. **Absent at `v9.3.0`, `v9.4.0` and `main`.** Upstream commit `c2c7d4aad5` (2026-10-06, "LIVI runs on a Rust core") rewrote every file the patch touches. | SOURCE_VERIFIED_EXTERNAL |
| Current upstream CarPlay control path | Rust workspace under `native/` (for example `livi-helperd/bin/livi-core/src/carplay.rs`, `crates/livi-cp`, `crates/iap2-mfi`). No delegate hook was reviewed. | UNKNOWN |
| Latest release | `v9.4.0` (2026-10-10). Its notes say a LIVI Link dongle needs the latest firmware via OTA. | SOURCE_VERIFIED_EXTERNAL |

## Consequences

- The recorded patch applies only to the `v9.2.0`-era TypeScript stack. It does not apply to current releases. R6H/R6H1 evidence remains valid for the pinned revision only.
- ClarityLink's Python bridge (`auth_providers/livi_ipc.py`) is aligned with the patch's client: protocol version, 1,400,000-byte frame bound, proof string, plist content type, and the 4/3/8/7-field hello, ready, request and response frames. `tests/jmcs/test_cl_auth_01_livi_readiness.py` fails if either side drifts.
- Running the pinned `v9.2.0` stack against dongle firmware that has since been updated may not be supported. Compatibility between the pinned software and the current OTA firmware is UNKNOWN and must be re-established before any hardware step.
- A real delegate seam in the Rust core must be designed and reviewed separately. That is new upstream-facing work and is not attempted here. Any patch carries GPL-3.0 obligations for the modified LIVI source.
- The synthetic `SYNTHETIC_BRIDGE` and the Unix-socket bridge test peers prove only ClarityLink's side of the contract.

## Software defect fixed in M4

A bodyless request (empty request body with no content type, such as a plain `GET /info`) was rejected by `_decode_control_plist` as a malformed plist, which closed the bridge. An empty body now decodes to an empty mapping. Non-empty malformed plists and wrong content types are still rejected (`test_cl_auth_01_livi_readiness.py`). It is not known whether a real iPhone sends a bodyless `/info`, so this change is defensive and is not evidence of phone behavior.

## Unchanged residual risk

The bridge's `authenticated` hello is a constant proof string sent by a same-user local process. It cannot be verified by ClarityLink, so a LIVI handoff is classified `UNVERIFIED_HARDWARE` and never `ATTESTED`.
