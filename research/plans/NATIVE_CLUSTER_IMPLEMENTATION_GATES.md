# Native CarPlay cluster-map implementation gates

**Target:** keep normal CarPlay and spoken directions on the center unit while Apple Maps provides an independent map view in the Clarity's compass/Navigation region, even when Music is foreground on the center screen. This is standard CarPlay secondary-display work; CarPlay Ultra and spatial audio are outside this plan. No safety-critical display, bus, control, gauge, or warning interface is an implementation target.

## What the September 25 session settled

- Honda Hack casting is an actual center-screen mirror. The cluster changed from mirrored Apple Maps to mirrored Music when Music came forward. It preserved spoken guidance, but it does not meet the independent-map target.
- Android exposes a separate 800×480 HDMI display. Cast-on physical photos show a wide central rectangle below the speed readout and above the Menu/trip row; speed and range stay visible, but its sides crowd the power/charge scales. The exact safe rectangle within that video path still needs measurement against those photos before a custom renderer.
- Two `OMX.Nvidia.h264.decode` instances produced 28 800×480 output frames each in 1973 ms with EOS. This establishes a useful concurrent-decode prerequisite under one 15 fps fixture. The strict 30-frame probe criterion did not pass, and CarPlay coexistence was not tested.
- The kernel has `CONFIG_USB_MON` unset, so a built-in usbmon trace cannot yield raw iAP2 Identification bytes. ADB process maps/fds were permission denied. Packet-level capabilities remain unknown.
- Android Waze installed on the head unit supplies a positive control for semantic cluster guidance: its 300-foot arrow remained on HDMI when Honda Home replaced Waze on the center, then cleared to compass when the route ended. The physical cluster showed the arrow/distance but no road name. Honda Hack's live `enable_custom_meter=false` branch feeds the factory external-display handler messages 5601/5602/5603. This proves the cluster renderer can operate independently of the center image, not that iPhone CarPlay supplies maneuver metadata.
- The factory 5601–5603 start/turn layouts do not draw their stored road string. `TurnByTurnController` maps ordinary events to view IDs 61441/61442, while only special 61445/E2 renders `getAndroidAutRoadName()`. Reusing the proven path alone would fail Goal 1's street-name requirement. A bounded custom navigation view or a dedicated CarPlay map view is required for it.
- Connecting the Mac to the head unit by USB did not enumerate a device in macOS or add a wired ADB transport. Wi-Fi ADB continued to work. That connection did not expose iAP2 packets.

See [the session evidence](../captures/20260925T150706Z-SESSION_FINDINGS.md), [the Waze positive control](../captures/20260925-WAZE_HEADUNIT_FINDINGS.md), and [the receiver audit](../native/receiver-multidisplay-audit.md).

## Gate 1 — receiver protocol truth, offline first

**Question:** what does this build advertise in iAP2 Identification, and what does its CarPlay session separately advertise/set up for screen streams? These are distinct payloads. Do not infer either from `turn_by_turn` resource-ownership logs.

1. On copied firmware, trace `mc_carplay_app_init`, `screen_add_props`, `AirPlayReceiverSessionScreen_CopyDisplaysInfo`, and the iAP2 identification builder into an explicit, versioned capability model. Record each field with symbol/offset and confidence; mark opaque fields unknown.
2. Build a Mac-side harness that serializes the reconstructed current one-screen model and a proposed two-screen model into inspectable events. Use Apple public sessions for behavior boundaries, but do not invent private numeric fields from presentation slides.
3. For byte-level confirmation, choose a separately reviewed transparent inline USB analyzer or another independently verified non-mutating capture method. Do not remount/load kernel modules or inject into the running receiver simply to obtain packets. If no safe method is available, leave the packet verdict unknown and keep receiver work offline.

**Exit:** observed payload bytes or a clearly labeled static-only model; separate answers for Route Guidance metadata and multi-display stream setup. A missing debug log is not a negative packet result.

## Gate 2 — faithful offline receiver/display twin

Use the [casting replay](../simulator/sample-live-casting-20260925.jsonl) and [head-unit Waze replay](../simulator/sample-waze-headunit-20260925.jsonl) as two distinct current-behavior oracles. Extend the simulator with two identified logical CarPlay streams, center/cluster decoder events, display-1 composition bounded to the NE region, independent route lifecycle, and an unchanged audio observation. Feed it captured frames and labeled protocol events. Test app switch Maps → Music, route end, disconnect, dropped frames, stale guidance, decoder failure, and rollback. Head-unit Waze, iPhone Waze, and Apple Maps need separate fixtures and pass criteria.

**Exit:** a deterministic Mac replay that distinguishes actual Honda mirroring from a proposed independent map. The current simulator's hypothetical cluster channel is a contract test, not receiver proof.

## Gate 3 — decoder and rendering engineering

Explain the two missing output frames in the diagnostic fixture before setting a throughput threshold. Instrument output timestamps and frame hashes in a new **offline** build; don't reinterpret 28/30 as a complete pass. Then design a background-safe decoder measurement for coexistence with the factory center CarPlay decoder, with an exact future parked run/rollback card.

Prototype an Android API-17 renderer against mock H.264 frames and a display-1 surface contract. Keep the composited image inside the verified navigation region and make it disappear on route end, disconnect, stale frame, or renderer failure. Do not call `ITBTInformation` setters because they can emit B-CAN traffic.

**Exit:** bench timing/memory measurements and a reviewable renderer package/contract; no on-car receiver patch yet.

## Gate 4 — choose receiver path

The copied `jmcs` registers one `gMainScreen`, `CopyDisplaysInfo` selects main, and `libcarplay_proxy.so` has a singleton screen callback. A configuration bit alone cannot create a second independent display. Choose a candidate only after Gate 1:

- **Compatible vendor receiver update**, if a verified MY16ADA-compatible build exists. Verify signatures, dependencies, version, and recovery before considering it.
- **Local receiver extension** in a copied/isolated build: add distinct display identities and negotiated view/safe areas, per-stream callback dispatch, a second decode/render sink, and independent lifecycle. Preserve main-screen and audio ABI. Produce a byte-level diff, tests, failure modes, and a boot-recovery plan before any vehicle change.
- **Route Guidance metadata branch** if actual iAP2 metadata is observed but a second video stream remains unavailable. Render Honda-drawn maneuvers in a display-only UI. This is native guidance, but it is not the requested iPhone-rendered map.

The screenshot/OCR bridge remains an interim experiment only: the September 25 Music capture proves it loses the Maps source when the center changes apps.

## Gate 5 — staged vehicle validation, only after a complete reversible artifact

First validate a standalone display-1 renderer with synthetic frames and visual bounds while parked. Then validate receiver negotiation, independent cluster map across center app changes, voice guidance, route end/disconnect clearing, and rollback. Stop on warnings, covered indicators, CarPlay audio loss, or instability. Each on-car change needs exact files/packages, hashes, affected startup state, a restore method that works if the UI fails to boot, and explicit approval for that reviewed artifact. The verified original backup is never edited.

**Definition of done:** Apple Maps remains in the physical NE Navigation region while Music is on the center display; both are iPhone-driven independent views; voice guidance works; the map clears cleanly; speed, range, telltales, and warning areas remain untouched; the change can be removed and the pre-change behavior restored. Waze is a separate acceptance run rather than an assumed consequence.
