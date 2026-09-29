# Next action

**Offline: finish the exact Honda byte mapping from ProcessFrames through `mc_ScreenStreamProcessData`.** Step 35 recovers the accepted NetSocket read path and AES-CTR screen cipher, but not the plaintext frame header/boundary, VideoConfig message/body, H.264 AU framing, metadata, or concrete sink bytes. Inspect the exact Honda `AES_CTR_Update` call arguments and state lifecycle, then map each callback parse branch to constructed media-buffer bytes/size/timestamp. Keep MHI2's 128-byte/avcC/AVCC contract clearly marked as prior art until Honda evidence matches it.

Do not use vehicle, ADB, ptrace, firmware patches, live hooks, Type-111 handling, cluster rendering, or registry work. Do not add a parser or crypto implementation until Honda byte semantics are supported. See `step-reports/35-screen-framing-and-h264.md`, `research/carplay/honda-screen-framing.md`, `screen-crypto.md`, `honda-video-config.md`, and `honda-h264-format.md`.
