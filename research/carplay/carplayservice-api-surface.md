# Step 42A — CarPlay AP service API surface

## Exported Android service and Binder

`research/resources/CarPlayService/AndroidManifest.xml` declares `com.mitsubishielectric.ada.appservice.carplayapservice.CarPlayApService` enabled and exported, with action `com.mitsubishielectric.ada.appservice.carplayapservice.ICarPlayApService`. No service-level `android:permission` is declared. Its `onBind` returns the AIDL-style Binder only for the interface action. Manifest caller permissions, signing, and per-method caller enforcement are not established by this static review.

The library interface `research/decompiled/CarPlayApServiceApiLib/.../ICarPlayApService.java` exposes CarPlay phone/app status, callback registration, call/audio controls, touch and main-window status, display configuration/permission, external-device state, and navigation-related control. It does not accept SETUP plists, `streamConnectionID`, file descriptors, sockets, encoded video, `Surface`, or frame buffers.

`setVideoPath(int)` is not a video-frame sink: `DispControl.setVideoPath` calls `IAvApService.openVideoPath(11)` for mode 0 and `closeVideoPath(11)` otherwise. `setDisplayConfig(DisplayConfig)` is brightness/contrast/tint/density-style configuration, not an AltScreen descriptor or video route.

## Internal service relationships

At creation, `CarPlayApService` binds to the ExternalDisplay AP service and Navigation AP service among its internal service map, and registers service callbacks. `ExternalDisplayOutService` also binds back to CarPlay and Navigation AP services as a UI client. These interfaces coordinate app state, screen ownership, navigation/UI events and meter operations. No connection from the native jmcs Setup response or accepted ScreenStream socket to a Binder-carried display frame was recovered.

## Decision

```text
CARPLAYSERVICE API SURFACE: FOUND (app/session control)
EXPORTED BINDER: YES
MANIFEST COMPONENT PERMISSION: NONE DECLARED
VIDEO/TYPE111 SESSION TRANSFER: NOT FOUND
EXTERNALDISPLAY BINDING: YES, internal AP-service control relationship
CARPLAY SCREEN FRAME SINK: NOT FOUND
```

Sources: `research/resources/CarPlayService/AndroidManifest.xml`, `research/decompiled/CarPlayService/.../CarPlayApService.java`, `DispControl.java`, `research/decompiled/CarPlayApServiceApiLib/.../ICarPlayApService.java`, and `research/resources/ExternalDisplayOutService/AndroidManifest.xml`.
