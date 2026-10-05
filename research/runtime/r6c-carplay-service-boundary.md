# R6C Android service boundary

`CarPlay.apk` is the foreground UI consumer. `CarPlayService.apk` provides exported `CarPlayApService` Binder UI/state functions. `CarPlayApServiceApiLib` declares callback registration for app/phone/navigation/Siri categories, call/audio and display controls, touch/main-window state, and status. The service binds ExternalDisplay and Navigation services. See the [R3C service audit](43t1-r3c-honda-service-boundary-audit.md) and [API surface](../carplay/carplayservice-api-surface.md).

No recovered method carries a raw iAP2 handle, authentication context, AirPlay request/response, session socket, stream key, or ScreenStream frame. `setVideoPath` controls an AV route, not a frame sink. The service process name/UID and any native-to-service private status IPC are not fully established. This is a scoped static negative finding: Binder's visible public interface is not the R6B handoff.
