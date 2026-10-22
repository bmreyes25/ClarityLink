# CL-FACTORY-01 / M10 — Remaining evidence gaps

Status: living list. Evidence class per item. Offline only. `safeForHonda() == false`.

## Resolved offline (static scope complete)
| ID | Gap | Outcome |
|---|---|---|
| G-01 | Native CarPlay second-stream capability in `carplay_main` / `libcarplay_proxy` | **DONE** (report 05) — singleton screen registration code-confirmed; no exposed second-stream handoff at the native binding |
| G-02 | Main-vs-interrupt compositing order | **DONE** (reports 07/08) — three separate windows attached bottom→main→interrupt (interrupt top-most); static 3-tier z-bucketing within each layer. Runtime/under-injection precedence still open → G-10/U-05 |
| G-03 | Host-process death/restart + factory-restoration sequencing | **DONE** (report 07) — display-removed = immediate teardown + content stand-down; display-added = delayed, validity-gated rebuild + resume; invalid display refused. Real-world timing + injected-content behavior remain runtime-only |
| G-04 | Structured cluster-navigation state model (ClarityLink side) | **DONE** — `cluster_navigation_model.py` + 11 unit / 3 integration tests |
| G-05 | CarPlay Type110 decoder/frame-buffer ownership (Java→JNI boundary) | **DONE** (report 05) — platform MediaCodec owns decode; proxy is the single-screen callback bind |

## Resolvable offline (bounded next work)
_All originally-scoped offline gaps (G-01…G-05) are closed above. Remaining items below require authorized hardware
or separate approval; no further static-only gap is outstanding for this campaign._

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
  structured data; two-layer main/interrupt composition as **separate windows** (interrupt top-most, G-02);
  display-link death→teardown and validity-gated rebuild→resume (G-03); Display-1 observed (not created).
- SYNTHETICALLY IMPLEMENTED: secondary-stream identity/lifecycle, bounded FrameGate, fail-closed contract, dual-stream integration.
- UNKNOWN/UNSUPPORTED: supported admission, authentication ownership, cluster aperture, warning-precedence preservation.
- None of the UNKNOWN/UNSUPPORTED items may be promoted by synthetic evidence.
