# Type111 bounded first-bytes oracle — 43T1-PREP2

**Decision: `TYPE111_ORACLE_OFFLINE_READY`.** Pure structural classifier: `classify_type111_prefix` in `src/claritylink-honda/prep2_runtime.py`.

## Bound and outputs

Maximum accepted prefix is 256 bytes; invalid attempts to enlarge the bound return `UNSUPPORTED`. It parses no bytes into media, has no I/O, and never returns decrypted content. It checks the known Honda Type110 128-byte envelope family only as a candidate: LE32 declared body length, discriminator byte at offset 4, and the statically observed opcode set. Zero/oversized length, impossible zero opcode, inconsistent length, truncation, and unsupported values are explicit non-success results. The 16 MiB body threshold is a local guard, not Honda's bound (Honda's inspected allocation path has no pre-allocation maximum).

The existing tests synthesize a structural Type110-shaped header and label its source context; they do not contain a raw Honda packet capture. The sanitized 43P oracle events record that the separate PlayPort parser classified Type110 and Type111 bodies as `MODERN_CHACHA_SCREEN`, but the tracked capture contains metadata/event summaries, not a raw bounded first-byte fixture. PlayPort's 128-byte screen framing shares a family with Honda Type110, so header shape alone cannot identify AES versus ChaCha. A source-tagged PlayPort fixture is consequently returned as `CLEAR_OR_UNKNOWN` with `header_not_crypto_discriminator`; it is not relabeled as Honda evidence.

No crypto branch is selected. AES-then-ChaCha fallback is prohibited. Unknown or unsupported bytes imply close and retire the Type111 generation. No media, key, identity, private capture, or raw first-byte data is committed.

**Fixture boundary:** the repository has no privacy-cleared raw prefix sample for either Honda Type110 or the modern 43P/PlayPort capture. The structure tests are synthetic. This is an evidence limit, not unfinished oracle logic: do not reconstruct a “known” packet from redacted metadata, and do not guess a crypto branch from a shared header. The first real Honda Type111 prefix, framing, security mode, KDF, nonce/counter and integrity behavior remain `HONDA_UNKNOWN` until separately observed and reviewed.
