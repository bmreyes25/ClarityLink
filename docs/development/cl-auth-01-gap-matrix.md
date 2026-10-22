# CL-AUTH-01 implementation gap matrix

Base: `origin/main` `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792`. Baseline offline suite on that commit: 1526 passed, 29 skipped. Evidence is source-level and synthetic only. No Honda, vehicle, hardware, or live-iPhone activity occurred, and `safeForHonda() == false`.

Classifications: `IMPLEMENTED_OFFLINE`, `TESTED_SYNTHETIC`, `SOURCE_VERIFIED_EXTERNAL`, `AUTHORIZED_HARDWARE_REQUIRED`, `REAL_IPHONE_REQUIRED`, `HONDA_TARGET_REQUIRED`, `UNKNOWN`, `UNSUPPORTED`. A missing real-world proof is not a software defect.

## Defects found by the source audit

| ID | Finding | Location | Severity | Action |
|---|---|---|---|---|
| D1 | A `SYNTHETIC_BRIDGE` LIVI handoff is built as `AUTHENTICATED_LAB`, `authenticated=True`, `authority_type=GENUINE_MFI_COPROCESSOR`. Only the `real_livi_bridge` capability differs, and nothing consumes it. A synthetic bridge is therefore indistinguishable from real authority to `ReceiverSession`. | `auth_providers/livi.py` `LiviAuthority.open` | High (trust promotion) | Add a derived trust class on the handoff; reject synthetic trust by default in `ReceiverSession`. |
| D2 | `AuthenticatedSessionHandoff` accepts any `authenticated=True` plus any `AuthorityType` from the caller, and `explicitly_authorized` is a caller-set Boolean. There is no provenance level above "caller said so". | `authentication.py` | High | Trust class: constructor can never produce `ATTESTED`; promotion requires a verifier from a source-controlled allowlist (empty). |
| D3 | `handoff.security_context` is never consumed. `Receiver.security_factory` accepts any callable and never checks profile, session, generation or stream binding. | `session.py`, `receiver.py` `setup` | Medium | Single-use, generation/stream/session-bound security grant; unknown profile denies. |
| D4 | `LabSessionTransport` does not enforce one-outstanding-request pairing. A response can be written with no request, or twice. The LIVI bridge enforces this, but the generic transport does not. | `session_transport.py` | Medium | Enforce exact pairing in the transport. |
| D5 | Closing the parent handoff does not revoke the Receiver generation unless the control loop is next polled. Media for an already-open Type111 stream can continue after authority loss. | `session.py`, `authentication.py` | Medium | Close callbacks from handoff to `ReceiverSession` to receiver teardown. |
| D6 | No reconnect guard against a repeated session identifier across providers or restarts. | `session.py` | Low | Optional `SessionLedger`. |
| D7 | The LIVI Unix-socket hello is a constant proof string, so any same-UID process can self-assert authentication. UID peer-check is the only gate. This is inherent to the delegate design and cannot be fixed offline. | `livi_ipc.py` | Residual | Classify as `UNVERIFIED_HARDWARE`, never `ATTESTED`; document. |
| N1 | Two parallel authority concepts exist: `auth.py` (receiver-owned `MODEL_ONLY` session) and `authentication.py` (handoff). They are redundant but not contradictory, because the receiver evidence string is fixed to `MODEL_ONLY`. | `auth.py`, `receiver.py` | Info | Do not consolidate; document. |

## Component matrix

| Component | Source | Existing implementation | Evidence class | Existing tests | Missing behavior | Offline-solvable | External dependency | Risk | Action | State |
|---|---|---|---|---|---|---|---|---|---|---|
| Authentication provider protocol, `LabAuthenticationProvider` | `jmcs/authentication.py` | Fail-closed wrapper; verifies the handoff matches the authority; sanitized errors | TESTED_SYNTHETIC | `test_r6e_auth_transport`, `test_r6f_provider_conformance` | Provenance above caller-asserted (D2) | Yes | None | High | M2 | Partial |
| Provider selection | `auth_providers/__init__.py` | Always raises `authorized_provider_adapter_unavailable` | IMPLEMENTED_OFFLINE | `test_r6e_auth_transport` | None; fail-closed by design | n/a | A reviewed adapter | Low | Keep | Complete |
| Hardware and service adapter slots | `auth_providers/hardware.py`, `authorized_service.py` | `discover()` raises | IMPLEMENTED_OFFLINE | indirect | A real adapter | No | AUTHORIZED_HARDWARE_REQUIRED | Low | None | Stub by design |
| Handoff claim, close, non-serializable | `authentication.py` | Single use, generation bound, redacted repr, pickling blocked | TESTED_SYNTHETIC | `test_r6e`, `test_r6b` | Close callbacks (D5) | Yes | None | Medium | M2 | Partial |
| Replay provider | `authentication.py` | `SYNTHETIC` origin, cannot authenticate | TESTED_SYNTHETIC | `test_replay_never_promoted_to_live` | None | n/a | None | Low | Keep | Complete |
| Session transport | `session_transport.py` | Bounded validation, generation check | TESTED_SYNTHETIC | `test_r6e`, `test_r6f` | Request/response pairing (D4) | Yes | None | Medium | M2 | Partial |
| ReceiverSession | `session.py` | Provider, handoff, transport, receiver; `/info` then SETUP ordering | TESTED_SYNTHETIC | `test_r6e`, `test_r6h_livi_ipc` | Synthetic-trust gate (D1), security binding (D3), revocation (D5), ledger (D6) | Yes | None | High | M2, M3 | Partial |
| LIVI authority and transport | `auth_providers/livi.py` | Requires an authenticated bridge and an explicit-authorization Boolean | TESTED_SYNTHETIC | `test_r6g_livi_provider` | Synthetic bridge labelled genuine (D1) | Yes | Genuine CPC200 | High | M2, M4 | Partial |
| LIVI AF_UNIX IPC | `auth_providers/livi_ipc.py` | Same-UID peer check, 0700 directory, framing limits, UUID request IDs, replay rejection, one outstanding request, duplicate-key rejection, redacted repr | TESTED_SYNTHETIC | `test_r6h_livi_ipc` | Authentication assertion is self-asserted (D7) | Partly | AUTHORIZED_HARDWARE_REQUIRED | Medium | Document; trust stays unverified | Partial |
| LIVI upstream patch and pin | `third_party/patches`, `research/runtime/r6g-*`, `r6h-*` | Patch and pinned commit recorded | SOURCE_VERIFIED_EXTERNAL (R6G/R6H) | `test_r6h_livi_ipc` | Execution against real LIVI with hardware | No | AUTHORIZED_HARDWARE_REQUIRED | Medium | M4 re-check | Needs hardware |
| Type111 SETUP parse and contract | `negotiation/type111_setup_contract.py` | Duplicate-ID rejection, once-only serializer, rollback | TESTED_SYNTHETIC | `test_type111_setup_contract` | Real Honda serializer | Done | HONDA_TARGET_REQUIRED | Medium | Keep | Synthetic complete |
| Receiver SETUP and stream ownership | `jmcs/receiver.py` `setup` | Per-generation listeners, security, decoder; preserves Type110 on Type111 failure | TESTED_SYNTHETIC | `test_receiver_lab`, `test_r6_receiver_promotion` | Profile-gated security (D3) | Yes | None | Medium | M3 | Partial |
| Type111 lifecycle twin | `negotiation/lifecycle.py`; tests `transport/test_type111_lifecycle_twin.py` | Generation, teardown, parent destroy | TESTED_SYNTHETIC | twin tests | Duplicate lifecycle models (twin vs receiver) are intentionally separate; no change | n/a | None | Low | Keep | Complete |
| Security providers | `jmcs/security.py` | Clear (lab), evidence-required (deny), Modern ChaCha AEAD with counter | TESTED_SYNTHETIC | `test_r6_receiver_promotion` | Counter exhaustion, replay and tag-failure counter tests | Yes | None | Medium | M3 tests | Partial |
| `SessionSecurityContext` | `jmcs/security.py` | Metadata only; `unprotect` always denies | IMPLEMENTED_OFFLINE | `test_r6_receiver_promotion` | None; deny-by-default | n/a | Real key derivation | Low | Keep | Complete |
| Type110 KDF model | `negotiation/screen_kdf.py` | Honda Type110 SHA-512 model | SOURCE_VERIFIED_EXTERNAL (static) | KDF tests | Type111 use unknown | n/a | UNKNOWN | Medium | Keep isolated | Type110 only |
| Type111 KDF and security context | none | `EvidenceRequiredSecurity` denies | UNKNOWN | `test_unknown_type111_framing_and_security_fail_closed` | Real derivation | No | REAL_IPHONE_REQUIRED, HONDA_TARGET_REQUIRED | High | Keep evidence-required | Blocked |
| Protected-media parser and AES-CTR model | `transport/screen_parser.py`, `crypto_model.py`, `receiver_core.py` | Type110 framing, continuous CTR | TESTED_SYNTHETIC | transport tests | Type111 profile unknown | n/a | REAL_IPHONE_REQUIRED | Medium | Keep | Type110 only |
| VideoConfig | `transport/video_config.py`, `receiver.py` | AVCC parse; opcode 1 | TESTED_SYNTHETIC | `test_media_pipeline` | Mid-stream change and replace tests | Yes | None | Low | M3 tests | Partial |
| Frame gate | `transport/frame_gate.py` | Generation, sequence, timestamp ordering | TESTED_SYNTHETIC | `test_frame_gate` | None | n/a | None | Low | Keep | Complete |
| Real authenticated session (T0–T5) | none | none | AUTHORIZED_HARDWARE_REQUIRED, REAL_IPHONE_REQUIRED | none | A genuine authority | No | CPC200-CCPA, LIVI Link, iPhone | n/a | Runbook (M6) | Not reached |
| Honda session reuse, Display 1, cluster admission | none | Adapters fail closed | HONDA_TARGET_REQUIRED | `test_honda_display_boundary_gate` | Everything | No | Honda target | Critical | Do not touch | Out of scope |

## Smallest change set

1. `authentication.py`: trust class, attestation gate, close callbacks, session ledger.
2. `auth_providers/livi.py`: synthetic trust for `SYNTHETIC_BRIDGE`, unverified-hardware trust for the real bridge.
3. `session_transport.py`: request/response pairing.
4. `session.py`: synthetic gate, revocation, ledger, grant wiring.
5. `security.py`: `Type111SecurityGrant`, `HandoffSecurityFactory`.
6. Tests for each, plus the 24 negative cases (existing coverage mapped in the readiness document).

Redundant or contradictory lifecycle code (N1, twin vs receiver) is documented but intentionally not consolidated.
