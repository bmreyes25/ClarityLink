# Type111 offline pipeline status

The offline path is already represented by synthetic, host-testable pieces. This status separates the implementation model from Honda wire facts. No Type111 code was enabled in Honda and no live stream was tested.

| Layer | Existing model | Evidence boundary / open item |
|---|---|---|
| SETUP response | `src/claritylink-negotiation/setup_augmentor.py`, `setup_transaction.py` | Preserves stock response and appends an MHI2-derived Type111 descriptor/dataPort/streamID shape. Honda's Type111 response schema and correlation fields remain unknown. |
| Lifecycle/session | `src/claritylink-negotiation/lifecycle.py`, `screen_kdf.py` | Generation/teardown is modeled. Honda Type110 KDF is modeled with synthetic inputs; whether Type111 reuses it or needs a new streamConnectionID/key derivation remains unknown. No key material is saved. |
| ScreenStream envelope | `src/claritylink-transport/screen_parser.py` | 128-byte header and bounded length framing modeled from Honda static analysis; body opcodes/security field selection still need exact stream-111 evidence. |
| CTR state | `src/claritylink-transport/crypto_model.py` | Stateful body transform modeled with injected test block function; real AES and session-key provisioning remain outside the model. |
| VideoConfig | `src/claritylink-transport/video_config.py` | Bounded avcC fields Honda's helper consumes are modeled; stream-111 delivery/order and negotiation remain unknown. |
| H.264 extraction | `src/claritylink-transport/h264_extractor.py` | Honda's 1/2/4-byte length-prefixed NAL conversion to Annex-B is modeled; actual Type111 payload parity is unverified. |
| Renderer handoff | `src/claritylink-renderer/model.py`, `android-api17/` | Host lifecycle/mock and Java API17 skeleton exist. Actual Honda ExternalDisplay ownership, decoder Surface path, geometry/crop, and zero-copy behavior are not proven. |

The host-only end-to-end fixture joins synthetic display advertisement, stock-first response augmentation, listener stand-in, session lifecycle, ScreenStream config/media parsing, Annex-B conversion, and teardown. It is not a Honda protocol acceptance test; fixture Type111 fields remain prior-art-derived/hypothetical.

Focused verification after the probe work: Setup negotiation 18 tests passed; transport parser/crypto/config/H.264 receiver 29 passed; display/session model 12 passed; renderer 8 passed; host-only Display B integration smoke passed. Pytest is unavailable, so the integration function was invoked directly and unittest discovery was used for unittest suites.

Next offline Type111 task: review descriptor/stream correlation and security fields against the exact archived Honda parser and prior-art sources, then update only fields whose provenance is explicit. Do not guess wire fields or enable Type111.
