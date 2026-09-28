# Step 5 — Protocol and cluster map-region evidence

**Status: offline review complete; practical live evidence remains open.** ClarityLink targets a separate CarPlay map display inside the existing instrument-cluster navigation region while the center display remains independently usable.

## Cluster geometry and Honda render path

The exact factory Navigation destination rectangle remains unknown. Saved evidence establishes Android built-in and HDMI logical displays at 800×480. Honda Hack mirrors into the cluster over the HDMI path, but its `(0,24,584,191)` coordinates are local to a 584×215 layout and do not establish the underlying factory surface or native cluster bounds.

The next step is parked, read-only ADB diagnostics of framebuffer/sysfs, Android display services, and bounded Honda display components. If those do not reveal enough geometry, use an identified read-only frame and a matched normal Navigation view/photo. Do not read a framebuffer until the target and byte count are verified.

## CarPlay second-display/session evidence

Static `jmcs` evidence configures one main CarPlay screen and has a separate AirPlay receiver display-info path. The raw iAP2 Identification bytes, display/session descriptor, UUID, and second-display negotiation are unknown. Before considering a USB analyzer, check existing read-only USB-monitor support, tools, and targeted runtime logs after ADB is available.

## Practical Step 6 gate

Step 6 remains **not ready**. It may proceed when evidence is sufficient to define:

1. The second CarPlay display size and session identity.
2. The Honda rendering surface/path and cluster Navigation destination rectangle.
3. A reversible binding with rollback and fail-clear behavior that preserves all stock cluster UI and center CarPlay use.

Perfect knowledge of unrelated panel specifications is not required. See `step-reports/05b-display-diagnostics.md` for the current parked-access gate.
