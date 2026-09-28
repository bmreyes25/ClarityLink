# HondaHack Display 1 output path

**Status: output path traced to Honda's external-display Android window/view hierarchy. The exact physical cluster crop and a standalone ClarityLink host adapter remain unverified.** This report uses a local copy of the installed HondaHack 7.7.7 APK plus existing live read-only snapshots. No vehicle was accessed for this milestone.

## Screen Casting call path

1. HondaHack's MyService preference handler for special:enable_screen_cast sets enable_custom_meter, toggles enable_screen_cast, and schedules the meter refresh.
2. HondaHack's Xposed module hooks com.android.systemui.screenshot.TakeScreenshotService$1.handleMessage. It gets built-in display token 0 and invokes the hidden nativeScreenshot method (Surface before API 18; SurfaceControl on API 18+), requesting 400×240.
3. The captured ARGB_8888 bitmap is copied to a 384,000-byte MemoryFile (400×240×4) and transferred through Messenger with a duplicated ParcelFileDescriptor. A HondaHack handler reconstructs the Bitmap and invokes its receiver callback.
4. C0270ua.a(Bitmap) assigns the bitmap to the screen_cast ImageView. HondaHack's Civic meter layout has a 584×215 px root; screen_cast_layout has 24 px top padding and a match-parent ImageView with fitXY, giving a 584×191 local image region. This is a HondaHack layout-local size, not a measured physical cluster rectangle.
5. HondaHack's Xposed code targets com.mitsubishielectric.ada.app.externaldisplay, resolves InterfaceWindow.getMainLayout()/getInterruptLayout(), and inserts its custom view into the external-display root. Honda's InterfaceWindow.createInitScreen() creates full-window layouts with WindowManager.LayoutParams width/height MATCH_PARENT, type 2006. Live WindowManager records show the externaldisplay process (uid 10056) owns full-frame 800×480 windows on Display 1.

**Path:** Display 0 screenshot → 400×240 ARGB bitmap → shared-memory IPC → HondaHack ImageView in an Xposed-injected view → Honda ExternalDisplayOutService main/interrupt window hierarchy → Android Display 1 / layer stack 1 → downstream Honda cluster path.

## Live correlation

| State | Display 1 evidence | Interpretation |
|---|---|---|
| Factory Navigation | 800×480 frame contains compass/grid and Menu; the physical photo additionally shows stock gauges/indicators | Display 1 contributes to cluster Navigation content, but is not a full capture of physical cluster UI. Exact physical crop/composition unknown. |
| Advanced Meter | 800×480 image changes to compass/vehicle data; Display 1 layers stay full-frame. Named MeterActivity window is on Display 0. | HondaHack view/output can change external content; static Xposed path locates its view injection in externaldisplay. |
| Screen Casting | 800×480 image is distinct; cluster settings content and Menu appear over a black remainder. Externaldisplay owns Display 1 full-frame windows. | Runtime screen changes and static call graph agree on the externaldisplay overlay route. |

SurfaceFlinger reports full [0,0,800,480] source and destination frames for Display 1 in all states. No smaller Android Display 1 crop/destination is observed. The physical photo contains UI absent from the Display 1 capture, so downstream composition/masking is plausible, but this evidence cannot distinguish cluster hardware masking from another downstream renderer.

Surface/SurfaceControl is used for capturing the built-in display only. The traced output does not use DisplayManager, Presentation, VirtualDisplay, direct framebuffer writes, EGL, or a JNI/native output renderer. Output is a regular Android View added to Honda's existing ExternalDisplay hierarchy. Standalone access to this privileged host cannot be assumed; HondaHack uses Xposed integration.

## Exact remaining limits

- HondaHack's output attach path is identified: inject/host a View in InterfaceWindow.getMainLayout() within com.mitsubishielectric.ada.app.externaldisplay. A production-safe ClarityLink adapter must establish supported ownership/lifecycle without HondaHack's private hook.
- Capture input is confirmed 400×240 ARGB_8888; HondaHack displays it with fitXY in a 584×191 local image area. This does not prove physical cluster destination bounds or native pixel format.
- Advanced Meter uses the same injected C0270ua custom-view infrastructure; meter/navigation callbacks populate the widgets.
- No raw framebuffer read/write was done. No direct /dev/graphics/fb* dependency was found in this output path.

## Evidence references

- Local ignored APK: research/hondahack/artifacts/hondahack-installed.apk, package cn.autohack.hondahack, version 7.7.7, SHA-256 5013b478ddd95b01d8f3866fa533d2cd2da5629d6bb609c03c3d816e836afb73.
- Decompiled APK classes used locally: C0170b.java, C0270ua.java, ne.java, C0240oa.java; generated source is not copied into Git.
- Honda source: research/decompiled/ExternalDisplayOutService/sources/com/mitsubishielectric/ada/app/externaldisplay/interfaces/InterfaceWindow.java.
- Existing snapshots and PNGs are local/ignored under research/captures/hondahack-display-path/20260928T152742Z/.
