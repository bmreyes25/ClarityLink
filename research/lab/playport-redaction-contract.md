# PlayPort oracle redaction contract

The opt-in `OracleDiagnostics` sink serializes only JSON events whose metadata keys are in a fixed allowlist. It is disabled unless `--type111-diagnostics` is present. Unsupported keys, including key-shaped names such as `session_key` and `aes_key`, are dropped before serialization.

Allowed observations are protocol shape and non-secret values: phases and event names; display type/UUID/dimensions/FPS/features/view-area presence/initial map URL; feature names when decoded as a string list; descriptor key names; stream type; connection-ID presence and equality-derived distinctness; response keys/type/dataPort; listener/socket lifecycle; codec/config/frame sizes; keyframe classification; framing category; control verb; target UUID presence; and a coarse parser protection branch. URL values are restricted to `maps:/` paths and queries/fragments are stripped. Key/feature names are character-filtered, length-limited, and capped.

The raw `streamConnectionID` is used only in memory to compare the two screen IDs. No raw ID, hash, packet body, media payload, key, IV, nonce, certificate, authentication challenge/signature, pairing record, or session material is emitted. Socket peer addresses and browser access tokens are not oracle fields.

The `security_mode` value reports the PlayPort parser branch that handled the observed frame. It is not a portable protocol claim, and `CLEAR_OR_UNKNOWN` does not distinguish clear media from a short/malformed body. A real 43P record must preserve this limitation and must not infer Honda security behavior.

Metadata values are currently generated from bounded protocol fields in the pinned PlayPort code. Adding a field requires adding its key deliberately to `SAFE_KEYS`, a redaction test, and a documentation update. Diagnostics failures must not affect stream processing; recording is opt-in and wrapped by the logging implementation's ordinary logger boundary.
