# CL-FACTORY-01 / M10 — Remaining evidence gaps

Status: living list. Evidence class per item. Offline only. `safeForHonda() == false`.

## Resolvable offline (bounded next work)
| ID | Gap | Approach |
|---|---|---|
| G-01 | Native CarPlay second-stream capability in `carplay_main` / `libcarplay_proxy` | Bounded Ghidra on the preserved native binaries; re-confirm singleton screen registration (report 05) |
| G-02 | Exact main-vs-interrupt compositing order vs main-layer manipulation | Method-level trace of the host layout/compositor in the deodexed smali |
| G-03 | Host-process death/restart + factory-restoration sequencing | Trace the host lifecycle + AP-service retry/feedback paths |
| G-04 | Structured cluster-navigation state model (ClarityLink side) | Implement an offline model (maneuver/arrow/distance/road-name) + tests (M5/M6 follow-on) |
| G-05 | CarPlay Type110 decoder/frame-buffer ownership (Java→JNI boundary) | Ghidra at the JNI boundary where DEX analysis stops (report 05) |

## Requires authorized hardware / separate authorization
| ID | Gap | Gate |
|---|---|---|
| G-06 | Legitimate secondary-stream receiver authentication | Authorized receiver hardware + legitimate auth (no bypass/keys/spoofing) |
| G-07 | A supported factory admission contract for cluster content | Unknown; none found → deny. Needs OEM/engineering evidence |
| G-08 | Live build vs preserved image identity; real Display 0/1 topology/ownership | Read-only parked-car ADB (report 11), owner-approved |
| G-09 | Physical cluster aperture / crop / mask | Runtime observation + measurement; not derivable from the Android logical size |
| G-10 | Warning-precedence preservation under third-party content (U-05) | Runtime evidence + independent safety review; never asserted from static code |

## Classification summary
- PROVEN_STATIC: factory CarPlay receiver shape (Java wrapper + native receiver + AIDL fabric); cluster nav =
  structured data; two-layer main/interrupt composition; Display-1 observed (not created).
- SYNTHETICALLY IMPLEMENTED: secondary-stream identity/lifecycle, bounded FrameGate, fail-closed contract, dual-stream integration.
- UNKNOWN/UNSUPPORTED: supported admission, authentication ownership, cluster aperture, warning-precedence preservation.
- None of the UNKNOWN/UNSUPPORTED items may be promoted by synthetic evidence.
