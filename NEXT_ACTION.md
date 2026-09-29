# Next action

**Offline: close the remaining Honda stream/display identity gap.** Step 33 proves Type-110 `streamConnectionID` is a uint64 request field used for screen AES key/IV derivation and that the same setup branch allocates a listener and returns its `dataPort`. It does not show a persistent ID-to-socket mapping or a relationship between the `/info` numeric display `uuid` and a SETUP stream. Recover the Screen UUID property's backing type/source and trace the accepted socket/listener owner; in parallel, inspect pinned prior-art history for versioned Type-111 request/security fields and feature-token requirements.

Keep this offline. Do not use vehicle, ADB, ptrace, firmware patches, live hooks, Type-111 handling, or decoder/rendering. Do not resume `mc_dev_attach` registry work. See `step-reports/33-stream-connection-binding.md`, `research/carplay/stream-connection-id.md`, and `research/carplay/display-stream-correlation.md`.
