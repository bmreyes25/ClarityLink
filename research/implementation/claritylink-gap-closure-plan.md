# ClarityLink implementation gap closure plan

This plan sequences offline implementation from the CL-IMP-00 audit. It extends the current custom receiver, renderer, Android/native adapters and simulator. It does not authorize Honda or live-iPhone activity. Each milestone gets focused verification, applicable regression/security checks, review, then a separate ECC commit approval gate.

| Milestone | Reuse and scope | Exit evidence | External boundary kept open |
|---|---|---|---|
| CL-IMP-00 | Add this executable architecture spec, component inventory and gap plan; enforce fixed claims in tests. | Spec tests and repository regressions pass; inventory paths resolve. | No live compatibility claim. |
| CL-IMP-01 | Consolidate HondaHack static behavior and provenance in the existing `research/hondahack/` records. | Documented attach, frame, lifecycle and restore semantics with source links and unknowns. | No hooks, stock-process changes, or physical safe-area assertion. |
| CL-IMP-02 | Extend `src/claritylink-renderer/android-api17/` with project-owned API17 hosted View, bounds, warning preemption and teardown contracts. | Host-side Java/API checks cover page exit, warning, resize and cleanup. | No Honda root acquisition. |
| CL-IMP-03 | Turn existing `SecondaryDisplayHost`/`Presentation` code into an independent test-app adapter. | Isolated API17 emulator admission, frame, warning and teardown evidence. | Emulator success is not Honda admission. |
| CL-IMP-04 | Implement a simulated ExternalDisplay-style host and bounded decoded-frame IPC/shared-memory channel. | Two project-owned processes exchange generation-bound frames with backpressure and cleanup tests. | No communication with Honda's process. |
| CL-IMP-05 | Harden existing capabilities and /info profiles with provenance and production gating. | Exact type/UUID/primary-ownership acceptance tests. | iPhone/Honda schema compatibility remains unknown. |
| CL-IMP-06 | Extend Type111 setup/delegation contracts over current receiver session model. | Stock-first, primary snapshot and secondary-only failure tests. | No Honda SETUP mutation or session access. |
| CL-IMP-07 | Complete per-stream transport/security provider seams and fail closed on unknown production crypto. | Provider conformance, malformed input, generation, and negative security tests. | No MFi bypass, secret extraction, or guessed Type111 cryptography. |
| CL-IMP-08 | Integrate H.264 config/parser/decoder paths and API17 decoder adapter. | API17 x86 emulator decoded two independent synthetic streams to separate Surfaces and exercised explicit 32×32→64×64 reset; host fixture decode, API17 compile, bounds, generation/timestamp rejection, teardown and regression tests pass. | No authentic iPhone fixture; no physical scanout proof; macroblock crop/viewport handling and complete production AU framing remain for CL-IMP-09. |
| CL-IMP-09 | Complete cluster viewport renderer from decoded frames, including crop/rotation policy and resource bounds. | Synthetic-only viewport contract; crop/rotation, safe/protected clipping, warning preemption/resume and stale-generation checks pass on isolated API17 emulator. | Safe area/warning priority remain simulated; no Honda physical scanout or geometry evidence. |
| CL-IMP-10 | Unify the existing session and receiver with independent Type110/Type111 workers, explicit resource identity, and bounded lifecycle shutdown. | Concurrent listener/media tests, same-generation replacement races, Type111-only withdrawal, resource-zero close, and full offline regression pass; independent ECC review clear. | Synthetic/replay host evidence only; no Honda process lifecycle or authentic iPhone claim. |
| CL-IMP-11 | Compose separate Type110/Type111 owners in a full offline two-display demonstration. | Distinct simultaneous streams; warning blanking; secondary faults do not stop primary. Synthetic labels remain visible. | Laboratory success is not Honda/iPhone validation. |
| CL-IMP-12 | Build reproducible ARMv7/API17 native library and test-only APK; record hashes/toolchain. | Clean repeat build and symbol/package audit. | No installation on Honda. |
| CL-IMP-13 | Add bounded stress/fault/security coverage and perform security review of session, crypto and IPC changes. | Focused + complete offline regressions, emulator suite, memory/lifecycle checks. | No target execution. |
| CL-IMP-14 | Reconcile every acceptance item and external gate; update PR documentation and final matrix. | Exact-HEAD local/hosted checks and completeness report; stop without starting another milestone. | Future Honda work requires new evidence and separate authorization. |

## Fixed acceptance assertions

- Center Display 0 remains factory Type110 and retains all primary and vehicle control ownership.
- Display 1 receives separate navigation data; mirroring is never accepted as completion.
- Synthetic/replay content remains explicitly synthetic.
- Mock/source/emulator/build evidence never establishes Honda integration.
- Any secondary failure, warning or disconnect clears only ClarityLink's secondary output and owned resources.
- Unknown production authentication/security fails closed.
- Honda integration is disabled throughout this campaign.
