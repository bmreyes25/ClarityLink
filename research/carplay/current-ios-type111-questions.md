# Current iOS Type111 oracle questions — Step 43P results

Step 43P produced a sanitized live lab trace. Findings below apply only to the observed PlayPort profile and are classified `CURRENT_IOS_LAB_CONFIRMED`; the iPhone model and iOS build were not retained. The shared PlayPort identity is `EXPERIMENTAL_LAB_ONLY`, not a trusted, production, or Honda credential. See the [43P report](../../step-reports/43p-current-ios-type111-oracle.md) and [capture summary](../lab/captures/43p/session-summary.json).

1. **`altScreenURLs`:** request key present; sanitized advertised values empty.
2. **Features:** the canonical session requested `altScreen`; enabled features were `iAPChannel`, `viewAreas`, and `altScreen`.
3. **Type111/order:** Type111 was requested and set up before Type110.
4. **Descriptor/identity:** Type111 `streamConnectionID` was present and the redacted comparison found it distinct from Type110.
5. **Second endpoint:** Type111 received its own dataPort and its socket connected.
6. **Type110 coexistence:** Type110 remained active while Type111 delivered sustained video. Type111-only stop/restart was not tested; server shutdown stopped both streams.
7. **Media:** VideoConfig and frames arrived on both streams. Codec is unknown because no codec value was retained. The active PlayPort parser classified both streams `MODERN_CHACHA_SCREEN`.
8. **Controls:** four `suggestUI` events; `forceKeyFrame`, `showUI`, and `stopUI` were not observed. No control experiment was performed.

Two session setups appeared in the source append log; the later one is the canonical committed trace, and the earlier one is disclosed in the 43P report. The initial feature proposal included `hevc`; the later one did not. No receiver profile setting was intentionally changed.

Only allowlisted protocol metadata is committed. Authentication bodies, certificates, private keys, pairing secrets, challenges/signatures, AES/ChaCha/DataStream keys, IVs/nonces, bearer tokens, Wi-Fi credentials, and decrypted media are excluded. The experimental identity stays outside both repositories. This 43P-only exception does not change Honda or production credential policy.

The pinned PlayPort's current `ScreenStream` parser uses 128-byte framing and a ChaCha20-Poly1305 frame path; the 43P capture observed that branch on both streams. That is a property of this receiver implementation, not evidence of Honda compatibility. The legacy AES per-screen design remains strong `EXTERNAL_PRIOR_ART`; Honda Type111 remains `HONDA_UNKNOWN`.
