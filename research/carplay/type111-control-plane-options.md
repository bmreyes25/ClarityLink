# Step 42A — Type 111 control-plane options

This note separates the primary control plane from rendering and from the parked `LD_PRELOAD` hypothesis. No option is implemented here.

| Option | Evidence / requirement | Assessment |
|---|---|---|
| Append a display descriptor in `/info` | Honda's phone-facing `displays` value is an array, but the stock callback appends exactly one descriptor from `ScreenCopyMain()`. The second descriptor fields/UUID semantics and iPhone acceptance are unknown. | Structurally modellable, protocol behavior unproven. |
| Let stock Setup see Type 111 | Honda's current loop logs/skips unsupported 111 without writing an error or response entry. It is not a handler. | Cannot produce Type 111 listener/response. |
| Stock-first Setup extension | Step 38's static flow supports calling stock on the original mixed request; successful Type 110 remains in the response and unsupported 111 alone does not set status. A separate implementation would still need listener, security, response schema, and teardown ownership. | Best future compatibility pattern, but requires code entry in jmcs/proxy or another receiver. Not live-ready. |
| CarPlay AP Binder API | Exported `CarPlayApService` Binder covers app/session state, phone, audio/source, touch, display configuration/status, callbacks and navigation ownership. It does not accept a stream descriptor, data socket, H.264 frame, Surface, or decoder output. `setVideoPath(int)` toggles AV service video path 11. | Not a Type 111 control plane. |
| ExternalDisplay AP Binder API | Exported API supports LVDS status/interrupt, meter content selection/data, display state, callbacks and diagnostics. No arbitrary View/Surface/pixel/H.264 input is exposed. | Not a Type 111 receiver handoff. |
| ExternalDisplayOutService | Owns external-display windows but `onBind()` returns null. It exposes static in-process `InterfaceWindow` methods such as `addView(int, View, boolean)` to code executing in its process/classloader. | Rendering host exists; no supported external Binder view API found. |
| Independent companion receiver | Would need its own iPhone-visible negotiation endpoint, session association/authentication, Type 111 parser/crypto/listener and decoder; no Honda API transfers those objects from jmcs. | Possible as a new receiver architecture, not a recovered Honda handoff. Large unknown scope and may conflict with stock receiver/network ownership. |
| jmcs/proxy integration | Honda Setup and `/info` behavior are in jmcs; `libcarplay_proxy.so` is mapped/linked but prior audits describe a stock proxy boundary without a proven plugin ABI. | Remains the most direct control-plane seam, but load/entry is unresolved and `LD_PRELOAD` remains parked. |

## Least-disruptive architecture supported by present evidence

The models should keep Type 110's stock response and runtime untouched, then treat any Type 111 listener/descriptor as separately owned state. The only known Android output host is ExternalDisplayOutService. It can render regular Views from inside its own process, but no stable public API accepts decoded frames. Therefore control-plane and rendering integration remain two distinct unresolved interfaces.

No existing component currently proves a supported bridge from jmcs's authenticated stream session into the ExternalDisplay host. A future safe design needs either (a) a supported receiver/session handoff plus a supported render-frame handoff, or (b) an independently implemented receiver and renderer path that does not take over stock Type 110. The current evidence establishes neither.

## Decision

```text
NON-JMCS TYPE111 CONTROL PATH: NO EXISTING HANDOFF FOUND
NON-JMCS RENDERING HOST: YES (ExternalDisplayOutService), with private in-process attach only
SUPPORTED NON-JMCS RENDERING API: NOT FOUND
CURRENT STOCK TYPE111 RESPONSE: NONE; unsupported request is skipped
JMCS OR NEW RECEIVER REQUIRED FOR TYPE111: YES (absent a newly implemented independent receiver)
```
