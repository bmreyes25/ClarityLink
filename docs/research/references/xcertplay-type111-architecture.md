# xcertplay Type111 architecture

## Pinned source

Analysis is pinned to [shilapi/xcertplay `1298fb35e29ee30e7bd849cb0e751b52aa22a13f`](https://github.com/shilapi/xcertplay/tree/1298fb35e29ee30e7bd849cb0e751b52aa22a13f), inspected 2026-10-20. The repository declares GPL-3.0. This is source-level analysis, not independent runtime validation.

## Control and stream shape

```text
iPhone control /info
  -> main display descriptor (UUID ...1111..., stream 110)
  -> alternate descriptor (UUID ...2222..., stream 111) only after
     paired altScreen + uiContext negotiation and event-channel setup
  -> Type111 SETUP gated on accepted alternate-screen negotiation

session + stream type + connection identity
  -> ScreenStream: config / frames / keyframe recovery
  -> MediaSink: local decode OR copied compressed access units to MediaTap
  -> separate /main and /cluster web channels (HTTPS, browser decode)
```

The UUIDs shown are the source's example constants, not universal CarPlay UUIDs. `AirPlayInfoPlist.kt` contains descriptor geometry, safe-area/view-area fields, frame-rate and feature properties, selection state, and optional initial URL. `AirPlaySession` recognizes stream types 110 and 111; Type111 setup is gated by the negotiated alternate-screen capability. The source handles `altScreen` and `uiContext` as a pair and requires event-channel/configuration conditions. These are xcertplay behaviors, not a universal protocol rule.

`CarPlayMediaEngine` keys streams by session and type and associates connections; it routes configuration and frames through the stream/sink callbacks. `ScreenStream` consumes the AirPlay header/body and produces configured, length-prefixed access units; its conversion path and ownership are explicit in source. `AndroidMediaSink` can decode locally or forward a copy of compressed data to `MediaTap`; it closes the leased access unit after forwarding when no preview retains it.

The web factory exposes `/main` and `/cluster`; the project separates main controls/audio from view-only cluster output. Browser code uses WebCodecs with MSE fallback. Source implements bounded queues and keyframe recovery. The cluster service binds all interfaces on HTTPS port 8080 with self-signed trust; source checks WebSocket origin/host but documents no user authentication. Treat this as a LAN-exposure and trust limitation.

## Lifecycle evidence and limits

Explicit stream teardown is type-specific. The inspected `ScreenStream.onClosed` path removes its stream and calls session close; therefore unexpected stream EOF can terminate the whole session despite stream-key isolation. Web viewers may reconnect while the server persists, and closed sessions gate stale frame forwarding. These are code-path findings; test evidence is catalogued in [source provenance](source-provenance.md). Source tests cover negotiation, setup ordering, teardown, forwarding, queue pressure, and recovery. No genuine iPhone Type111 session was independently verified for this campaign.
