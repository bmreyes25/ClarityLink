# ClarityLink Rules v2 — staged prototype discipline

## Final goal

The final goal remains:

```text
normal Type110 CarPlay on the center Display Audio screen
+
independent navigation content on the instrument cluster
```

The ideal final form is one simultaneous CarPlay session with independent Type111 / AltScreen navigation on the cluster. R6 offline work may develop a target-compatible custom receiver; this does not authorize running or installing it on the Honda.

## Current status

- R3C still controls `jmcs`/Type111 runtime work.
- R4C found API17 `Presentation` is a possible generic Android lead, but Honda Display 1 admission remains unproven.
- R6 primary engineering path is an offline clean-room Honda-compatible custom receiver; R3C still parks stock `jmcs` interposition.
- No car test is authorized by these rules or the current milestone.

## Core principle

Offline first. Backups required. Tests required. Static review required. Car tests only after exact written plans and explicit authorization. Backups are mandatory, but backups are not enough. Host tests are mandatory, but host tests are not Honda proof. A parked-car test is possible only after an exact written plan is reviewed and explicitly authorized.

## Evidence levels

Use these labels with scope and provenance:

| Level | Meaning |
|---|---|
| `MODEL_ONLY` | A simulation, design, or synthetic/host model; no target behavior established. |
| `DOCUMENTED_ANDROID` | Generic Android behavior supported by version-correct Android documentation/source. |
| `HONDA_STATIC` | Honda-specific preserved artifacts inspected offline; establishes only what those artifacts show. |
| `HONDA_READ_ONLY_OBSERVED` | Honda behavior observed through a separately authorized read-only procedure under recorded conditions. |
| `HONDA_PROTOTYPE_OBSERVED` | Behavior observed from a separately authorized prototype under its exact plan and conditions. |

Never promote a lower evidence level into a higher one. Never treat Android generic behavior as Honda behavior. Never treat host simulation as car proof.

## Current Type111 status

Phone/current-iOS dual-stream behavior is proven in the lab. Honda Type111 is not proven. R3C found no safe additive Honda receiver entry. Type111 may reopen only with new Honda-specific entry/ownership evidence; any further step still requires its own review and authorization.

## Current Display 1 status

Display 1 exists and is tied to the cluster Navigation path. API17 `Presentation` is a possible ordinary-app lead. Honda ordinary-app admission to Display 1 is unproven. Physical safe area, warning z-order, crop, mask, and downstream composition are unproven.

## Required workflow

Every milestone must:

1. Define its objective.
2. Define scope.
3. Define prohibited activity.
4. Preserve user work.
5. Implement or research offline first.
6. Add or update tests/checks.
7. Run focused tests/checks.
8. Run the full suite when relevant.
9. Run repository health checks.
10. Run a diff check.
11. Write a report.
12. Update `PROJECT_STATE.md`, `NEXT_ACTION.md`, and `EVIDENCE_INDEX.md`.
13. Push the milestone commit when authorized and feasible.
14. Verify hosted CI and CodeQL on the actual pushed commit.
15. Decide the next milestone.

Record checks that were not run as not run; never imply success from an older commit.

## Live-car authorization gate

No Honda/vehicle step may happen automatically. Before any Honda, ADB, APK, display, or vehicle action, require a written run plan containing:

- objective;
- exact commands or actions;
- expected duration;
- vehicle state;
- whether CarPlay is connected;
- whether the vehicle is parked;
- whether READY mode is needed;
- read/write classification;
- files touched;
- rollback;
- stop conditions;
- success criteria;
- failure criteria;
- how stock behavior is verified afterward; and
- explicit user authorization for that exact plan.

Passing this gate applies only to the specifically authorized plan. It does not grant blanket or continuing authorization.

## Absolute no-go without separate higher-risk review

The following are not authorized by normal progress work and require a separate high-risk review:

- `/dev/block` writes;
- flashing;
- boot/recovery changes;
- persistent init/startup changes;
- persistent HondaHack/Xposed dependency;
- CAN writes;
- USB injection;
- framebuffer writes while driving;
- disabling warnings;
- obscuring speed/status/safety UI;
- live Type111 negotiation;
- `jmcs` patching;
- callback replacement;
- `LD_PRELOAD`/startup mutation; and
- APK installation.

Higher-risk review is not itself authorization; explicit authorization for the exact plan is still required.

## Parked-car prototype rules, if ever authorized

Any separately authorized parked-car prototype must be parked only and not used on public roads. It must prove one narrow thing only, have logging and an immediate stop path, verify stock restoration afterward, verify the center display afterward, verify cluster warning visibility afterward, clear stale route display, and avoid persistence unless persistence is separately authorized. A prototype must satisfy the exact run plan and stop conditions; unexpected behavior ends the session.

## Success definition

ClarityLink is complete only when a reviewed implementation demonstrates all of the following:

- normal center Type110 CarPlay active;
- independent cluster navigation active;
- both simultaneous;
- stock audio preserved;
- safety/warning UI not obscured;
- stale navigation clears;
- teardown/reconnect works; and
- system returns to stock behavior when disabled.

Host-only success, backups, static feasibility, or generic Android behavior cannot satisfy this definition.
