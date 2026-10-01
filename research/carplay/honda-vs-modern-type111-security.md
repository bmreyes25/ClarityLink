# Honda Type110 vs modern external Type111 security — Step 43N

## Evidence split

| Stack | Evidence and behavior |
|---|---|
| Honda Type110 | **HONDA_CONFIRMED** from hash-matched `jmcs` (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) and [Honda Screen crypto audit](honda-screen-crypto.md): 128-byte ScreenStream framing; session master material plus unsigned decimal `streamConnectionID` feed the recovered SHA-512 screen key/IV routine; protected body bytes use continuous AES-CTR state; header is not encrypted. |
| DiPlay / PlayPort current screen path | **EXTERNAL_PRIOR_ART** at DiPlay `f2d06951b4e8114dbb62f551c12a32a845a3042f` and PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`: authenticated session shared secret plus `streamConnectionID`, DataStream-specific HKDF labels, 32-byte key, and ChaCha20-Poly1305 frame body, with an 8-byte frame counter nonce. |
| Honda Type111 | **HONDA_UNKNOWN**. No Honda-local Type111 security path has been proven. The Type110 function's use of stream connection ID does not prove that Type111 is accepted or that its security is identical. |

## Safety rule

Do not port the current DiPlay/PlayPort DataStream KDF, ChaCha20-Poly1305, labels, nonce rules, or framing behavior into Honda. The shared 128-byte header family is not evidence of cipher compatibility. ClarityLink should first preserve Honda's authenticated session and established Type110 behavior, then prove whether a second stream can reuse Honda-compatible semantics or needs some other Honda-specific path. No live keys or packet captures are included here.
