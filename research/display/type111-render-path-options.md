# Step 42B — render-path options

| Render path | Evidence and frame source | Can accept Type111 frames today? | Requirements and risk | Decision |
|---|---|---|---|---|
| Xposed-style View insertion into ExternalDisplayOutService | HondaHack demonstrates a custom View/ImageView inserted into the service's existing Display 1 root from code executing in that process. | No Type111 frame source today; bitmap demonstration only. | Requires host-process integration/Xposed-style hook. Could interfere with factory overlays and has no supported ClarityLink attach lifecycle. | Best evidence-backed **host target**, not a supported product seam. |
| Existing HondaHack host path reuse | Local APK static evidence and previous live output observation. | It can display a supplied bitmap; not a CarPlay Type111 decoder. | Depends on third-party app and Xposed integration; not an OEM interface. | Reference only; not selected as production integration. |
| Privileged/system companion app | Existing Android system can host display-aware windows, but no Honda-specific app contract or Screen 1 sample is proven. | Unknown. | Requires suitable system/signature permissions and testing on Android API 17; exact display composition and physical crop unknown. | Potential alternative after API feasibility proof; not first. |
| `Presentation`/Surface on Display 1 from companion | No Honda evidence that a normal companion may create a visible cluster window or that output stays in safe region. | Unknown. | Could require system privileges, and may compete with factory ExternalDisplay roots. | Do not assume available from Android API presence alone. |
| Direct framebuffer | No active framebuffer format/ownership/geometry contract is recovered for this output. Prior evidence warns about unrelated cluster-composition layers. | No proven path. | Highest risk: bypasses WindowManager, unknown format/bounds, possible loss of factory warnings. | Reject for current plan. |
| Native renderer in jmcs | Generic media/decoder components are present; active CarPlay screen sink/decoder-output surface link remains unresolved. | Unknown. | Would require mapping decoded frames to a valid Android Surface and respecting display ownership. | Not selected. |
| Digital twin/host renderer mock | ClarityLink Python/JS and API17 skeleton model bounded frames/lifecycle; tests pass with synthetic frames. | Synthetic frames only. | No Android process/window, hardware decoder or physical output. | **Only render path ready now.** |

## Selection

The long-term render target is the existing ExternalDisplayOutService View hierarchy because Honda already renders Display 1 content through it and the HondaHack evidence reaches that host. Any ClarityLink adapter still needs authorized code execution in that process and an explicit, bounded frame handoff from the receiver. The closest known mechanism is Xposed-style in-process insertion; it is not a supported public API and is not approved/deployed here.

For active development, use the host-only renderer and HondaOS twin. A first synthetic renderer test is ready and already exercised; a live renderer/companion test is not.

```text
BEST RENDER TARGET: ExternalDisplayOutService View host
BEST EVIDENCED INSERTION: in-process View attachment (Xposed prior implementation)
SUPPORTED COMPANION ATTACH API: NOT FOUND
FIRST SYNTHETIC RENDER TEST: READY (existing host tests only)
LIVE RENDER TEST: NOT READY
```
