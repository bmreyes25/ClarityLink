# R6D Honda oracle operation semantics

| Abstract operation | Honda evidence | Inputs / outputs and ownership | Confidence / oracle mapping |
|---|---|---|---|
| Acquire/release | `uwh_ipod_cp_obtain/release` → `os_auth_cp_obtain/release` | singleton device fd; mutex held across operation | `HONDA_STATIC_CONFIRMED`; YES, exclusive lifecycle |
| Protocol/version | `uwh_ipod_cp_get_auth_level` → `os_auth_cp_read` | value read; mapping to public protocol major unproved | `PARTIAL`; UNKNOWN |
| Certificate length/body | `uwh_ipod_cp_get_certificate_len/get_certificate`; `APSMFiPlatform_CopyCertificate` | caller-sized buffer; obtained device released afterward | `HONDA_STATIC_CONFIRMED`; YES |
| Submit challenge | `uwh_ipod_cp_set_challenge` → `os_auth_cp_write` | bytes and length; AirPlay wrapper bounds length to 20 bytes | `HONDA_STATIC_CONFIRMED`; YES |
| Status/poll | `uwh_ipod_cp_signature_ready`; `os_auth_cp_ready` reads device status | poll loop in AirPlay platform wrapper | `HONDA_STATIC_CONFIRMED`; YES |
| Signature length/body | `uwh_ipod_cp_get_signature_len/get_signature`; `APSMFiPlatform_CreateSignature` | allocated output, freed by caller; release on success/failure | `HONDA_STATIC_CONFIRMED`; YES |
| Reset | `uwh_ipod_cp_reset` symbol and `os_auth_cp_reset` call family | precise trigger and hardware effects need closure | `PARTIAL`; UNKNOWN |

`os_auth_cp_read` writes a selector before the read; `os_auth_cp_write` packages selector and payload. Register values are deliberately omitted. Honda-specific error values, sleep/wake and the public protocol-version correspondence remain unresolved. The clean-room contract models acquire, certificate, sign and release; `protocol_major()` stays fail-closed for Honda.
