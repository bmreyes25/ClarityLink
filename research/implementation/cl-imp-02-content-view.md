# CL-IMP-02 — API 17 hosted content View

**Status:** project-owned decoded-frame View and simulator adapter implemented. All displayed pixels in this milestone are synthetic lab frames.

## Reused renderer path

`DecodedFrame` remains the renderer input contract. Its API 17 implementation now snapshots the caller's RGBA bytes into owned read-only storage, validates row-stride arithmetic with wide integers, rejects negative timestamps, and caps one frame including row padding at 4 MiB. The view does not retain a caller-mutable `ByteBuffer`. In the worst pipeline overlap, two owned frame snapshots, one conversion `int[]`, one bitmap being built, one pending bitmap, and one displayed bitmap fit within an approximate 24 MiB pixel-payload ceiling (six 4 MiB buffers), excluding Android object/allocator overhead and caller-owned decoder input. The 4 MiB per-frame admission check is performed before copying.

`Display1OutputBackend` now uses `ClarityLinkContentView` rather than a private duplicate render View. It applies the existing bounded viewport, generation, host-admission and navigation checks. `HondaStyleSimulatorRendererHost` adapts it only to `HondaStyleDisplayHostSimulator`; the adapter does not obtain or search for any Honda root.

## View and lifecycle contract

- A positive session generation is required. Stale generations, non-monotonic presentation timestamps, frames received while suspended, and nonzero rotation are rejected.
- Input conversion runs on a lazily started API 17 `HandlerThread`. The converter holds one replaceable pending frame and one replaceable pending bitmap; it drops an older converted frame when a newer frame is waiting.
- A clear increments a frame epoch so an in-flight conversion cannot repaint cleared content. Frame crop is drawn with aspect fit inside the measured View bounds; resize invalidates the view and recalculates the destination rectangle.
- The simulator warning callback clears current and queued pixels immediately and rejects frames while the warning is visible. Clearing the simulated warning accepts new frames but never restores the previous bitmap.
- Navigation exit, content detach and host close clear frames, close the View and stop its worker. Re-entry requires a new View/session generation.
- The existing Surface and Presentation lifecycle remains separate. This CPU-backed custom View consumes already-decoded RGBA frames; Type111 decoding and a decoder-to-Surface path are later milestones.

## Verification

The API 17 Java checks exercise owned frame snapshots, row stride, channel layout, timestamp validation, allocation bounds, the existing policy adapter and 100 simulator lifecycle cycles. The isolated x86/API 17 emulator probe uses the real renderer backend and simulated host, draws synthetic red and green frames into a Canvas, verifies clearing queued/uninstalled content before a fresh same-timestamp frame, resize, warning blanking, rejection while preempted, fresh-frame resume, and navigation teardown. The implementation's frame epoch also fences in-flight conversions, but this probe does not synchronize on that race and is not evidence of a deterministic in-flight conversion test. The same run retains invalid-display, permission-denial, Presentation/Surface lifecycle, display-removal and process-death checks.

These checks establish only public Android API behavior and the project-owned synthetic host. They do not establish Honda Display 1 admission, its physical safe area, warning signals/order, Honda Surface ownership, authenticated Type111 negotiation, security delegation, or an authentic iPhone frame. Production Honda integration remains disabled.
