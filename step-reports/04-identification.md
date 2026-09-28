# Step 4 — CarPlay Identification/display advertisement

**Status: static primary-screen model reconstructed.** No Identification bytes were decoded, and the report deliberately leaves packet-level claims unknown.

## Result

The inspected `jmcs` initialization at VA `0xaff09` creates/configures/registers one Honda `gMainScreen`. The receiver's display-info copy path at VA `0x287ae1` calls `ScreenCopyMain` at `0x287b0c`, selecting the main screen. Copied `j_config.xml` configures 800×480, 30 FPS, high-fidelity touch; it separately states 153×92 mm under `System/Display`. The singleton screen callback in `libcarplay_proxy.so` remains another obstacle to forwarding a second display.

The static source does not provide a packet capture or raw iAP2 Identification component list. It also does not establish the live UUID value, view/safe-area fields, or a second cluster descriptor. The structured field-by-field model, hashes, source paths, confidence, and unknowns are in [`research/carplay-identification-model.md`](../research/carplay-identification-model.md).

## What this completes—and what it does not

This completes the requested **static** reconstruction for the available primary-screen configuration and identifies the exact next protocol evidence needed. It does not complete a wire-accurate iAP2 Identification packet reconstruction. The saved snapshots cannot supply bytes that they never recorded; that requires a future reviewed capture method that sees the iAP2 accessory-identification exchange. No identification/configuration values were changed.
