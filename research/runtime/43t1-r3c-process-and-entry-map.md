# 43T1-R3C expanded — process and entry map

```mermaid
flowchart TD
  Phone[iPhone] -->|HONDA_CONFIRMED AirPlay control| J[jmcs]
  J --> Dispatch[request dispatch]
  Dispatch --> Setup[AirPlayReceiverSessionSetup]
  Setup --> Resp[response construction]
  Resp --> Serializer[plist serializer / HTTP send]
  Setup --> Stream[stream/media lifecycle]
  Stream --> Final[teardown / finalization]
  J -->|HONDA_CONFIRMED DT_NEEDED + PLT proxy registration| Proxy[libcarplay_proxy.so]
  Proxy -->|HONDA_CONFIRMED single callback record| Screen[stock ScreenStream callbacks]
  J -->|INFERENCE app status bridge; no Setup payload proven| Service[CarPlayService.apk / CarPlayApService]
  Service -->|HONDA_CONFIRMED Binder binding| External[ExternalDisplay services]
  Service -->|HONDA_CONFIRMED Binder binding| Nav[Navigation services]
  App[CarPlay.apk foreground UI] -->|HONDA_CONFIRMED service client| Service
  J -.->|UNKNOWN project entry: none evidenced| Project[project-owned process/sidecar]
  Project -.->|UNKNOWN no native session correlation| Final
```

Within `jmcs`, Dispatch→Setup→response→serializer is `HONDA_CONFIRMED` static control flow from [R3A](43t1-r3a-setup-path-seam-map.md). `jmcs`→proxy is a genuine dynamic boundary but leads to fixed stock media callbacks, not Setup. The app-service relationship is confirmed for status/display coordination in [service audit](43t1-r3c-honda-service-boundary-audit.md); any specific native Setup payload route across it is `UNKNOWN`, so the diagram does not claim one. Other linked libraries include Binder, Stagefright, media, GUI, crypto, and `libdl`; [dependency graph](jmcs-dependency-graph.md) gives the exact set.

Potential extension points assessed: proxy register (`REJECT_REPLACEMENT`), generic screen array (`REJECT_NO_SETUP_CONTEXT`), app-service callback (`REJECT_TOO_LATE`), direct Setup/serializer (`REJECT_RUNTIME_WRITE`), loader/preload (`REJECT_PERSISTENCE`), and hypothetical independent sidecar (`REJECT_NO_EVIDENCE`). [Matrix](43t1-r3c-extension-path-matrix.md) records all gate fields.
