# R5Z Type111 screen security design

Honda Type110: `HONDA_STATIC` nonzero stream ID plus 16-byte established session master material enters `AirPlay_DeriveAESKeySHA512ForScreen`; two salted SHA-512 results supply AES-CTR key/IV and `SetSecurityInfo` installs a persistent screen context. This is established only for stock Type110. [Static evidence](../carplay/honda-screen-crypto.md).

43P current iOS delivered both screen streams to PlayPort under its modern ChaCha path (`CURRENT_IOS_LAB_CONFIRMED` for that session). [43P observation](../lab/current-ios-type111-observation.md). Legacy AES Type111 reuse is `EXTERNAL_PRIOR_ART`, not Honda confirmation. Header form alone does not distinguish AES from ChaCha. [First-byte oracle](../carplay/type111-first-bytes-oracle.md).

`ScreenSecurityProvider` has open, unprotect and close operations. `EvidenceRequiredSecurity` is the production-default failure boundary: it never accepts encrypted Type111. `ClearLabSecurity` is opt-in and accepts only locally generated clear H.264 fixtures; it is not a CarPlay security implementation. No keys, IVs, derivation, MFi authentication, fallback cipher detection, or private Apple code is in R5Z.

To replace it, obtain lawful, privacy-cleared current Type111 framing/nonce/integrity evidence, the negotiated security-generation decision, and an authorized established-session security context. Require known-answer vectors and independent lifecycle tests before enabling encrypted input. The code waiting is `security.py` and the media handoff in `receiver.py`.
