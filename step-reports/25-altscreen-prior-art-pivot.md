# Step 25 — AltScreen prior-art integration and Display-B pivot

**Date:** 2026-09-29  
**Scope:** offline repository/source review and documentation only. No vehicle, ptrace, third-party code copied into project, protocol bytes invented, or Honda code implemented.

## Source review

- Apple WWDC19, [Advances in CarPlay Systems](https://developer.apple.com/videos/play/wwdc2019/252/): official documentation of multiple H.264 streams, cluster map and maneuver-card examples, vehicle-selected cluster content, and the R15 feature requirement.
- `harman-f/mhi2_altscreen_carplay`, commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`: reviewed Type-111 profile/video and native interposer source. Platform-specific MHI2 implementation.
- `shilapi/xcertplay`, commit `3753867f0dd0e5c03490b987fb9df49b8ac96472`: reviewed `AirPlayInfoPlist.kt`, `AirPlaySession.kt`, and `CarPlayMediaEngine.kt`. Source constants and actual descriptor/SETUP dispatch support 110/111, separate UUIDs, `altScreen`, and returned per-stream dataPort.
- `arctus/mib2-carplay-rgi-altscreen`: supplied remote was unavailable/incomplete during checkout; no claims rely on it.

## Findings

1. 110 main / 111 alternate is strongly supported as open/reverse-engineered implementation convention, not an Apple-published numeric guarantee.
2. A separate secondary stream/listener and a per-stream SETUP response port are demonstrated by open receiver implementations. Exact Honda response dictionary field and security-context behavior remain unknown.
3. Modern display structures include many configured properties; legacy minimum requirements are not known. Do not copy xcertplay's whole display dictionary into Honda.
4. Apple Maps cluster map/card behavior is officially documented. Private URL/control schema (`suggestUI`, `showUI`, URL variants) remains open-implementation evidence; Waze automatic cluster selection is unknown.
5. Honda static evidence still shows one initialized main screen, `ScreenCopyMain`, and a singleton proxy callback table. Its ephemeral listener and accepted connection are primary-path facts only. The phone-facing descriptor serialization boundary is not yet proven.
6. A ClarityLink-owned Type-111 receiver/decoder would not need to use the primary `mc_dev_attach` winner by design. But Honda acceptance of an appended descriptor and Type-111 setup request is unproven. Thus registry work moves to fallback status, while the Honda setup/serializer interposition gate becomes critical.
7. Recommended strategy is hybrid: preserve Type 110/Honda flow and potentially add a separately owned Type-111 path if the negotiation boundary is safely extensible. Do not implement yet.

## Required decision gate

```text
SECONDARY STREAM TYPE: 111 (open implementation convention; not Apple numeric guarantee)
ALTSCREEN CAPABILITY: observed `altScreen` token in modern receiver; Honda requirement unknown
SECONDARY SETUP MECHANISM: independent requested stream and setup response in open receiver
SEPARATE DATA PORT: YES in reviewed implementations
HONDA CAN REPRESENT MULTIPLE SCREENS: UNKNOWN; observed path selects main only
HONDA NATIVE ALTSCREEN SUPPORT: UNKNOWN
CLARITYLINK INTERPOSER FEASIBLE: UNKNOWN pending serializer ABI/response evidence
PRIMARY mc_dev_attach REGISTRY STILL BLOCKING: FALLBACK ONLY
RECOMMENDED MEDIA PATH: CLARITYLINK OWNED if Honda negotiation can be extended
CENTER + CLUSTER INDEPENDENT UI: STRUCTURALLY SUPPORTED by Apple model; Honda integration unknown
BIGGEST REMAINING RISK: Honda setup response may not be safely extensible without breaking singleton primary path
RECOMMENDED ARCHITECTURE: HYBRID
READY TO IMPLEMENT DISPLAY-B NEGOTIATION PROTOTYPE: NO for wire behavior; YES for structured fixture only
```

## Updated next action

Offline recover the exact Honda phone-facing descriptor and SETUP response serializer/ABI, then determine whether a narrow stock-delegating wrapper can preserve the primary response while adding one display and its dataPort. Ptrace remains paused and is not required for that analysis.
