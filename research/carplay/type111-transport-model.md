# Type-111 transport model — Step 38

Honda Type-110 gives a proven reusable primitive set: nonzero uint64 `streamConnectionID`; 16-byte session master material; `AirPlay_DeriveAESKeySHA512ForScreen`; independent AES-CTR initialization; an ephemeral TCP listener; a `{type:110,dataPort}` response; and the ScreenStream media path from Steps 36–37. Honda does not dispatch Type 111 into any of these handlers.

The Type-111 target remains a project-owned session over the same authenticated CarPlay session. MHI2 prior-art reads its Type-111 ID, derives a separate screen key/IV from stock session security material using the stock screen KDF, opens an independent listener, and returns a cloned descriptor with `dataPort` and `streamID=111`. Its Setup path calls stock with the original request; its explicit `clone_without_111` helper is used while forwarding teardown to stock.

Honda Setup statically logs/skips 111 and continues. This makes stock-original delegation the best-supported offline strategy. After stock success, copy the response and append a prior-art-shaped Type-111 response while preserving all request/stock unknown fields. Honda response shape and Honda Type-111 KDF compatibility remain unknown.

Offline negotiation/crypto models now exist under `src/claritylink-negotiation/`. They use synthetic secrets and injected stock/listener callbacks; they create no socket, alter no Honda process, and do not prove a live Type-111 receiver.
