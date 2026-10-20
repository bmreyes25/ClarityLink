# R7C6 final software fault matrix

| Software row | Evidence | Status |
|---|---|---|
| Owned API17 AVD create, boot, identity, install, cleanup | Repeated unique AVD smoke; API 17 / 4.2.2 / x86 / Dalvik; no target remains after cleanup | PASS |
| Type110 and Type111 native socket → receiver → H.264 → Surface | 100/100 cycles; fragmented production-adapter loopback frames every cycle | PASS (cycle subgate) |
| Per-cycle native owners and socket FDs | Zero after each cycle | PASS (cycle subgate) |
| Type110 Surface loss at pre-post | Session-global closure and owner cleanup | PASS |
| Type111 Surface loss at pre-post | Type111 closes; Type110 posts after; 25 repetitions in full run | PASS |
| Presentation dismissal at pre-post | Type111 closes; Type110 posts after; 25 repetitions in full run | PASS |
| Type111 peer close during active transport | Type110 continuity and frame post; 25 repetitions | PASS |
| Type110 / Type111 SETUP cancellation | One deterministic case each | PASS (single case) |
| Type110 / Type111 decode shutdown | One deterministic case each | PASS (single case) |
| Native adapter read/write shutdown | Checkpointed local shutdown and thread joins | PASS (single case) |
| Activity destroy after cumulative stress | Focused run passed; combined run paused and released primary Surface but did not reach `onDestroy()` in bounded wait; run stopped without final result | BLOCKED |
| Native socket timeout/refusal/collision and malformed/truncated/oversized/wrong generation/stream | Not all driven through the production Android adapter on Dalvik | BLOCKED |
| Type111 timeout/malformed/truncated/oversized/wrong generation isolation | Not all driven through the production Android adapter on Dalvik | BLOCKED |
| Exact-head hosted checks | No commit/push made | NOT RUN |

`PARTIAL` is not used to imply closure. Honda, iPhone/MFi, physical USB
ownership, and vehicle restoration remain `EVIDENCE_REQUIRED` and are outside
the R7C software decision.
