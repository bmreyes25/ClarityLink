# CarPlay decoder and Surface binding

The ELF has an Android MediaCodec surface setter (`android_mediacodec_set_surface`) and configures a `SurfaceTextureClient` during backend initialization. No evidence connects the active `CarPlay Screen` registry entry or its attach callback to this backend.

| Question | Result |
|---|---|
| Active CarPlay caller of surface setter | Unknown |
| Surface creation site/type on CarPlay path | Unknown |
| Surface owner/storage | Unknown |
| Setter per decoder/device instance | Unknown |
| Primary CarPlay Surface host/activity/view/display | Unknown |
| Two Surfaces supported | Unknown |

Backend API availability does not establish that the screen path invokes the setter. Continue from the proven registration winner and concrete attach callback once recovered. See [carplay-decoder.md](carplay-decoder.md), [device-registration.md](device-registration.md), and [primary-screen-end-to-end.md](primary-screen-end-to-end.md).
