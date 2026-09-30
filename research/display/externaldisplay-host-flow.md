# Step 42A — ExternalDisplay host flow

## Static process path

```text
ExternalDisplayOutReceiver / system startup
  -> ExternalDisplayOutService.onCreate()
  -> InterfaceWindow / ContentsManager initialization
  -> WindowManager adds bottom, main, interrupt full-window roots
  -> regular Honda content Views are inserted into those roots
  -> Android external Display 1 (HDMI / 800x480)
```

The service binds to Honda AP services (including `IExternalDisplayApService`, `INavigationApService`, and `ICarPlayApService`) as a **client** and registers callbacks for UI/control state. It is the rendering/window owner. Its own exported service `onBind` returns null. `InterfaceWindow` static root getters and `addView` are in-process methods, not an IPC interface.

## What the host can draw

Honda views, text, images, and other regular Android view content are drawn inside the host's WindowManager roots. Existing HondaHack proof shows a screen-cast `Bitmap` set on an ImageView and a custom View inserted through Xposed into the root. That confirms Android view composition is possible when code executes in the host process. It does not prove that this service can accept a CarPlay H.264/ScreenStream socket or that a decoded Type 111 frame can be delivered to it through a supported interface.

## Lifecycle and geometry limits

The tracked static source shows main and interrupt roots are initialized and removed with the service's window lifecycle. Live snapshots previously documented Display 1 as 800×480, but safe-map bounds/crop are not established. HondaHack's own layout sizes are local to that app and are not a proven factory map viewport. No new capture or runtime observation was made for Step 42A.

## Decision

```text
RENDER HOST: HONDA CONFIRMED
PROCESS: com.mitsubishielectric.ada.app.externaldisplay
VIEW INSERTION: HONDA CONFIRMED IN-PROCESS
EXTERNAL BINDER VIEW HANDOFF: NOT FOUND
SURFACE/DECODER INPUT: NOT FOUND
FRAME DELIVERY FROM JMCS: UNKNOWN / no IPC contract recovered
```
