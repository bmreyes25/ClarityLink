# R5A — Honda Type111 static signature checklist

Use only against a lawfully accessible, provenance-recorded receiver artifact. Static signatures should be tied through a call/data-flow path; isolated strings or generic library presence are insufficient. Do not execute the artifact or use a live receiver.

## Strong positive signatures

- [ ] Setup stream-type switch/range includes 111 and reaches a secondary-screen setup branch.
- [ ] Requested type 111 reaches screen setup, not merely generic decoder code.
- [ ] Response stream entry includes `type=111` and a separately allocated/listening `dataPort`.
- [ ] A distinct `streamConnectionID` is consumed and associated with the secondary stream/session.
- [ ] A second screen object is created, registered, and set up with independent identity/lifecycle.
- [ ] `AirPlayReceiverSessionScreen_SetSecurityInfo` or equivalent is called for that screen.
- [ ] `AirPlay_DeriveAESKeySHA512ForScreen` or an identified equivalent derives per-screen security inputs.
- [ ] A second socket/listener/accepted-stream path feeds the secondary stream.
- [ ] Type111-specific or generic typed teardown reaches secondary screen, socket, decoder, worker, and crypto cleanup.
- [ ] Type110 remains stock-owned: no replacement of its response, listener, crypto, callbacks, audio, or teardown path.

## Weak / non-decisive signatures

- [ ] Literal `111` with no validated branch/data flow.
- [ ] Generic H.264 decoder or codec library.
- [ ] Cluster/driver-display app, CarPlay marketing text, or instrument-cluster UI.
- [ ] CarPlay metadata, TBT, `NavGuide`, route data, or iAP2 route-guidance fields.
- [ ] Apple documentation that describes multiple displays without linking Honda receiver behavior.
- [ ] External receiver behavior (including xcertplay/MHI2/DiPlay) without Honda linkage.

## Outcomes

| Outcome | Rule |
|---|---|
| `TYPE111_POSITIVE` | Strongly linked receiver-side request, response, distinct stream/security/session, second screen, and teardown evidence; Type110 stock ownership also assessed. |
| `TYPE111_PROMISING_STATIC_CANDIDATE` | Multiple linked strong indicators, but at least one required lifecycle/security/response edge remains unresolved. |
| `TYPE111_METADATA_ONLY` | Route/TBT/iAP2 or cluster semantic data only; no secondary H.264 stream evidence. |
| `TYPE111_NO_EVIDENCE` | Sufficient relevant receiver artifact reviewed and no Type111 path found within stated scope. |
| `TYPE111_INSUFFICIENT_ARTIFACT` | Artifact absent, incomplete, wrong version, or provenance does not permit a meaningful scoped conclusion. |

Current repository result: **`TYPE111_INSUFFICIENT_ARTIFACT` for descendant binaries**; the reviewed Honda `jmcs` artifact remains negative for supported Type111 and is controlled by R3C. External modern dual-stream and legacy AES prior art are context only. @ECC review requires evidence for each checkbox rather than inferring protocol support from strings.
