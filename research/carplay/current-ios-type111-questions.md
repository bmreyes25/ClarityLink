# Current iOS Type111 oracle questions

These questions are reserved for Step 43P. Step 43O built the lab offline and did not use an iPhone. The separately scoped 43P run may use PlayPort's documented shared experimental identity, classified `EXPERIMENTAL_LAB_ONLY`; this does not make it a trusted, production, or Honda credential.

1. Does this iOS build request any `altScreenURLs`, and which non-secret URL values?
2. Which SETUP feature proposal and response tokens appear, and does `altScreen` survive?
3. Does the phone automatically request stream type 111 after the secondary display is advertised? Record exact order relative to 110 without making ordering an assumption.
4. Which Type111 descriptor keys appear? Is `streamConnectionID` present, and does it differ from Type110? Record only presence and a redacted correlation result.
5. Does the phone open a second connection to the returned Type111 data port?
6. Can Type110 remain active through Type111 stop, teardown, and restart?
7. What codec/config and screen framing are observed, and which protection branch does the selected PlayPort build actually process?
8. How do UUID-scoped `forceKeyFrame`, `showUI`, `stopUI`, and `suggestUI` behave?

Capture only allowlisted protocol metadata. Do not record authentication bodies, certificates, private keys, pairing secrets, challenges/signatures, AES/ChaCha/DataStream keys, IVs/nonces, bearer tokens, or decrypted media. Keep the experimental identity outside both repositories with restrictive permissions; never include it in committed files or capture artifacts. This 43P-only exception does not change Honda or production credential policy.

The pinned PlayPort's current `ScreenStream` parser uses 128-byte framing and a ChaCha20-Poly1305 frame path. That is a property of this receiver implementation, not evidence of Honda compatibility. The legacy AES per-screen design remains strong `EXTERNAL_PRIOR_ART`; Honda Type111 remains `HONDA_UNKNOWN`.
