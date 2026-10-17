# CL-R0–CL-R8 development plan

The roadmap is ordered by technical dependencies. Each milestone must close its stated evidence gate before dependent work begins. The roadmap does not grant authorization for emulator, iPhone, Honda, or vehicle operations.

| Milestone | Objective | Exit gate |
|---|---|---|
| CL-R0 | Organize repository guidance, establish one status and roadmap, add lightweight consistency checks, preserve history | Curated docs and status manifest agree; links/schema/evidence checks pass; independent review records exact reviewed changes and limitations. |
| CL-R1 | Resolve deterministic warning-preemption race | Reproduce queued-frame race; add epoch/generation invalidation; prove no stale frame appears during warning entry, renderer death, or resume. |
| CL-R2 | Establish reliable isolated API17 emulator testing | Use the verified dedicated API17 emulator and ADB-server isolation; bind each run to exact emulator and artifact identity. |
| CL-R3 | Complete Binder-to-View integration | Current lab APK completes bounded end-to-end frame, draw, warning rejection, lifecycle, and cleanup checks on approved emulator. |
| CL-R4 | Complete independent dual-stream fault and reconnect coverage | Preserve stream isolation while proving Type111 sink recovery, Type110-only ownership behavior, parent-authority death, reentrant teardown, and complete API17 cleanup. |
| CL-R5 | Establish authenticated Type111 extension contract | Define evidence-backed same-session authority and teardown without borrowing or fabricating authentication; remain lab/synthetic until Honda acceptance is separately established. |
| CL-R6 | Establish Honda display integration contract | Evidence and review establish a supported frame-admission boundary, warning/lifecycle behavior, safe region, and rollback. No implementation assumption substitutes for missing Honda evidence. |
| CL-R7 | Perform separately authorized hardware validation | Each bounded test has separate explicit authorization, reviewed artifacts, stop conditions, and restoration evidence. |
| CL-R8 | Validate integrated navigation target | Demonstrate factory CarPlay on Display 0 and independent navigation on Display 1 while preserving warnings, instruments, authentication, audio, controls, and stock behavior. |

CL-R0 remains `REVIEW_PENDING`. CL-R1 warning interleavings, CL-R2 isolated crash recovery, and CL-R3 Binder-to-View acceptance are API17-lab verified. CL-R4 has a versioned stream-aware Binder/PFD contract, bounded Type111 dispatch, Type110 progress during deterministic Type111 saturation, separate Type110/Type111 generation changes, and actual Type111 fixture frames drawn after a live Type111 generation transition. It remains `IN_PROGRESS` until the independent API17 decoder/producer/sink failure and reconnect matrix is complete. CL-R5's synthetic capability, setup, presentation, geometry, and VideoConfig model now executes through the API17 compositor's private Binder endpoint and the same stream identity. It is not CarPlay wire negotiation or authenticated Honda integration. These results do not prove Honda warning, authenticated Type111, or display behavior. CL-R6 through CL-R8 require further evidence and separate authorization.

## Related records

- [Current status](../status/current.md)
- [Milestone specifications](milestone-specifications.md)
- [Dependency map](dependency-map.md)
- [Blocker tracker](../status/blockers.md)
- [Safety guide](../safety/vehicle-testing.md)
