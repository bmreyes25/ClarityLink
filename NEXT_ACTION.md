# Next action

**Offline: resolve Honda's config and media payload semantics.** Step 36 proves the 128-byte header, LE32 body length, discriminator byte, plaintext header/body-only AES-CTR boundary, and the type-0 callback path. The envelope parser and CTR state model are implemented. Trace the type-1 CF data property to its consumer and establish whether its body is avcC; then tie the callback's selected 1/2/4-byte record-length mode to exact NAL and complete-access-unit boundaries, timestamp, and keyframe metadata.

Do not use vehicle, ADB, ptrace, firmware patches, live hooks, on-car Type-111, cluster rendering, or unrelated control-plane work. Do not add semantic fields until Honda evidence proves them. See `step-reports/36-prove-screen-wire-format.md`, `research/carplay/honda-screen-header.md`, `honda-screen-crypto.md`, `mc-screenstream-input.md`, and `type111-transport-model.md`.
