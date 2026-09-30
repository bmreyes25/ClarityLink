# Step 42A — companion rendering path assessment

## Current path

Honda already has an Android render owner for the external screen: `ExternalDisplayOutService` creates WindowManager roots for Display 1, and its UI uses ordinary Android Views. HondaHack's captured implementation places its custom View inside that process using Xposed and feeds an ImageView from a shared-memory bitmap path. This is evidence that the display can be composed by Android UI code.

## Missing supported handoff

The checked-in `IExternalDisplayApService` Binder provides Honda menu/meter/LVDS control and callbacks, not decoded pixels or a Surface. The exported `ExternalDisplayOutService` component's `onBind` returns null. `InterfaceWindow.addView` is a static Java method that must execute in the ExternalDisplayOutService process; it is not exported through Binder. No Java native declaration, `MediaCodec` integration, `Surface`, `SurfaceTexture`, H.264 or ScreenStream receiver was found in the traced Honda view-output path.

Thus the existing host is a **rendering destination**, not a proven companion plug-in API. A companion that decodes Type 111 elsewhere would still need an explicit secure, lifecycle-safe way to deliver frames or a View to that host. A separate process cannot access its Java root merely because the service is exported.

## Rendering options and status

| Candidate | Status |
|---|---|
| Supported ExternalDisplay Binder accepts pixels/Surface | Not found in interface or manifest evidence |
| Existing `InterfaceWindow.addView` | Present; same-process method, no cross-process contract |
| HondaHack Xposed overlay | Demonstrated prior implementation; not a supported ClarityLink extension mechanism |
| Add a new companion-to-host IPC for decoded buffers | Technically modellable; would require a host-side integration and bounded buffer/lifecycle protocol not present today |
| Decode and render in a separate ordinary app window on Display 1 | Not established; system Display 1 ownership/composition and safe area/permission constraints remain unknown |

No patch, hook, IPC, decoder, or display operation was created in this milestone.

## Step 42B architecture decision

The selected target keeps Type 110 and Type 111 session/control ownership beside the Honda receiver in `jmcs`, then adds a narrowly scoped renderer adapter in the ExternalDisplay host. This is a target design only: neither a supported Type111 handler nor a supported frame handoff exists today. Current active work remains the offline digital twin. The Xposed View path is prior-art evidence for host composition, not authorization or a ClarityLink API.
