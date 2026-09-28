# Step 7 — Second CarPlay display/session model

**Status: PARTIAL; true Display B negotiation is not ready to implement.** All work in this report is offline. No vehicle or iPhone test was performed.

## Findings

- The Honda primary path is statically configured as one `gMainScreen`: `mc_carplay_app_init` creates it, adds config properties, and registers it. `AirPlayReceiverSessionScreen_CopyDisplaysInfo` calls `ScreenCopyMain`, which obtains registry entry 0; the observed path does not enumerate all displays.
- The generic receiver registry is an array and generic `ScreenStream` lifecycle code increments a stream counter. This is partial generic capability, not evidence of two advertised screens or two independently dispatched sessions.
- Honda `libcarplay_proxy.so` has one global screen callback table and rejects a second registration. No second descriptor, role, UUID, setup response, video/session ID, content assignment, or decoder destination was recovered.
- The configured primary values are 800×480, up to 30 FPS, hifi touch, and 153×92 mm under `System/Display`. They are local config values; they do not prove wire fields or live negotiated values.
- `_ScreenThread` calls `AirPlayReceiverSessionScreen_StartSession` at VA `0x2883a9`; this identifies a receiver-side session start site but not its wire request/transport or its binding to a video stream.
- H.264 handling and ScreenStream lifecycle symbols exist, but the phone response-to-stream-to-Android-surface chain is incomplete.

## Offline model

Added `src/carplay-session-model/model.py` and tests. It models the configured primary display and a candidate cluster Display B using the known 800×480 Android output canvas. UUID/session/stream IDs, B's role encoding/capabilities, independent content assignment, and wire bytes remain explicit unknowns. Deterministic JSON is a research fixture only, not protocol serialization.

## Decision table

| Gate | Result |
|---|---|
| Primary display model | PARTIAL — configured fields recovered; UUID and wire encoding unknown |
| Multi-display support in Honda stack | PARTIAL — generic screen array/stream lifecycle exist; car initialization and advertisement choose one main screen; proxy callback is singleton |
| Second display descriptor | BLOCKED — role/UUID/capability schema and accepted descriptor absent |
| Second display session | BLOCKED — no setup, session/stream identity, app assignment, or independent teardown evidence |
| Serialization | BLOCKED — no field IDs/order/length/byte order/framing or capture fixture |
| Raw Identification capture | MAYBE — needed to resolve exact iAP2 packet fields; may not expose the separate AirPlay display-info/session exchange. First identify the transport/capture boundary and relevant receiver events |
| Ready for real Display-B negotiation implementation | NO |

## Strategy assessment

**Preferred investigation architecture: B, an interposer/extension at the Honda receiver's display/session layer, but only as a bench/offline design at this point.** It is the only option that can plausibly reuse the authenticated primary transport and preserve the existing center session while adding the observed display-info/stream setup behavior. The current proxy is singleton, so this is a real ABI/control-flow change, not a configuration flag. A separate protocol component (C) has even less evidence because transport ownership, iPhone authentication/session coexistence, and USB control ownership are unknown. Config-only extension (A) is contradicted as sufficient by the single `gMainScreen`, main-only display-info copy, and singleton callback evidence.

This does not establish that B is feasible on the old receiver; a compatible implementation may need replacing a larger portion of `jmcs`/proxy behavior. Do not patch or install anything. First obtain a field-backed setup/response trace or find static serializer/setup code that supplies the missing schema.

## Implementation boundary

Future event chain, still unproven:

```text
accepted Display B descriptor/session
  -> independent second video stream and lifecycle
  -> H.264 decoder with stream timing/format
  -> ClarityLink DecodedFrame boundary
  -> Honda ExternalDisplay View host on Android Display 1
```

The model does not claim the iPhone will accept an 800×480 Display B. It uses 800×480 only as the confirmed Android output canvas. The renderer integration, physical crop, and zero-copy path remain outside this milestone.

## Verification

Run `python3 -m unittest discover -s tests/carplay-session-model -p 'test_*.py'`. Model tests cover the primary baseline, Display B preservation/size, unique UUIDs, invalid dimensions, session/display binding, deterministic fixture output with unknown markers, and independent candidate teardown. These tests validate the offline model only.

## Next bounded task

Trace the call site and transport around `AirPlayReceiverSessionScreen_CopyDisplaysInfo` and trace the proxy's `ScreenStream` callbacks through the concrete decoder/output consumer. If those edges cannot be recovered from the saved static artifacts, prepare a capture design that distinguishes iAP2 Identification from the later display-info/session exchange. No hardware purchase or vehicle test follows from this report alone.
