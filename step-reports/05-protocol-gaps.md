# Step 5 — Protocol and cluster map-region evidence

**Status: offline review complete; practical live evidence remains open.** ClarityLink targets a separate CarPlay map display inside the existing instrument-cluster navigation region while the center display remains independently usable.

## Cluster geometry and Honda render path

The exact factory Navigation destination rectangle remains unknown. Saved evidence establishes Android built-in and HDMI logical displays at 800×480. Honda Hack mirrors into the cluster over the HDMI path, but its `(0,24,584,191)` coordinates are local to a 584×215 layout and do not establish the underlying factory surface or native cluster bounds.

Parked, read-only ADB diagnostics are now collected. Android display 1 is the 800×480 HDMI output; `fb1`/`tegradc.1` is the likely matching framebuffer. Its BPP reports zero, so its raw format/size remain unverified. `screencap -d 1` provides a read-only output capture path. Next capture one display-1 frame only after the user shows the normal factory Navigation page with casting off and replies READY. This frame can validate what reaches HDMI; a matched straight-on photo may be needed to derive physical map bounds. Do not read the raw framebuffer until its format and byte size are proven.

## CarPlay second-display/session evidence

Static `jmcs` evidence configures one main CarPlay screen and has a separate AirPlay receiver display-info path. The raw iAP2 Identification bytes, display/session descriptor, UUID, and second-display negotiation are unknown. Read-only USB-monitor and log checks are complete: usbmon is not available, and the filtered live logs expose connection/authentication policy but no payload bytes or screen descriptor. A hardware analyzer is likely needed for raw USB traffic, but no purchase is recommended while the separate descriptor transport is still unknown.

## Practical Step 6 gate

Step 6 remains **not ready**. It may proceed when evidence is sufficient to define:

1. The second CarPlay display size and session identity.
2. The Honda rendering surface/path and cluster Navigation destination rectangle.
3. A reversible binding with rollback and fail-clear behavior that preserves all stock cluster UI and center CarPlay use.

Perfect knowledge of unrelated panel specifications is not required. See `step-reports/05b-display-diagnostics.md` for the current parked-access gate.
