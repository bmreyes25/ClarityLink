# ClarityLink Display B architecture — Step 37 update

**Status:** offline transport/media core established for the Honda Type-110 ScreenStream family. Type-111 SETUP/security contract and live interposition are not implemented.

## Separate planes

```text
PRESENTATION
/info -> Honda display descriptor -> ClarityLink capability augmentation (future)
      -> suggestUI / showUI / stopUI / ViewArea (future)

SETUP / TRANSPORT
incoming streams[] -> future ClarityLink Type111 split/interposer
                    -> Honda handles preserved 100/101/110 entries
                    -> keep Honda response
                    -> ClarityLink Type111 listener + merged response (future)
Type111 socket -> ScreenReceiverCore -> config + timestamped Annex-B buffers
```

Display UUID remains presentation identity. `streamConnectionID` remains the transport/security identity; no direct UUID binding is required by current evidence.

## Media receiver boundary

Honda Type110 evidence now closes the type-1 config-to-type-0 data link: avcC-like config yields converted SPS/PPS and NAL width; next type-0 callback uses that width, builds one media buffer, and prepends pending parameter sets. The offline core is a Type110 compatibility model; MHI2 shows a similar Type111 family, but Honda's Type111 contract has not been accepted or tested.

## Primary path preservation contract for future changes

Any future interposer must preserve, when ClarityLink is disabled or Type111 handling fails:

- Honda main display descriptor and UUID
- Honda Type100, Type101, and Type110 entries and response fields
- Honda primary listener and dataPort
- Honda primary key/IV and screen crypto state
- Honda center display and CarPlay audio
- no CAN writes, block-device writes, or firmware flashing

Observable disabled-mode behavior should remain byte/structure-equivalent to stock wherever the serialized protocol permits exact comparison.

## Mixed request, error and rollback design questions

Honda Setup logs and skips unsupported Type111 entries in its per-entry loop at `0x2861f6` -> `0x286220`; this does not yet prove the complete response or transaction status. Future code should retain the original request, pass unchanged supported entries to stock, and append Type111 output only after listener/key setup succeeds. Step 38 must prove whether the transaction is atomic, whether a failed secondary can be omitted while primary succeeds, how listener cleanup works, and which response object owns the merge window. Do not implement a rollback strategy until those behaviors are traced.

## Readiness

| Component | Status |
|---|---|
| Offline Honda Type110 media model | READY with injected crypto provider; timebase and byte-normalization caveat remain |
| Type111 Setup contract | NOT READY |
| Type111 security/key integration | NOT READY |
| Live interposer | NOT READY |
| Cluster renderer/decoder connection | NOT READY |
| Presentation controls | NOT READY |
