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

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.
