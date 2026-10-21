# CL-FACTORY-01 / M3 — Cluster composition & safety boundaries (sanitized)

Status: IN PROGRESS. Evidence OBSERVED_STATIC. Offline only. `safeForHonda() == false` (unchanged, non-negotiable).
This report states safety **limits**; it does not certify any safe integration.

## What the evidence establishes (PROVEN_STATIC)
1. The factory cluster Navigation path is **semantic**: structured turn-by-turn data is sent to a host that renders
   Android Views. ClarityLink can therefore model an *independent* renderer for structured nav data without
   capturing factory pixels.
2. The factory host composes in **two layers**, with a dedicated **interrupt/warning layer** that preempts the main
   layer. A factory warning-precedence mechanism **exists**.
3. The host renders onto an existing Android **Display 1**; it does not create that display.

## What the evidence does NOT establish (UNKNOWN / UNSUPPORTED)
- **Warning precedence under third-party content (U-05):** that the interrupt layer's precedence is *preserved* when
  non-factory content is injected into (or composited with) the host. HondaHack inserted into the main layer, which
  is nominally below the interrupt layer, but in-process third-party code could still perturb measure/layout/focus
  or the host itself. **Precedence preservation is UNPROVEN.**
- **Admission / caller authorization:** no supported interface admits third-party content; the only demonstrated
  route (HondaHack) is an unauthorized in-process insertion. There is **no OEM lease or delegated ownership**.
- **Physical cluster aperture (U-04):** the Android logical display size (hist. 800×480) does **not** define the
  physical cluster viewport, crop, or mask. No safe rectangle follows from it.
- **Downstream composition:** whether any compositing happens outside the Android components we possess is UNKNOWN.

## Implications for ClarityLink (fail-closed)
- A ClarityLink cluster renderer must treat **factory warnings/interrupts as always-dominant** and must itself
  **withdraw** on any interrupt/warning/unknown host state — it may **not** claim to *enforce* factory precedence.
  This is exactly the posture encoded in `src/claritylink-honda/factory_integration_contract.py`
  (`withdraw_for_warning()` always succeeds; unknown ⇒ deny; `safe_for_honda()` hard-False).
- Any real admission/attachment to the factory host remains **UNSUPPORTED IN REVIEWED EVIDENCE** and is kept inert.
- Physical-safety and warning-priority claims require **separate factory evidence and independent safety review**;
  nothing here authorizes vehicle integration.

## Open safety questions (→ M9 read-only ADB, pending approval)
- Does a live unit expose any supported second-display/second-stream admission not present in the static image?
- What is the real Display-1 topology and the interrupt-layer compositing order at runtime?
- What is the physical cluster aperture/crop?
These require a **read-only** parked-car observation plan (report 11), to be approved separately. No vehicle access
is taken here.
