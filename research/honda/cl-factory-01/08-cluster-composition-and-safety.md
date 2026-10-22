# CL-FACTORY-01 / M3 — Cluster composition & safety boundaries (sanitized)

Status: IN PROGRESS. Evidence OBSERVED_STATIC. Offline only. `safeForHonda() == false` (unchanged, non-negotiable).
This report states safety **limits**; it does not certify any safe integration.

## What the evidence establishes (PROVEN_STATIC)
1. The factory cluster Navigation path is **semantic**: structured turn-by-turn data is sent to a host that renders
   Android Views. ClarityLink can therefore model an *independent* renderer for structured nav data without
   capturing factory pixels.
2. The factory host composes in **two layers**, with a dedicated **interrupt/warning layer** that preempts the main
   layer. A factory warning-precedence mechanism **exists**. (G-02) Mechanism confirmed: main and interrupt are
   **separate top-most-ordered windows** (interrupt attached last, above main), not one shared view tree, so a
   factory interrupt composites above main content while the main tree is preserved. This is static add-order
   evidence, not a runtime precedence guarantee (see U-05).
3. The host renders onto an existing Android **Display 1**; it does not create that display.
4. (G-03) The host is **self-healing against the display link dropping**: on display removal it tears down its
   window stack and stands content down; on display return it performs a **validity-gated** rebuild and resume, and
   refuses to attach to an invalid display (fail-closed). This protects the factory's **own** content only.

## What the evidence does NOT establish (UNKNOWN / UNSUPPORTED)
- **Warning precedence under third-party content (U-05):** that the interrupt layer's precedence is *preserved* when
  non-factory content is injected into (or composited with) the host. G-02 proves the factory *attaches* the
  interrupt window above the main window at init; it does **not** prove that ordering is guaranteed at runtime among
  same-type windows, nor that it survives in-process third-party code, which could perturb measure/layout/focus, add
  to the interrupt window, or change window params. HondaHack inserted into the main layer (nominally below
  interrupt), but **precedence preservation under injected content remains UNPROVEN.**
- **Content behavior across a host teardown/rebuild (G-03 limit):** the validity-gated rebuild protects factory
  content, but whether injected/third-party content is cleanly removed, and how warnings behave during the
  teardown→rebuild gap, is **UNKNOWN** (runtime-only).
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
