# CarPlay decoder and Surface binding

The ELF has a MediaCodec surface setter (`android_mediacodec_set_surface`) and configures a `SurfaceTextureClient` during backend initialization. The active CarPlay attachment has not been joined to this backend, so the following remain unknown:

| Question | Result |
|---|---|
| Active CarPlay caller of surface setter | Unknown |
| Surface creation site/type on CarPlay path | Unknown |
| Surface owner/storage | Unknown |
| Setter per decoder/device instance | Unknown |
| Primary CarPlay Surface host/activity/view/display | Unknown |
| Two Surfaces supported | Unknown |

Backend API availability does not establish that the screen path invokes the setter. Continue from the matched `CarPlay Screen` registration only. See `carplay-decoder.md`, `active-carplay-sink.md`, and `primary-screen-end-to-end.md`.
