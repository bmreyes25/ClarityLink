# R6C stock audio reuse

`jmcs` compiles `mc_carplay_audio_iap2_attached`, `mc_carplay_audio_init`, AirPlay audio session code, and links Android media, Stagefright and OpenSLES. `libcarplay_proxy` has a separate audio callback record, registered from `jmcs`. This proves a separate **internal callback group**, not a separate process or externally reusable audio route. The audio path is tied to the same `jmcs` receiver/session ownership; exact sequencing versus screen SETUP and audio teardown remains untraced.

Factory audio retention while ClarityLink owns control/SETUP is `UNKNOWN`. A future interface would need to keep session identity, timing, focus, Siri/call behavior and teardown coherent. The current adapter does not claim audio reuse.
