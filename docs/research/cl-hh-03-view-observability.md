# CL-HH-03 — Runtime View observability boundary

## Result

The current project record does not establish runtime measure/layout results, clipping at runtime, final Display 1 composition, or the physical cluster aperture. This task adds a generic bounded recorder for immutable metadata snapshots and synthetic lifecycle tests. It is not an Android hook, Xposed module, adapter, deployment package, or Honda display integration.

`safeForHonda()` remains false. No Honda or vehicle operation was performed.

## Observable metadata versus pixel evidence

An authorized observer running in the relevant process could read, at a specific sample time:

- Main and interrupt roots' measured dimensions, local bounds, visibility and screen location.
- The injected View and ImageView parent chains, attachment state, bounds and visibility.
- `getGlobalVisibleRect()` output, source bitmap dimensions, ImageView scale type and image matrix.
- The View's logical display ID where available. Android documents `View.getDisplay()` as added in API 17; a null result means the View is not attached to a window. Android defines `getGlobalVisibleRect()` relative to the root view and reports Android View clipping, not a physical panel aperture. [Android `View` API reference](https://developer.android.com/reference/android/view/View)
- A redacted, observer-assigned window label. A raw window token is not retained; a token by itself would not establish the owning process or OEM authority.

These observations could establish whether the injected view is attached beneath a particular root, how the Android hierarchy lays it out, and whether the measured interrupt root becomes visible or the main root changes visibility during an ordinary page transition. They would not prove why a warning appeared, warning priority across warning types, compositor output, physical visibility, safe geometry, or authorization for another producer.

## Existing evidence and remaining observation

The available public record does not establish runtime view bounds, final Display 1 composition, a calibrated physical aperture, or warning behavior. No such properties are inferred by the synthetic model.

The smallest passive observation, if separately authorized and if the existing Screen Casting feature is available, is a synchronized external recording of the center display and cluster while using that feature through its existing UI. Record only ordinary page transitions and restoration. Do not induce or wait for warnings. Use a common visible/audible synchronization marker, keep both displays in frame where practical, and record the existing source image only through an already-available supported recording method. Do not install a recording app or change vehicle settings for this proposal. Stop casting through its existing UI and stop recording if a warning appears, the display process restarts, the view freezes, or factory content does not return normally. This can estimate visible pixel correspondence for that observed state; it cannot expose parent chains or Android clipping metadata.

To learn the parent chain and runtime View bounds requires code executing in the Honda external-display process. Any such injection changes process execution and carries crash, stall, lifecycle, privacy, and restoration risks even if it only reads fields. This campaign stops at the offline design and does not build a vehicle-installable payload. Separate independent safety review and explicit authorization would be required before any hardware instrumentation proposal is considered.

## Offline observer model

`src/claritylink-renderer/view_observation.py` accepts only frozen metadata values and exact immutable tuple fields. It cannot receive or retain Android View objects, has no hierarchy mutation or frame-submission API, and accepts only a finite enum of redacted window labels rather than arbitrary tokens. Collection has a fixed caller-selected capacity (maximum 4096 samples), ordered timestamps, a bounded event count, and explicit stop behavior. Unknown bounds, parent chains, attachment and display identity remain unknown. Interrupt-root visibility is recorded as a View state, not interpreted as a warning event or safety priority. Events distinguish node appearance from a proven false-to-true attachment transition and report local/global geometry, screen location, display/window labels, source dimensions, scale type and image-matrix changes.

`tests/renderer/test_cl_hh_03_view_observation.py` uses synthetic fixtures for known/unknown geometry, attachment/detachment, parent replacement, interrupt-root visibility, global-visible bounds, display/window labels, bounded collection, invalid initialization, shutdown, mutable-input rejection and a fake View object with mutation traps. The fake object is rejected; no View mutation is invoked. Tests demonstrate the recorder's value-contract behavior only, not Honda runtime compatibility.

## Evidence gap

The highest-value new passive evidence is a synchronized Display 0/cluster recording across normal page changes and factory restoration. It can answer what pixels are visible. The exact Android parent, clipping and display identity require an authorized in-process observer; visible aperture calibration requires a separately calibrated camera/display pair. Neither result would establish an OEM-authorized frame-admission API or warning guarantee.
