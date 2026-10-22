# CL-FACTORY-01 / M2–M4 — Type110 vs Type111, and two cluster presentation contracts

Status: IN PROGRESS. Evidence OBSERVED_STATIC + SYNTHETIC. Offline only. `safeForHonda() == false`.
This report separates **what the factory does** from **what the ClarityLink product wants**, and keeps the two
candidate cluster presentation contracts distinct.

## Type110 — center-display CarPlay (understood)
- A genuine Apple CarPlay **video** stream. Path (PROVEN_STATIC, reports 03/05): iPhone → native AirPlay-family
  receiver → AES-encrypted screen stream → Android **MediaCodec** decode → platform video-out, with the proxy as
  the single-screen callback bind. This is a real, decoded pixel stream on Display 0.

## Type111 — the product goal (secondary cluster stream)
The product goal is a **second, independent** navigation presentation on the instrument cluster while Type110
continues on the center display. Two very different presentation contracts could satisfy "navigation on the
cluster", and they must not be conflated:

### Contract 1 — Structured turn-by-turn (semantic)
- **What the factory actually does.** The factory cluster consumes **structured** maneuver/distance/road-name data
  and renders it host-side into Android Views (reports 06/07). It is **not** a video feed.
- **ClarityLink side (implementable, done):** `cluster_navigation_model.py` (G-04) models exactly this — structured
  updates, freshness, visibility, warning withdrawal, recovery, restoration — offline and testable.
- **Compatibility:** aligned with the factory's *mechanism*, but **delivery into the factory cluster host is
  UNSUPPORTED** — there is no public/authorized API to inject structured nav into the factory host; the only
  demonstrated route (HondaHack) is an unauthorized in-process insertion. So ClarityLink can *produce* correct
  structured nav state, but a *supported* path to the factory cluster is unproven.

### Contract 2 — Genuine Type111 video frame pipeline
- **What "secondary CarPlay stream" normally implies:** a second *decoded video* stream (Apple CarPlay second
  display). Path would be: authenticated second stream → decoder → renderer → cluster sink.
- **ClarityLink side (partially implementable):** the transport/decoder/renderer pieces exist or are modeled
  (`frame_gate.py`, existing receiver/renderer). The **independent** stream identity/lifecycle/freshness is done.
- **Blockers (UNSUPPORTED / UNKNOWN):** (a) a **legitimately authenticated** second CarPlay stream needs an
  **authorized receiver** (hardware + auth) — the factory native binding admits **one** screen (singleton,
  code-confirmed, report 05); (b) a **safely admitted cluster video sink** — the factory cluster path is *semantic*,
  with **no evidence it accepts arbitrary video**.

## Critical caveat (do not overclaim)
**The factory rendering turn-by-turn Views does NOT mean the factory can render full Apple Maps/Waze video on the
cluster.** The cluster's factory input is structured data; there is no evidence of a factory contract that accepts a
general video frame stream for the cluster. A "Type111 video to the cluster" therefore would **not** ride the
factory's structured-nav path and would require an independent renderer plus a cluster video sink that is currently
**UNSUPPORTED IN REVIEWED EVIDENCE**.

## Compatibility matrix
| Element | Contract 1 (structured TBT) | Contract 2 (Type111 video) |
|---|---|---|
| Matches factory cluster input mechanism | YES (semantic) | NO (factory cluster is not a video sink in evidence) |
| ClarityLink can produce it offline | YES (G-04 model) | PARTIAL (transport/decoder/renderer; stream modeled) |
| Legitimate second-stream authentication | n/a (no second CarPlay stream needed) | UNSUPPORTED (needs authorized receiver) |
| Supported admission to factory cluster | UNSUPPORTED (no API; HondaHack route unauthorized) | UNSUPPORTED/UNKNOWN |
| Type110 continuity preserved | YES (independent) | YES (independent) — if a separate receiver is used |
| Warning precedence preserved | UNPROVEN (U-05) | UNPROVEN (U-05) |
| Physical cluster aperture known | NO (U-04) | NO (U-04) |

## Recommendation (consistent with report 09, Option E)
Build and verify the **independent offline components** for both contracts (structured-nav model + stream/transport/
renderer) and keep **all factory-facing admission inert**. Treat Contract 1's delivery path and Contract 2's
authentication + cluster-video-sink as **open gates** requiring authorized hardware, a supported admission contract,
read-only runtime evidence (report 11, separate approval), and independent safety review. Do not represent either
contract as integrated. `safeForHonda() == false`.
