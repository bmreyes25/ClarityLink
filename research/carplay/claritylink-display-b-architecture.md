# ClarityLink Display B architecture — Step 38

**Status:** Honda media path and mixed SETUP loop are statically recovered; offline Setup/security models exist. Honda's Type-111 response/phone-trigger contract and live interposition safety remain open.

## Separate planes

```text
PRESENTATION
/info -> Honda display descriptor -> future ClarityLink capability augmentation
      -> suggestUI / showUI / stopUI / ViewArea (later)

SETUP / TRANSPORT
original streams[] -> Honda handles 100/101/110 and skips unsupported 111
                    -> stock response remains intact
                    -> ClarityLink prepares separate Type111 state
                    -> append cloned Type111 response before serializer
Type111 socket -> independent CTR -> ScreenReceiverCore -> VideoConfig/H264
```

Display UUID remains presentation/capability identity. `streamConnectionID` is the per-screen crypto input. No UUID-to-ID binding is required by the proven transport path.

## Honda mixed-Setup result

The unsupported branch at `0x2861f6` only logs; it does not write the Setup status or mutate/clear response entries. It continues at `0x286220`. If supported entries and final `AirPlayReceiverSessionPlatformControl` succeed, Setup returns success. This supports passing the original mixed request to Honda, preserving stock response, and appending project output afterward. Supported-stream failures still follow existing Setup rollback.

## Primary path preservation

When Type111 handling is disabled or fails, retain the original Honda response and leave Type100/101/110 entries, ports, key/IV, listeners, center display and audio untouched. Fail softly by returning the stock response after cleaning project-owned partial state. Phone behavior when its requested Type111 descriptor is omitted remains unknown.

## Security and ownership

The Type-110 derivation contract is implemented offline with synthetic input. Type111 reuse of Honda's helper is MHI2 prior-art, not Honda proof. Any parallel Type111 stream needs its own key/IV, CTR position, listener/socket, parser/config state and generation; never modify Honda screen object crypto. Keep all secret values in memory and out of logs/persistent storage.

## Readiness

| Component | Status |
|---|---|
| Honda Type110 media model | READY offline with documented normalization/timebase limits |
| Honda mixed stream Setup analysis | READY static; Type111 skip is non-fatal absent other errors |
| Offline Type111 response augmentation | READY as explicit MHI2-shaped model, not Honda wire proof |
| Offline Type110 screen KDF | READY synthetic-only |
| Honda Type111 KDF compatibility | UNKNOWN |
| First Type111 request trigger | UNKNOWN |
| Live interposer / listener / car test | NOT READY / not performed |
| Decoder, cluster rendering, presentation controls | later milestones |

Step 39 should build/review the host-only interposer and lifecycle around this transaction model. It must not attempt live deployment.

## Step 39 host implementation

The implementation separates `server_info.py`, `setup_interposer.py`, `listener.py`, `transaction.py`, `models.py`, and `lifecycle_coord.py`. All use injected dependencies and synthetic data. The media receiver remains the existing `HondaScreenReceiverCore` from `src/claritylink-transport/`.

A prepared generation owns its synthetic derived key and IV containers, fake listener, optional accepted socket, receiver instance, generation number, and streamConnectionID. The host lifecycle changes the generation to ACTIVE only after successful modeled stock SessionStart. Teardown closes only project resources.

The response publisher is an injected serializer boundary. A false result or exception triggers project rollback and returns the unmodified stock response. Actual Honda serializer timing and CF ownership still require runtime adapter validation.
