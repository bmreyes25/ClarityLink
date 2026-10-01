# Honda Type110 vs modern external Type111 security — Step 43N

## Evidence split

| Stack | Evidence and behavior |
|---|---|
| Honda Type110 | **HONDA_CONFIRMED** from hash-matched `jmcs` (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) and [Honda Screen crypto audit](honda-screen-crypto.md): 128-byte ScreenStream framing; session master material plus unsigned decimal `streamConnectionID` feed the recovered SHA-512 screen key/IV routine; protected body bytes use continuous AES-CTR state; header is not encrypted. |
| DiPlay / PlayPort current screen path | **EXTERNAL_PRIOR_ART** at DiPlay `f2d06951b4e8114dbb62f551c12a32a845a3042f` and PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`: authenticated session shared secret plus `streamConnectionID`, DataStream-specific HKDF labels, 32-byte key, and ChaCha20-Poly1305 frame body, with an 8-byte frame counter nonce. |
| Honda Type111 | **HONDA_UNKNOWN**. No Honda-local Type111 security path has been proven. The Type110 function's use of stream connection ID does not prove that Type111 is accepted or that its security is identical. |

## Safety rule

Do not port the current DiPlay/PlayPort DataStream KDF, ChaCha20-Poly1305, labels, nonce rules, or framing behavior into Honda. The shared 128-byte header family is not evidence of cipher compatibility. ClarityLink should first preserve Honda's authenticated session and established Type110 behavior, then prove whether a second stream can reuse Honda-compatible semantics or needs some other Honda-specific path. No live keys or packet captures are included here.

## xcertplay third reference

Pinned xcertplay `17c92439413638dfd1d7f91d7e1c2e7358398762` also describes a 128-byte screen header, clear VideoConfig, and ChaCha20-Poly1305 VideoFrame bodies using a DataStream output key and frame counter. Its media key path salts DataStream HKDF with `streamConnectionID`. This corroborates the modern implementation family represented in DiPlay/PlayPort, whose source ancestry overlaps; it is not a Honda Type111 security result. Classifications remain: **XCERTPLAY screen security: EXTERNAL_PRIOR_ART / modern receiver; Honda Type110: HONDA_CONFIRMED legacy AES-CTR; Honda Type111: HONDA_UNKNOWN.** See [pinned xcertplay differential](xcertplay-type111-differential.md) and the [four-way comparison](honda-xcertplay-diplay-playport-differential.md).

Protocol features that recur externally—types 110/111, separate stream IDs/listeners, and the 128-byte framing family—are only candidate invariants across receiver generations. Encryption, key labels, nonce/counter policy, HEVC, and detailed frame protection remain generation-specific until Honda evidence says otherwise.

## Legacy AES-era Type111 cross-reference

Pinned MHI2 documentation for an AirPlay 210.81-era receiver describes its project Type111 screen using the same stock `AirPlay_DeriveAESKeySHA512ForScreen` primitive with the established session AES material and the Type111 stream's own `streamConnectionID`, followed by its own `AES_CTR_Init/Update/Final` context. The pinned `45clouds/WirelessCarPlay` source also reads `streamConnectionID` from the screen descriptor and passes it with `aesSessionKey` to that screen KDF on its legacy non-PairVerify path. That source has a separate modern PairVerify/ChaCha path. Together these are strong `EXTERNAL_PRIOR_ART` for a per-screen legacy AES model, but they do not establish Honda Type111 behavior. The Honda conclusion is now **LEGACY_PER_SCREEN_KDF_STRONGLY_SUPPORTED; HONDA ABI/STATE VALIDATION REQUIRED**, with Type111 still `HONDA_UNKNOWN`. See [legacy AES Type111 cross-reference](legacy-aes-type111-cross-reference.md).
