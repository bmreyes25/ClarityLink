# Step 42A — ExternalDisplay service API surface

## Components and ownership

| Component | Evidence | Role |
|---|---|---|
| `com.mitsubishielectric.ada.appservice.externaldisplay.ExternalDisplayApService` | `research/resources/ExternalDisplayApService/AndroidManifest.xml`; decompiled `ExternalDisplayApService.java`; `ExternalDisplayLib/IExternalDisplayApService.java` | Exported AP/control Binder for LVDS status, meter contents, channel/info updates, interrupt handling, callbacks and diagnostics. |
| `com.mitsubishielectric.ada.app.externaldisplay.ExternalDisplayOutService` | `research/resources/ExternalDisplayOutService/AndroidManifest.xml`; decompiled service and `interfaces/InterfaceWindow.java` | Persistent Android process that creates full-window overlays and draws Honda UI on external Display 1. |

## Binder contracts

`ExternalDisplayApService` is manifest-exported and has an intent action matching `IExternalDisplayApService`. Its Binder surface includes `notifyLvdsDisplayOperationStatus`, `notifyLvdsDisplayingStatus`, `notifyLvdsInterrupt`, `notifyChannelData`, `notifyNewInfo`, meter contents/data/configuration requests, meter interruption, and event/customization/diagnostic callbacks. Arguments are booleans, integers, strings, and Honda parcelable control objects. No method accepts `View`, `Surface`, `SurfaceTexture`, `Bitmap`, pixel buffers, H.264 data, ScreenStream socket/Fd, or a CarPlay stream descriptor.

Its manifest does not declare a `service android:permission` gate. This means no component-level bind permission is visible in this manifest. Whether a caller can successfully use every method still depends on Android package/signature/permission grants and method-level checks; this static audit does not claim unrestricted runtime access. The manifest itself requests `WRITE_MEDIA_STORAGE` and Honda `VEHICLE_RW`.

`ExternalDisplayOutService` is also marked exported, but its `onBind(Intent)` returns `null`. It is not a usable Binder frame/view endpoint. Its manifest requests `SYSTEM_ALERT_WINDOW` and `INTERNAL_SYSTEM_WINDOW`, among other permissions. Their effective grants/signing conditions on this unit were not revalidated here.

## Renderer API boundary

The external-display window owner has static in-process methods `InterfaceWindow.getMainLayout()`, `getInterruptLayout()`, and `addView(int, View, boolean)`. `createInitScreen` creates the root `FrameLayout`s and attaches them using its `WindowManager`. The regular-View output route is independently corroborated by existing HondaHack static analysis; HondaHack obtains access by Xposed injection into `com.mitsubishielectric.ada.app.externaldisplay`, not through the AP Binder API.

No supported cross-process arbitrary content API was found in the checked-in Binder interfaces. Adding a `Surface` or frame-stream transaction would be new functionality. A third-party caller must not assume it can call package-private/static root APIs in another app process.

## Decision

```text
EXTERNALDISPLAY API SURFACE: FOUND (control Binder) / NOT FOUND (video-frame or View handoff)
MANIFEST EXPORTED: YES for both service declarations
COMPONENT BIND PERMISSION: NONE DECLARED
RUNTIME CALL PERMISSION: UNKNOWN
NON-JMCS OUTPUT OWNER: YES, ExternalDisplayOutService process
PUBLIC ARBITRARY VIEW/SURFACE/H264 API: NOT FOUND
```

Sources: manifests under `research/resources/{ExternalDisplayApService,ExternalDisplayOutService}`, decompiled sources under `research/decompiled/{ExternalDisplayApService,ExternalDisplayOutService,ExternalDisplayLib}`, plus [HondaHack output path](../hondahack/hondahack-display-path.md).
