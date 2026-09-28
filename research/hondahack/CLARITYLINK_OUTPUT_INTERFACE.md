# ClarityLink Display 1 output interface

**Prototype status: host renderer abstraction complete; Android/Honda attach backend is a skeleton requiring a privileged integration hook. No hardware output has been tested.**

## Evidence-backed output contract

| Field | Current contract |
|---|---|
| Android display | Display 1, HDMI/external, 800×480 at about 60 Hz |
| Layer stack | 1, assigned by Android to Display 1 |
| Host owner | com.mitsubishielectric.ada.app.externaldisplay creates the external full-screen windows |
| View creation path | HondaHack Xposed-injects a regular Android View into InterfaceWindow.getMainLayout()/external-display root |
| Honda Binder API | None in the traced renderer path; access to the root is via code in/hooking externaldisplay |
| Native library/framebuffer | Not used by the traced output path |
| View canvas | Outer window 800×480. HondaHack Civic layout root 584×215 local px; cast image region (0,24,584,191) uses fitXY. This is a layout-local candidate, not a verified physical safe area. |
| Pixel format | HondaHack input bitmap ARGB_8888, 400×240. Display 1 fbdev format unknown (bits_per_pixel=0). |
| Lifecycle | Attach only while externaldisplay main root exists and Navigation page is active; clear/detach on root destruction, navigation exit, display removal, or renderer failure. The safe host lifecycle hook is not implemented. |
| Failure behavior | Remove ClarityLink overlay and leave Honda's original UI visible. Do not write framebuffer or leave stale frames after detach. |

## Prototype boundary

src/claritylink-renderer/ separates FrameSource, ClarityLinkRenderer, and Display1OutputBackend. Its Python backend validates metadata and simulates attach/submit/clear/destroy. The API 17 Java skeleton draws CPU ARGB frames in a normal View attached to an injected FrameLayout host. The caller must provide a viewport; it does not claim HondaHack's local layout as the factory physical rectangle.

The future decoded-frame contract includes width, height, pixel format, row stride, presentation timestamp, rotation, crop, and CPU-buffer versus Surface-backed storage. Surface-backed input is represented but unsupported by the current Canvas/mock backend. Zero-copy decoder output requires a separate API 17 Tegra/MediaCodec investigation.

## Remaining integration work

1. Establish an allowed, lifecycle-safe way to obtain the externaldisplay root (HondaHack currently uses Xposed/private classes).
2. Confirm the physical Navigation viewport before showing a live stream.
3. Demonstrate API 17 decoder output and pixel-format support before choosing a zero-copy path.
4. Remove the overlay and restore Honda UI immediately if its host disappears or Navigation is no longer active.

No second CarPlay Identification/session or H.264 decoder is implemented here.
