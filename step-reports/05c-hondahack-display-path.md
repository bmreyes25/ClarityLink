# Step 5C — HondaHack Display 1 output path

**Status: output path traced; cluster physical crop unresolved.** Live data collection is complete and the car is not needed for offline follow-up.

HondaHack Screen Casting captures the built-in display at 400×240 through hidden Surface/SurfaceControl.nativeScreenshot, transports ARGB_8888 pixels in a 384,000-byte MemoryFile over Messenger/PFD IPC, and assigns each bitmap to an ImageView inside its custom meter View. HondaHack's Xposed module inserts that view into the Honda com.mitsubishielectric.ada.app.externaldisplay InterfaceWindow main/interrupt root. Honda creates full-window external display surfaces through WindowManager; live WindowManager records identify externaldisplay uid 10056 and Display 1 at 800×480/layer stack 1.

Advanced Meter uses the same externaldisplay Xposed/view injection infrastructure but shows HondaHack meter/navigation widgets rather than captured display pixels. The named MeterActivity SurfaceFlinger layer is on Display 0; it is not the Display 1 output layer.

## Geometry

SurfaceFlinger reports full [0,0,800,480] bounds and no smaller Display 1 crop in factory Navigation, Advanced Meter, or Screen Casting captures. HondaHack's Civic layout has a 584×215 local root and cast ImageView region (0,24,584,191) using fitXY. This is a HondaHack view-local candidate, not the measured factory Navigation destination. The physical photo shows speedometer, power/charge, range, and status UI absent from the Display 1 image, which supports downstream composition but does not prove a hardware mask.

## ClarityLink consequence

The practical rendering target is a View hosted in Honda's externaldisplay main layer/window, not direct framebuffer I/O or a DisplayManager-created Presentation. ClarityLink would need access to that process's view root (HondaHack gets it through Xposed/private classes) and draw decoded frames there. The offline mock validates the frame/backend lifecycle contract, but the API 17 device adapter still needs permitted root acquisition and physical viewport confirmation. Zero-copy decoder Surface routing is not established.

## Evidence

- Static detail: research/hondahack/hondahack-static-analysis.md
- Output contract: research/hondahack/CLARITYLINK_OUTPUT_INTERFACE.md
- Raw state snapshots/checksums: ignored research/captures/hondahack-display-path/20260928T152742Z/
- Local APK remains ignored; package/version/hash are recorded in the static analysis report.

## Decision

SCREEN_CAST_PROCESS: SystemUI screenshot hook plus HondaHack Xposed module; output View hosted in Honda ExternalDisplay window hierarchy
SCREEN_CAST_RENDERER: Android ImageView/View drawing a Bitmap
SCREEN_CAST_DISPLAY_ID: Display 1 output; Display 0 capture source
SCREEN_CAST_LAYER_STACK: 1
SCREEN_CAST_BUFFER_SIZE: capture 400×240 ARGB_8888; external canvas 800×480; HondaHack local image region 584×191
SCREEN_CAST_OUTPUT_API: Xposed hook into InterfaceWindow root; regular Android View
ADVANCED_METER_PATH: same externaldisplay root/view injection; content-specific meter widgets
SHARED_BACKEND: YES for host/view path; content differs
ANDROID_DISPLAY1_CANVAS: 800×480 full frame
ANDROID_SMALLER_NAV_CROP: NOT OBSERVED in SurfaceFlinger
DOWNSTREAM_CLUSTER_MASK_OR_COMPOSITION: PLAUSIBLE; physical transform unresolved
STEP 2 OUTPUT PATH: COMPLETE
STEP 3 HOST RENDERER: COMPLETE; Android host integration skeleton only
STEP 4 IDENTIFICATION: NEXT / unresolved
