# 43T1-R4C — independent Display 1 app feasibility gate

**Default state: `NOT_AUTHORIZED`.** This is an evidence checklist for a separately scoped future decision. It does not approve APK installation, ADB, Honda contact, display drawing or any car experiment. R3C's runtime-interposition NO-GO and the [R4A new-evidence gate](43t1-r4a-new-evidence-gate.md) remain in force.

## Combined evidence needed before a future proposal

1. **Supported app-owned entry:** version-correct public Android mechanism plus Honda-specific proof that an independently signed normal app can identify Display 1 and own a visible window there. AOSP category behavior and Honda's own WindowManager use are **not** this proof.
2. **No rejected dependency:** no `jmcs`, Type111, HondaHack/Xposed, Honda service replacement, framebuffer write, process memory modification or persistent system configuration. Record exact code and package boundary.
3. **Known package/signing grant:** determine Display 1 flags/type and any relevant OEM policy; enumerate actual requested permissions, protection levels, signing/install class and whether ordinary app grants suffice. Unknown `VEHICLE_RW` and `ACCESS_MAP` definitions cannot be assumed grantable.
4. **Lifecycle and bounded failure:** known create/show/dismiss/display-removed/restart behavior; explicit manual disable; stale/lost route clearing; crash and long-session cleanup. The R4B host model does not prove Android window removal.
5. **Safety boundary:** OEM-supported or independently established physical Navigation viewport/transform and warning/status priority; no coverage of speed, warning, or factory interrupt content; known z-order relative to Honda's main/interrupt roots. An 800×480 Display 1 screenshot is insufficient.
6. **Stock coexistence:** evidence that center CarPlay/audio and factory Navigation remain Honda-owned and unaffected by app window creation, route cancellation, and process failure. Architectural separation alone is insufficient.
7. **Exact future review packet:** a separately requested plan identifying hardware/software fingerprint, app provenance, entry API, permissions, every command/action, observation scope, stop conditions, privacy handling, uninstall/recovery behavior, ECC safety review and independent approval. A positive static finding would only enable review of that packet.

## Current gate status

| Gate item | R4C status |
|---|---|
| AOSP API-17 public `Presentation` mechanism | `DOCUMENTED_ANDROID` |
| Honda Display 1 HDMI/800×480 existence | `HONDA_OBSERVED` |
| Ordinary app visible on Honda Display 1 | `UNKNOWN` |
| Honda `Presentation` admission / app signing grant | `UNKNOWN` |
| Physical safe rectangle and warning priority | `UNKNOWN` |
| App window crash/stale cleanup and stock coexistence | `UNKNOWN` |
| Any live/app experiment authorization | **`NOT_AUTHORIZED`** |

No missing item may be filled by HondaHack's in-process output, a model preview, a semantic Navigation Binder call, or generic AOSP behavior. R4D may continue static analysis; it may not install or run anything on the head unit.
