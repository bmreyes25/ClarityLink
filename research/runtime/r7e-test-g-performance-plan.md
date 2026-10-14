# R7E Test G — target performance characterization

**Plan state:** `BLOCKED_BY_PRIOR_TEST` / `NOT_AUTHORIZED`  
**Risk:** Tier 3, sustained display/compute load.

**Objective:** Only after separately authorized execution, display admission, controlled rendering, warning coexistence, and restoration passes, characterize actual target performance under an explicitly reviewed workload.

**Staged rates:** very low, then moderate, then higher bounded rates; no immediate 30 FPS jump. Set numeric values and durations in the later reviewed plan using observed results and stop criteria. Record CPU/memory, dropped frames, decode and frame-post latency, UI responsiveness, and thermal observations only where available. No inferred Honda requirement is introduced by R7E.

R7D completed 30 minutes at 14.405 FPS with zero delivery failures; this is a documented emulator/software-test limitation and not a Honda prediction or compatibility failure. Initial target compatibility remains execution/enumeration/admission/one-frame, not continuous rendering.

**Write/resource audit:** temporary bounded render workload and transient counters; no persistent files, system/startup changes, USB/iAP2, MFi, or real CarPlay. Exact commands, rates, workload and temperature observation availability require evidence and prior-test results.

**Stop/rollback:** stop on dropped/unstable UI beyond preapproved bounds, warning/display/audio changes, thermal concern, resource growth, or failed cleanup. Clear/dismiss/release, close process, verify resources and stock UI/cluster/warnings/audio.

**Success:** characterize measured target results with conditions and confidence; final usable acceptance range remains a later product decision. **Readiness:** `BLOCKED_BY_PRIOR_TEST` pending A–F outcomes and separate authorization.
