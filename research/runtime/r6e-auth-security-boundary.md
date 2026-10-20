# R6E authentication and security boundary

Apple's [accessory security description](https://support.apple.com/guide/security/verifying-accessories-sec70a4f377d/web) is the governing public model: genuine authorized IC/service owns authentication; CarPlay media protection is session-bound. R6E implements no MFi signer, private certificate path, recovered identity, phone patch, verification bypass or Honda credential reuse.

ECC security review: provider selection fails closed; handoff rejects missing authenticated state, stale/duplicate claims and mismatched channel identity; replay is visibly synthetic; structured input has byte/depth/array/string caps; unknown requests fail closed; close is idempotent and releases opaque context. Trace uses an allowlist and omits raw peer and authority identifiers. Lab binding defaults to loopback; no wildcard listener is enabled. New runtime dependencies: none. Project prior-art licenses are documented in authority selection and no external source is copied.

Residual boundary: no genuine authority API is installed or verified; provider-specific wire parser, real TLS/RTSP framing, current-iOS /info compatibility and private-interface exposure need review when an authorized authority is connected. Test doubles never prove physical authentication.
