# 43T1-R4A — cluster navigation renderer architecture

**Scope:** offline architecture only. No Honda, ADB, display, listener, phone, or runtime work occurred. R3C's `jmcs`/Type111 interposition NO-GO remains in force. This note separates the **known display canvas** from an **unproven independent app entry**.

## Preserved display evidence

| Claim | Evidence and label | Limit |
|---|---|---|
| Android HDMI Display 1 is 800×480, about 60 Hz, layer stack 1 | Paired saved SurfaceFlinger/screencap records in [safe-area audit](../navigation-safe-area.md) — `HONDA_OBSERVED`; config independently supports 800×480 — `HONDA_CONFIRMED` | Full Android canvas is not the physical instrument cluster panel or its Navigation rectangle. |
| Factory Navigation, Advanced Meter, and screen casting yielded distinct Display 1 frames | [Paired read-only evidence](../navigation-safe-area.md) — `HONDA_OBSERVED` | The physical photo contains gauges and indicators absent from Display 1; downstream crop, mask, scale, and safe margins remain `UNKNOWN`. |
| Honda `ExternalDisplayOutService` creates Display 1 WindowManager roots | [Static service audit](../display/externaldisplay-api-surface.md) — `HONDA_CONFIRMED` | Its exported `onBind()` returns null; no arbitrary view/bitmap/Surface Binder sink is evidenced. |
| HondaHack 7.7.7 can show a bitmap/custom View through Xposed insertion into that process | [HondaHack path](../hondahack/hondahack-display-path.md) — `HONDA_OBSERVED` plus static third-party implementation | Xposed injection is not a supported ClarityLink API and is outside R4A. Its `(0,24,584,191)` rectangle is **layout local**, not a physical safe area. |
| Android API 17 provides `Presentation` and presentation-display discovery | [Android `Presentation`](https://developer.android.com/reference/android/app/Presentation), [DisplayManager](https://developer.android.com/reference/android/hardware/display/DisplayManager) — `DOCUMENTED_ANDROID` | Whether Honda Display 1 advertises `FLAG_PRESENTATION`, permits an ordinary app window, z-orders it safely, or clips it to Navigation is `UNKNOWN`. |

## Pivot architecture

```text
User-selected destination / own routing app / synthetic offline fixture
  → route-step normalizer (maneuver, distance, street, ETA, route generation)
  → bounded turn-card state machine
  → standalone Android Display 1 renderer candidate
  → physical cluster path (composition and safe area UNKNOWN)

Stock iPhone CarPlay → Honda jmcs → stock center screen/audio (no ClarityLink connection)
```

The first useful design target is **turn-card-only**: one clear next maneuver, distance, street label and optional ETA, with a conspicuous stale/unavailable state. No moving map, video capture, Apple Maps/Waze extraction, Honda Navigation/TBT Binder writes, or claimed Type111 behavior. Destination selection belongs to the user's own navigation source, before driving. The user-facing fallback is Honda's existing cluster/center UI or a blank ClarityLink card; a stale direction must disappear rather than persist. This is an `ARCHITECTURE_CANDIDATE` for offline work, not a proven deployable path.

## Offline renderer model and constraints

An R4B host model can use 800×480 synthetic frames and configurable masks to test: glanceable typography, text overflow, arrow clarity, route generation and expiry, missed update, GPS loss, route cancellation, reroute, disconnect, and immediate clearing. It should show a persistent **synthetic** label in demos. Multiple hypothetical masks can expose sensitivity to unknown physical cropping; none validates an actual safe area. The model may never infer that an Android pixel is visible in a particular physical cluster location.

The candidate app would need a supported, independently owned Android window on Display 1, explicit lifecycle/priority behavior, a safe local data channel, and proof that it cannot obscure warnings or disturb center CarPlay. Existing Honda Binder interfaces offer control/status, not arbitrary pixels. HondaHack's Xposed route and privileged WindowManager roots cannot be silently reused. App installation or car testing is outside this milestone. `Presentation` API existence is only `DOCUMENTED_ANDROID`, not `HONDA_STATIC_COMPATIBILITY` for a third-party app.

**Type110 preservation:** the proposed data/render path does not call `jmcs`, modify CarPlay response/media, or depend on Type111. This is an architectural separation (`INFERENCE`), not a runtime coexistence test. Any future display integration still requires independent evidence that windows/layers do not interfere with stock center CarPlay or safety-critical cluster content.
