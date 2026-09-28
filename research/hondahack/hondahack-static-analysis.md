# HondaHack targeted static analysis

**Artifact:** installed cn.autohack.hondahack 7.7.7 APK copied read-only from /data/app/cn.autohack.hondahack-2.apk; SHA-256 5013b478ddd95b01d8f3866fa533d2cd2da5629d6bb609c03c3d816e836afb73. The binary is ignored and is not part of Git.

**Tools:** repository-local JADX 1.5.6 and the existing decompiled Honda ExternalDisplayOutService sources. Decompiled APK output remained in /tmp. The APK packages libnative.so, libxposed.so, and libmp3lame.so; no JNI/native function participates in the traced Screen Casting output path.

## Screen Casting symbols and methods

| Caller | Method | Observed behavior | Target / evidence |
|---|---|---|---|
| MyService | a(int,int), special:enable_screen_cast branch | Sets enable_custom_meter, toggles enable_screen_cast, schedules refresh. | Preference/broadcast control path; decompiled lines around 622–630. |
| C0270ua | receiver onReceive; d(), e(), a(Bitmap) | Handles START_CAST/STOP_CAST; sets bitmap to screen_cast ImageView. | HondaHack overlay view; source around 150–175, 1071–1075, 1368–1456. |
| C0170b | handleLoadPackage and nested receiver d() | Xposed targets Honda ExternalDisplayOutService and resolves InterfaceWindow main/interrupt root views; inserts C0270ua using addView(view, 0). | Existing Honda window/view hierarchy; source around 250–310 and 1580–1775. |
| ne | hook for TakeScreenshotService$1.handleMessage | Gets display-0 token, invokes nativeScreenshot at 400×240, copies ARGB pixels to MemoryFile and passes PFD through Messenger. | Capture source only, not output; source lines 53–121. |
| C0170b.j | handleMessage switch 100/101/102 | Reads 384,000 bytes into Bitmap.createBitmap(400,240,ARGB_8888) and calls receiver callback. | IPC transport; source around 988–1030. |
| Honda InterfaceWindow | createInitScreen, getMainLayout, createWindowParameter | Creates full-window external display surfaces (type 2006) and exposes main/interrupt root views. | OEM source lines 75–145 and 543–555. |

No traced output call opens a framebuffer or uses EGL/ANativeWindow. SurfaceControl/Surface is used for built-in display capture only.

## Advanced Meter relationship

Advanced Meter is a custom C0270ua view injected into the same Honda external-display root. It shows meter/navigation widgets rather than captured display pixels. The live Display 1 output changes while the named MeterActivity window remains on Display 0. WindowManager identifies the externaldisplay process (uid 10056) as the owner of Display 1 full-screen windows. This supports a shared external-display overlay backend with different content; it does not mean the named MeterActivity surface itself is assigned to Display 1.

## Evidence and limits

- **Confirmed:** Screen-capture source is Display 0, requested 400×240, ARGB_8888; IPC uses a 384,000-byte MemoryFile/PFD; cast bitmap is assigned to HondaHack ImageView; the view is inserted into the Honda external-display hierarchy; Display 1 is 800×480 full-frame.
- **High confidence:** Advanced Meter and Screen Casting share Xposed-injected externaldisplay host/view infrastructure.
- **Unknown:** exact physical navigation bounds, downstream mask/crop, supported standalone replacement for the Xposed hook, and any stable public Binder interface.
- **Not evidenced:** direct framebuffer output, native decoder-to-Surface output, or a public arbitrary-view Binder API.

Line references refer to local JADX 1.5.6 output from the captured APK. Method/class names are the stable anchors.
