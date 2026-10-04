# 43T1-R4B — synthetic turn-card renderer requirements

## Goal and scope

The user goal is useful, glanceable navigation guidance in the cluster while stock center CarPlay stays Honda-owned. R4B creates only a deterministic host model for that proposed user interface. It consumes invented route updates and returns a JSON-ready card description. It neither paints Honda pixels nor runs an Android component.

**R4B does not establish Honda display compatibility. R4B does not authorize vehicle testing. R4B does not use jmcs or Type111.** R3C's receiver/runtime-interposition NO-GO remains in force.

## Evidence and non-goals

- `HONDA_OBSERVED`: preserved Display 1 Android frames are 800×480; see [R4A display audit](43t1-r4a-cluster-rendering-architecture.md). This is a canvas observation, not a cluster safe-area rectangle.
- `UNKNOWN`: third-party independent window access, physical crop/mask, z-order, warning visibility, font legibility and driving safety on the vehicle.
- `MODEL_ONLY`: all route steps, timeouts, layout regions, state transitions and preview snapshots in this milestone.
- Non-goals: live guidance; a navigation provider; GPS/map matching; phone transport; Android/Honda app; HondaHack/Xposed; receiver mutation; map tiles; real road testing.

## Input and output contract

`src/claritylink-renderer/turn_cards.py` defines `Route`, `RouteStep`, `ManeuverKind`, `RouteState`, `RendererState`, `WarningState`, and `ColorMode`. JSON fixtures are parsed through `Route.from_mapping`; malformed enums, negative/nonfinite distances or timestamps, invalid indexes and wrong types are rejected. A step contains maneuver, nonnegative remaining meters, optional street and optional lane hint. A route contains a synthetic ID, generation, state, steps, current index, update time in synthetic seconds, optional remaining ETA minutes and a **simulated** `source_trusted` flag. The flag is a fixture branch, not authentication or spoofing protection.

`render_card(route, now_s, mode, manual_clear)` returns a `TurnCard` with current/next maneuver, distance, street, secondary instruction/lane hint, ETA, route progress, warning, mode, generation, canvas, named rectangles, and the persistent `MODEL_ONLY / SYNTHETIC - NOT FOR DRIVING` evidence label. It has no I/O or side effects. `tools/r4b_preview.py` serializes the checked-in synthetic cases to stdout as JSON; it reads no external source and opens no listener.

## Minimum viable UI and layout

The card puts one primary maneuver and distance above a street name, a short next-step or lane hint, and ETA/progress. The warning banner has a reserved top region and supersedes all turn fields. The evidence label occupies a separate bottom region. These seven rectangles fit inside a synthetic 800×480 canvas and do not overlap; they are **not** Honda physical safe areas. Text capacity is a deterministic character budget: street at most 30 characters, secondary line at most 42, with `...` on truncation. It does not prove actual font metrics or readability.

The input mode is day/night and appears in the output state; R4B does not choose colors automatically, know ambient brightness, or test glare. A downstream renderer would need contrast, font, warning-priority and distraction review. No preview should be shown as road-ready navigation.

## Freshness and fail-safe rules

Synthetic `FRESH_SECONDS = 5`: an active route remains a guidance card at age ≤5 s. At age >5 s the model shows `ROUTE UPDATE STALE` and removes maneuver/distance/street. Synthetic `LOST_SECONDS = 30`: at age >30 s it shows `ROUTE LOST`. Explicit stale/lost/error/rerouting states, invalid/future time, unknown maneuver and untrusted-source fixture state also suppress turn data. Arrival shows `DESTINATION REACHED`; manual clear shows `GUIDANCE CLEARED`. No route shows `NO ROUTE`. These thresholds and strings are model values, not final UX or vehicle safety decisions.

The model cannot detect a syntactically valid but geographically wrong turn. It cannot authenticate a real route source, recover from a real renderer crash, or measure phone/GPS latency. Those remain `UNKNOWN` integration questions; the safety matrix records them.

## Proof boundary and next evidence

Focused tests establish deterministic schema rejection, all maneuver enum branches, warning precedence, freshness boundaries, text budgets, 800×480 model bounds and a source dependency boundary with only Python standard-library imports. The source contains no `jmcs`, Type111, Honda memory, network listener, Android or HondaHack backend. That is a **static model non-interference invariant**, not a measured Type110 coexistence result.

R4C should statically review whether a supported independently owned app can access Display 1 without obscuring warnings or disrupting stock center CarPlay. A negative display-access result must remain negative; it must not redirect R4B into runtime interposition. Any car work requires a new separately authorized milestone.
