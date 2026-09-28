# Step 5 — Resolve protocol and geometry gaps

**Status: complete for the offline evidence gate; both proof gaps remain and their minimum read-only observations are specified.** No Step 6 work or live car capture was started.

## Task A — factory Navigation safe area

**Exact factory rectangle: unresolved.** The static allowlist establishes only two related coordinate spaces: primary Android display `(0,0,800,480)` and Honda Hack's local cast image `(0,24,584,191)` within its `(0,0,584,215)` layout. No OEM safe-area rectangle, crop/scissor bounds, or transform between those spaces was found in the targeted Navigation/ExternalDisplay code, config/resources, cluster wrappers, or `disp_com_meter` evidence. The detailed candidate ledger and confidence labels are in [`research/navigation-safe-area.md`](../research/navigation-safe-area.md).

The smallest missing observation is a paired, read-only HDMI/display-1 frame and perpendicular full-cluster image while the OEM Navigation page is active with Honda Hack casting off. If the OEM page is composed by a separate meter controller, a read-only native page-layout/framebuffer snapshot from that controller will be required instead. The cast rectangle is explicitly excluded as proof.

## Task B — iAP2 Identification

**Raw packet: not reconstructed.** `jmcs` contains iAP2 Identification state names and accessory-info/XML routines. Separately, its AirPlay receiver's `AirPlayReceiverSessionScreen_CopyDisplaysInfo` path builds display/session information from the main screen. Static config values cannot supply missing packet bytes, parameter IDs/order, UUID, or encryption/framing. The exact capture boundary and privacy-scoped plan are in [`research/iap2-identification.md`](../research/iap2-identification.md): passive USB capture before iPhone reconnect through Identification Accepted, plus a separately identified passive session-control capture if the screen descriptor does not travel over the captured USB link.

## Step 6 gate

```text
SAFE_AREA_READY_FOR_STEP_6: NO
IDENTIFICATION_READY_FOR_STEP_6: NO
STEP_6_READY: NO
```

Blockers: (1) factory Navigation bounds are not measured in native panel coordinates, and (2) no raw iAP2 Identification exchange or subsequent display-session descriptor capture exists. Step 6 was not started. No car/USB capture, vehicle writes, or changes to firmware/backups occurred.
