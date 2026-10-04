# 43T1-R4D — framework and window policy audit

## Scope and evidence

Offline review of preserved Honda framework/configuration evidence and version-matched AOSP Android 4.2.2/API 17 sources. No device/framework query was made. Labels distinguish `HONDA_STATIC`, `DOCUMENTED_ANDROID`, `AOSP_API17_DOCUMENTED`, `INFERENCE`, `UNKNOWN`, and `REJECTED`.

| Surface | Evidence and finding | Label |
|---|---|---|
| `DisplayManager` / `Display` | API 17 enumerates logical displays and selects presentation displays by display type. `Display 1` HDMI is captured evidence. Honda's ExternalDisplayOutService enumerates displays and selects the final one, but this OEM choice is not a third-party contract. | AOSP_API17_DOCUMENTED; HONDA_STATIC/OBSERVED; INFERENCE |
| `Presentation` / display context | API 17 `Presentation` creates its own display-bound window/context and handles display removal/configuration. A separate ordinary app can attempt this through public API in generic AOSP; the API does not confer Honda policy approval or reveal physical clipping. | AOSP_API17_DOCUMENTED; Honda result UNKNOWN |
| `WindowManagerService` / `DisplayManagerService` | Preserved evidence does not include a complete, build-matched Honda framework source/decompilation or policy trace sufficient to reconstruct their per-display admission decisions. Do not infer Honda equality with AOSP. | UNKNOWN |
| `PhoneWindowManager` / `WindowManagerPolicy` / `PolicyManager` | AOSP API17 policy checks window-type permissions. No preserved Honda policy source or binary comparison establishes an OEM delta, package allowlist, or trusted-process check for Display 1. | AOSP_API17_DOCUMENTED; Honda delta UNKNOWN |
| Window type 2006 | AOSP API17 names 2006 `TYPE_SYSTEM_OVERLAY` and checks `SYSTEM_ALERT_WINDOW`; other privileged system window types use signature-level `INTERNAL_SYSTEM_WINDOW`. Honda's three full-frame roots use 2006. This says nothing conclusive about ordering between Honda roots and a new app window on this head unit. | AOSP_API17_DOCUMENTED; HONDA_STATIC; z-order UNKNOWN |
| ActivityManagerService / `ContextImpl` | API17 public display context and `Presentation` exist. Preserved artifacts do not show ActivityManager refusing ordinary app access by UID, nor a Honda package-name exception. There is no public API17 target-display activity launch API. | AOSP_API17_DOCUMENTED; Honda admission UNKNOWN |
| Trusted display / system UID | Display 1 being Honda-owned for its existing root does not prove the display is trusted-only. Existing Honda display owner has UID 10056 and no shared UID in the saved package record. No permission/policy record ties that UID to a Display 1-only trust gate. | UNKNOWN |
| Hardcoded package checks | No hardcoded package check was located in the preserved relevant evidence set; the framework policy implementation is incomplete, so absence from this search is not proof none exists. | UNKNOWN |

## Answers

- Is ordinary-app `Presentation` blocked by framework policy? **Not established.** Generic API17 provides the mechanism; Honda policy admission is unknown.
- Does display-context window creation inherently require system permission? **Not for every public `Presentation` in generic AOSP.** Certain system window types do. Honda's policy and target display behavior remain unknown.
- Does Display 1 require a trusted process or special UID? **Unknown.** No positive evidence was found; absence of an observed gate is not proof of ordinary access.
- Does Honda patch WindowManager policy compared with AOSP? **Unknown.** No complete matching source/binary diff was available.
- Are hardcoded package checks or display-type restrictions present? **Unknown on Honda.** API17 display-category behavior is type-based; no Honda app-facing Display 1 policy result was preserved.

**Finding:** `Presentation` remains `POSSIBLE_BUT_UNPROVEN`; no framework-level supported admission claim is made. See [package grants](43t1-r4d-package-grants-permission-resolution.md), [admission matrix](43t1-r4d-app-window-admission-matrix.md), and [warning/z-order review](43t1-r4d-warning-zorder-static-evidence.md). @ECC review retained unknowns instead of converting missing source into a negative finding.
