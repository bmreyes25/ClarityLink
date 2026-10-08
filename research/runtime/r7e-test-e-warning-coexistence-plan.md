# R7E Test E — warning and interrupt coexistence

**Plan state:** `BLOCKED_BY_EVIDENCE` / `NOT_AUTHORIZED`  
**Risk:** Tier 3, safety-sensitive visible display state.

**Objective:** Under a separately authorized safe condition, establish whether normal Honda warning/interrupt content remains visible and is not obscured while project content is admitted. AOSP z-order is not proof.

No warning/fault is to be induced. Do not create DTCs or provoke powertrain, airbag, ABS, or other faults. The static record does not identify a benign factory-supported warning/interrupt that can safely be observed in a stationary state. Therefore `SAFE_CONDITION_SELECTION_REQUIRED`; do not invent an example or assume an ordinary notification is equivalent.

**Prerequisites:** separately authorized A–D outcomes, a later evidence-backed benign condition, safety review of exact procedure, and separate explicit authorization. The first frame must be the reviewed diagnostic frame; the observation must not require driving or driver reliance.

**PROPOSED — NOT EXECUTED:** if a benign condition is later supported and approved, observe the stock warning layer before/during/after the bounded display test and record human-visible evidence. No deliberate fault induction, warning suppression, or warning-disable action.

**Audit/rollback:** temporary display output only; no warning configuration, system file, input, CAN, USB, authentication, or audio changes. Clear/dismiss/release/stop and verify warnings, cluster, center UI, and audio return to stock. Any warning disappearance/change is immediate stop.

**Success:** warning/interrupt remains visible in the exact observed condition and is not suppressed; scope limited to that observed state. **Readiness:** `BLOCKED_BY_EVIDENCE` because no supported benign condition is established. Not authorized.
