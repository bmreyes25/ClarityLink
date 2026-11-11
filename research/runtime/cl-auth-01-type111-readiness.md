# CL-AUTH-01 Type111 authentication readiness

Base `origin/main` `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792`. Offline, synthetic and source-level work only. No vehicle, Honda, hardware or iPhone activity occurred, and `safeForHonda() == false`. Synthetic proof is never real authentication.

## Evidence classes (never merged into one PASS)

| # | Class | State |
|---|---|---|
| 1 | Synthetic Type111 security | `TESTED_SYNTHETIC` (this campaign) |
| 2 | Authorized receiver authentication | Not reached: `AUTHORIZED_HARDWARE_REQUIRED` |
| 3 | Real iPhone Type111 negotiation | Not reached: `REAL_IPHONE_REQUIRED` |
| 4 | Genuine Type111 protected media | Not reached; key derivation `UNKNOWN` |
| 5 | Android API17 compatibility | Out of scope here; not touched |
| 6 | Honda factory integration | `HONDA_TARGET_REQUIRED`; adapters fail closed |
| 7 | Vehicle safety acceptance | Not started; `safeForHonda() == false` |

## Readiness matrix

| Area | Code status | Test evidence | Real proof | Blocker |
|---|---|---|---|---|
| Provider selection | `select_provider` always fails closed; no adapter is installed. | `test_r6e_auth_transport` | None | A reviewed adapter |
| Genuine authority | `LiviAuthority` plus `LabAuthenticationProvider`. Handoffs now carry a derived `TrustClass`. `ATTESTED` is unreachable because the verifier allowlist is empty. | `test_cl_auth_01_provenance` | None | No attestation contract; hardware absent |
| Authenticated handoff | Single use, generation bound, non-serializable, close callbacks revoke the receiver generation, optional `SessionLedger`. | `test_cl_auth_01_provenance`, `test_r6e` | None | Hardware |
| LIVI IPC | Same-UID AF_UNIX, framed JSON, bounded, UUID request IDs, replay rejection, one outstanding request. Bodyless requests now accepted. Wire protocol checked against the recorded patch. | `test_r6h_livi_ipc`, `test_cl_auth_01_livi_readiness` | None | Patch targets removed upstream code; hardware |
| `/info` lifecycle | One `/info` per session, required before SETUP, exact request/response pairing in `LabSessionTransport`. | `test_cl_auth_01_provenance` | None | Real phone |
| Type111 SETUP | Parse, duplicate-ID rejection, once-only serializer, rollback, receiver-level listener and security ownership. | `test_type111_setup_contract`, `test_receiver_lab`, `test_cl_auth_01_type111_security` | None | Real phone |
| Stream ownership | Per-generation stream identity; Type111 failure leaves Type110 and the parent session intact. Parent loss revokes dependents. | `test_cl_auth_01_type111_security`, `test_cl_factory_02_dual_stream_isolation` | None | Real session |
| Security-profile selection | A stream's provider comes only from a parent-owned `Type111SecurityGrant`. Only a source-registered profile builds. Unknown profile, `LEGACY_AES` (no provider) and a non-synthetic grant without an attested parent are denied. | `test_cl_auth_01_type111_security` | None | Real profile evidence |
| Type111 KDF/context | None. `EvidenceRequiredSecurity` denies. The Honda Type110 KDF model is kept isolated. | `test_unknown_type111_framing_and_security_fail_closed` | None | `UNKNOWN`; needs real session evidence |
| Protected media | `ModernChaChaScreenSecurity` AEAD with a nonce counter. Synthetic keys only. Replay, tag failure, truncation, oversize and counter exhaustion tested. | `test_cl_auth_01_type111_security` | None | Real profile evidence |
| VideoConfig | AVCC parsed; replacement and malformed handling tested. **Config frames bypass the security provider (opcode 1 is not unprotected).** Whether real config frames are sealed is `UNKNOWN`. | `test_cl_auth_01_type111_security`, `test_media_pipeline` | None | Real session evidence |
| Decode handoff | Host H.264 decode gated on generation/listener/decoder identity. | `test_receiver_lab`, `test_cl_auth_01_type111_security` | None | Real frames |
| Teardown/reconnect | Idempotent, concurrent-safe, no leaks over repeated cycles; consumed grants cannot be reused. | `test_cl_auth_01_*` | None | None for software |
| First real iPhone session | Runbook T0-T8 written, not executed. | n/a | None | Hardware, seam, approval |
| Honda integration | Adapters fail closed. Not touched. | `test_honda_display_boundary_gate` | None | Honda target; separate authorization |

## The ten questions

1. **Complete authentication code:** provider protocol and fail-closed selection, handoff claim/close/non-serialization, replay provider, bounded transport validation, LIVI provider and AF_UNIX IPC with synthetic peers, Type111 SETUP and lifecycle models, ChaCha AEAD provider.
2. **Implemented in CL-AUTH-01:** derived `TrustClass` and `attest_handoff` (always denies today); synthetic-authority gate in `ReceiverSession`; parent-loss revocation through handoff close callbacks; `SessionLedger`; request/response pairing; `Type111SecurityGrant` and `HandoffSecurityFactory`; bodyless-request acceptance in the LIVI bridge; bridge/patch drift guards. 82 new tests (suite 1526 -> 1608 passed, 29 skipped).
3. **Software-incomplete:** no reviewed attestation verifier or contract (by design); the LIVI delegate seam for the current upstream Rust core; real Type111 key derivation and profile; whether VideoConfig must be authenticated.
4. **Needs authorized hardware:** T0, any `ATTESTED` handoff, LIVI Link firmware compatibility.
5. **Needs a real iPhone:** T1-T8, `/info` field evidence, whether Type111 is requested, the real security profile and frame format.
6. **Needs the Honda:** factory-session sharing, Type110 continuity, Display 1 and cluster admission, warning priority, restoration.
7. **Providers that could satisfy the first gate:** a user-owned genuine CPC200-CCPA provisioned as LIVI Link with a reviewed control delegate, once the seam exists for the current upstream. An Apple MFi-licensed accessory path is the other legitimate route and was not assessed. No other documented, licensed alternative was identified.
8. **Synthetic-only paths:** `ReplayAuthenticationProvider`, `SYNTHETIC_BRIDGE`, `ClearLabSecurity`, any grant with `synthetic=True`, and all test peers.
9. **Earliest verifiable real event:** T0, genuine authority initialized. Next is T2, a real control request reaching ClarityLink through the delegate.
10. **Highest-value next action:** resolve the delegate-seam gap, since the recorded patch no longer matches upstream. Decide between re-pinning to `v9.2.0` with a firmware-compatibility check and designing a seam for the Rust core. Then obtain the verified authority hardware under written approval.

## Residual risk register

- A same-UID process can claim `authenticated` on the LIVI socket. Trust stays `UNVERIFIED_HARDWARE`.
- Python cannot zero all key copies: `release_key` returns `bytes` that persist until collected. Documented limit.
- `Receiver.security_factory` remains an open lab hook for callers that set it directly. `ReceiverSession` installs a grant factory only when none is set. Production wiring must not pass a bare factory.
- Two authority concepts coexist (`auth.py` receiver-owned `MODEL_ONLY` session and the `authentication.py` handoff). The receiver's evidence string is fixed to `MODEL_ONLY`, so it cannot be mistaken for real authentication. Not consolidated.
- No independent security review (see the gap matrix).
