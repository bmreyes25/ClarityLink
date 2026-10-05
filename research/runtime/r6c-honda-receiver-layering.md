# R6C Honda receiver layering

**Classification: `MONOLITHIC_RECEIVER` at the process/ELF boundary, with internal layers.** `jmcs` compiles USB host transport, iAP2, accessory authentication, MediaCore CarPlay, and AirPlay receiver/session/screen functions into one ARM32 executable. Internal objects and callbacks distinguish these layers, but an internal function call is not a supported interprocess API.

`libcarplay_proxy.so` is the one direct CarPlay-related shared-library boundary. Its authentication/audio/screen registration records forward to stock `jmcs` callbacks; they do not expose USB, iAP2, session creation, structured requests, security context, or response ownership. R3C found the screen registration is singleton. Android `CarPlayService` is a separate application-service layer for state and display coordination; it does not carry the native receiver session.

This classification is bounded to the preserved image and static reachability. A runtime service or channel omitted from the image remains possible but unproven.
