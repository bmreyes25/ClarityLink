# 43T1-R3B — cleanup coverage matrix

This matrix distinguishes static Honda cleanup of Honda-owned objects from project-child cleanup. `COVERED_STATICALLY` means the cited Honda static path covers the named Honda-owned object/path only; it never implies Type111 child reachability.

| Scenario | Cleanup path evidenced? | Session identity? | Project child reachable? | Type110 risk | Evidence label | Verdict |
|---|---|---|---|---|---|---|
| normal Setup success | Setup returns response; response graph is released after serialization; later session finalizer is possible but not guaranteed by this event | Opaque session in caller; no project association | No | Observed stock cleanup retains/releases Type110; no child link | `HONDA_CONFIRMED` | `PARTIAL_STATIC_EVIDENCE` |
| normal disconnect | `tearDownStreams` path handles recognized stock 100/101/110; eventual finalizer timing/coverage not universally shown | Session argument on teardown; app event lacks it | No; unknown 111 is skipped | Existing stock Type110 teardown is traced | `HONDA_CONFIRMED` | `PARTIAL_STATIC_EVIDENCE` |
| CarPlay cable disconnect | No distinct cable-removal-to-project-child cleanup chain established; may enter conditional session teardown | Conditional/unknown | No | Stock path not separately proven for this trigger | `UNKNOWN` | `UNKNOWN` |
| malformed Setup | Observed Setup/helper branches release local Honda response objects; no project child should exist if created only after success, but that is a project ordering rule | Session in handler frame | No evidenced child creation/cleanup path | Stock-only branch | `HONDA_CONFIRMED` | `PARTIAL_STATIC_EVIDENCE` |
| serializer failure | Response and Honda local objects are released along observed handler path; no project resource lookup/rollback edge | Caller session exists locally; no child association | No | Stock graph released; project rollback not Honda-proven | `HONDA_CONFIRMED` | `PARTIAL_STATIC_EVIDENCE` |
| Type111 unsupported security | No Honda Type111 security cleanup path evidenced; fail-closed retirement exists in offline policy only | Project key in model only | Only in model | Model promises Type110 remains untouched | `MODEL_ONLY` | `MODEL_ONLY` |
| listener bind failure | No Honda listener exists in reviewed path; project rollback contract is synthetic/host-only | Project generation in model only | Model registry only | Model avoids Type110 mutation | `MODEL_ONLY` | `MODEL_ONLY` |
| listener accept failure | Honda finalizer has no demonstrated listener handle; host tests close modeled listener | Project generation in model only | Model registry only | Model isolates Type110 | `MODEL_ONLY` | `MODEL_ONLY` |
| media stream never connects | No Honda cleanup edge from non-arrival to a project child; lease/reaper is a model policy | Project generation in model only | Model registry only | Model isolates Type110 | `MODEL_ONLY` | `MODEL_ONLY` |
| stale generation | No Honda generation field/cleanup dispatch; exact-key stale retirement exists in offline registry model | Project generation in model only; Honda generation unknown | Model registry only | Model exact-key cleanup avoids Type110 | `MODEL_ONLY` | `MODEL_ONLY` |
| duplicate generation | No Honda duplicate child registration path evidenced; duplicate rejection/supersession is modeled | Honda session pointer is not a stable generation | Model registry only | Model preserves Type110 | `MODEL_ONLY` | `MODEL_ONLY` |
| process crash | No process-independent project resource cleanup or durable owner evidenced | Lost/unknown | No | Not established | `UNKNOWN` | `UNKNOWN` |
| process restart | No restart recovery for project child/listener/generation evidenced | Lost/unknown; pointer reuse unknown | No | Not established | `UNKNOWN` | `UNKNOWN` |
| power loss | No Honda or project cleanup execution can be inferred across power loss | Unknown | No | Not established | `UNKNOWN` | `UNKNOWN` |
| manual CAR-OFF | No observed/static contract ties manual vehicle power-off to project cleanup; no vehicle action was part of R3B | Unknown | No | Not established | `UNKNOWN` | `UNKNOWN` |

## Sources and interpretation

Primary static sources: [43L.1](../../step-reports/43l1-callout-safety-cleanup-reachability.md), [43L.2](../../step-reports/43l2-session-finalizer-extension-audit.md), [project-child reachability](../../research/carplay/honda-project-child-cleanup-reachability.md), and [R2 CFLite ownership audit](honda-cflite-ownership-static-audit.md). Model-only scenarios refer to historical offline project policies/tests in 43L/R0/PREP2; they do not prove a Honda cleanup path. No row claims `COVERED_STATICALLY` for project-created Type111 children.
