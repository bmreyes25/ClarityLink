# R5Z ScreenStream transport reconstruction

`HONDA_STATIC`: stock Type110 uses a 128-byte plaintext header, little-endian body length, opcode at byte 4, timestamp field, and body-only AES-CTR when screen security is active. Config and media opcodes flow separately to ScreenStream callbacks. [Framing](../carplay/honda-screen-framing.md), [security](../carplay/honda-screen-crypto.md), [H.264 format](../carplay/honda-h264-format.md).

`CURRENT_IOS_LAB_CONFIRMED`: 43P saw sustained 110 and 111 video, distinct connected data ports, and PlayPort's modern ChaCha classification. It did not preserve a privacy-cleared raw prefix or isolate codec. [43P](../lab/current-ios-type111-observation.md).

`EXTERNAL_PRIOR_ART`: legacy MHI2 and WirelessCarPlay describe per-screen AES context; modern xcertplay describes ChaCha sealed screen frames. These differ in security generation. No Honda Type111 branch is known. The host `media.py` parser implements the bounded Honda Type110 envelope family solely as a Type111 **lab framing hypothesis**. It rejects unknown opcodes, zero/oversized lengths, EOF, and timeouts. It does not select or infer a cipher.

Open questions: shared header details beyond 128 bytes, negotiated legacy compatibility, capability-driven cipher choice, Type111 frame protection/integrity and H.264 configuration are `UNKNOWN`. Closure requires a lawful Type111 clear/metadata vector with source context or a documented receiver implementation for the exact security generation; see [gap map](r5z-honda-integration-gap-map.md).
