# Honda screen session binding

Type-110 Setup reads `streamConnectionID`, rejects zero, derives key/IV, installs AES-CTR state on the per-session screen object, opens its Type-110 TCP listener on an ephemeral port, and appends `{type:110,dataPort}`. The listener and screen stream state are Honda-owned; the request ID is proven as a KDF input but not proven stored in a named long-lived object field.

The KDF uses unsigned decimal ASCII `streamConnectionID` in separate `AirPlayStreamKey` and `AirPlayStreamIV` salts. See `screen-crypto.md` and `honda-screen-crypto.md`.

Type 111 is skipped before the Type-110 screen branch. ClarityLink must own separate Type-111 key/IV, CTR, listener, accepted socket, parser/config and generation state; do not overwrite Honda's Type-110 screen object's crypto or listener. MHI2 demonstrates this as prior-art architecture; Honda Type-111 compatibility remains unknown.
