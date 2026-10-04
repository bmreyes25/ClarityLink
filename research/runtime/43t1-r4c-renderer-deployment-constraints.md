# 43T1-R4C — renderer deployment constraints

The [R4B turn-card model](43t1-r4b-turn-card-renderer-requirements.md) proves only host-side state projection. This companion note lists evidence needed before any future device implementation is even reviewable. None is implemented or authorized by R4C.

| Concern | Missing proof or contract |
|---|---|
| Display entry | Ordinary project-owned `Presentation` or other public window accepted on Honda Display 1, with known display identification and permissions. `UNKNOWN`. |
| App lifecycle | Start/stop, display removal, interruption, power cycle, crash and stale window cleanup. `UNKNOWN`. |
| Route source | User-controlled, licensed route-step source and authenticated, bounded delivery; R4B fixtures are `MODEL_ONLY`. |
| Stale-state clearing | R4B clears its **data** after synthetic 5/30-second thresholds; Android View/window removal on source loss or crash is `UNKNOWN`. |
| Warning/safe area | Physical transform, OEM Navigation viewport and warning priority. Display 1's 800×480 canvas is `HONDA_OBSERVED`; safe coordinates remain `UNKNOWN`. |
| User disable switch | A reliable user-facing stop that removes project content without suppressing Honda content. `UNKNOWN`. |
| Center CarPlay | On-car evidence that the independently owned display window does not alter Type110/center audio/UI. `UNKNOWN`; R4B's no-dependency code is only architectural. |
| Factory Navigation | Priority and coexistence with Honda main/interrupt/bottom roots; no replacement or obscured warnings. `UNKNOWN`. |
| Crash cleanup | Operating-system and app-owned cleanup of window, route state and source channel, with bounded recovery. `UNKNOWN`. |
| Long session | Memory, redraw, expiry, display changes, suspend/resume and disable behavior over time. `UNKNOWN`. |

**Constraint:** no deployable vehicle code, APK, binder transaction, framebuffer output or on-car display action is produced in R4C. The [feasibility gate](43t1-r4c-independent-display-app-feasibility-gate.md) remains `NOT_AUTHORIZED`.
