# CL-FACTORY-01 / M4 — Custom compatibility architecture options & decision

Status: IN PROGRESS. Evidence OBSERVED_STATIC + SYNTHETIC implementation. Offline only. `safeForHonda() == false`.

## Evidence that constrains the design
1. **No supported third-party admission** into the CarPlay receiver or the ExternalDisplay host was found; the only
   demonstrated route (HondaHack) is an unauthorized in-process insertion (reports 03/07/08).
2. **The factory cluster consumes structured turn-by-turn data**, host-rendered into Android Views — not a video
   stream (report 06). A "second CarPlay *video* stream into the cluster" is therefore **partially mismatched** to
   how this factory actually drives cluster navigation.
3. **The native CarPlay receiver's screen registration is singleton** (CL-SYS-01A); no Java-layer secondary-stream
   construct exists (report 03). "No supported handoff found" — not proof of impossibility.
4. **Authentication ownership is unestablished.** A second CarPlay stream cannot be assumed to join the factory
   session; prior R6H1 work indicates genuine second-stream receive would need **authorized receiver hardware**.
5. **A factory warning/interrupt layer exists**, but its preservation under third-party content is **unproven**
   (report 08, U-05); physical cluster aperture is **unknown** (U-04).

## Options evaluated
| Option | Description | Verdict against evidence |
|---|---|---|
| A | Extend an existing *authorized* CarPlay receiver interface | **UNSUPPORTED IN REVIEWED EVIDENCE** — no such extension interface found |
| B | Independent legitimate secondary-stream **receiver** | Feasible **only with authorized receiver hardware + authentication** (not in hand). Its stream/transport/renderer parts are implementable offline now. |
| C | Modular API17 compatibility **service + stream router** | **Implementable offline** (the router/gate/lifecycle/contract). Factory attachment stays inert. |
| D | Independent **Navigation rendering** with a defined factory-display boundary | Best-aligned with the *structured-data* reality, but **attachment/admission is UNSUPPORTED** → must stay fail-closed/inert. |
| E | **Non-invasive fallback**: build & verify the independent offline components; keep all factory integration inert | **Selected** — strongest evidence, fewest unsupported assumptions. |

## Decision
Adopt **Option E now**: implement and test the **independent, offline, fail-closed** components —
secondary-stream identity/lifecycle, the bounded generation-gated `FrameGate` (report/src M5), the fail-closed
`FactoryIntegrationContract` (M6), and (next) a structured cluster-navigation state model — while **all
factory-facing admission/attachment remains inert** (`safe_for_honda()` hard-False).

**Options B/C remain the forward target** *iff* two independent gates are later satisfied: (i) **authorized
secondary-stream receiver hardware + legitimate authentication** (no bypass, no key extraction, no identity
spoofing), and (ii) a **supported factory admission contract** for cluster content (currently unknown → deny).
Option D's renderer is reframed around **structured nav data** rather than a pixel stream, matching the factory.

## Boundary classification (per the prompt's scheme)
| Boundary | Classification |
|---|---|
| Legitimate receiver authentication | UNSUPPORTED IN REVIEWED EVIDENCE (needs authorized hardware) |
| CarPlay session ownership | UNKNOWN (factory-owned; no shared-session evidence) |
| Secondary-stream negotiation (our side) | SYNTHETICALLY IMPLEMENTED (offline model/tests) |
| Type110 continuity | SYNTHETICALLY IMPLEMENTED + PROVEN_STATIC (factory path understood) |
| Independent Type111 lifecycle | SYNTHETICALLY IMPLEMENTED (lifecycle + FrameGate) |
| VideoConfig ownership | SYNTHETICALLY IMPLEMENTED (existing negotiation/transport) |
| Android API17 compatibility | SYNTHETICALLY IMPLEMENTED (pure-Python/offline; renderer reused) |
| Display-host integration | UNSUPPORTED IN REVIEWED EVIDENCE (kept inert) |
| Warning preemption / page selection / frame withdrawal | PROVEN_STATIC (factory mechanism exists) + SYNTHETIC (our withdraw-always model) |
| Host recovery / factory restoration | INFERRED (factory) + SYNTHETIC (our model) |

## What stays inert
No Honda-facing adapter is enabled. The contract mints no Binder transaction or access token. Any real admission,
attachment, authentication, or cluster write remains blocked pending authorized hardware, a supported contract,
read-only runtime evidence (M9, separate approval), and independent safety review.
