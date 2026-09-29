# Honda AltScreen gating: Step 28 findings

## Evidence boundary

Apple WWDC19 documents simultaneous CarPlay video streams for a main display and instrument cluster and vehicle-selected cluster content. It does not publish the private descriptor schema or a complete iPhone gate sequence. Pinned xcertplay and Harman MHI2 prior-art evidence defines a main/alternate distinction (110/111), multiple display identities/capability concepts, and Type-111 receiver handling; it is implementation evidence for those projects, not Honda behavior. Honda's recovered SETUP response is phone-facing and has a stock Type-110 stream. Honda's `CopyDisplaysInfo` builder returns one local dictionary, but its caller and phone-facing route are not established.

## Minimum supported sequence

| Stage | Status |
|---|---|
| Receiver exposes an additional display identity/capability | Prior-art supported; Honda unknown |
| iPhone recognizes/selects alternate display and proposes secondary UI | Apple documents multi-stream cluster use at high level; exact gate/schema unknown |
| Phone issues secondary setup/request with display correlation | Prior-art supported; Honda unknown |
| Receiver accepts Type 111 and provisions a distinct listener/port | Harman prior-art supported; Honda unknown |
| SETUP response includes Type 111 and its dataPort | Honda supports stock Type 110 only; Type 111 unknown |

`features` exists in Honda's local descriptor dictionary; no AltScreen-like bit/token is identified. No supported claim that type 111 alone is sufficient. Since display-to-stream correlation is unresolved, **TYPE111_WITHOUT_DISPLAY_ADVERTISEMENT: LIKELY INSUFFICIENT** as a conservative protocol inference, not an Apple-published rule. A full alternate-display implementation may require capability advertisement plus request parser/dispatcher changes in addition to response augmentation.

## Two-stage design gate

Stage A would require first proving the display-info dictionary reaches a phone-facing parent/serializer, then locating a mutable parent collection/schema. Neither is established. Stage B's response mutation point is structurally known after stock Setup and before serialization; Type-111 request acceptance, port/listener lifecycle, stream/display binding, and live-hook safety are not.

```text
CAPABILITY HOOK REQUIRED: UNKNOWN (likely required by prior-art architecture; Honda gate unknown)
SETUP HOOK REQUIRED: YES for a ClarityLink-owned secondary port if Honda stock code does not provide one; Type-111 acceptance unknown
READY FOR STRUCTURED DISPLAY-B NEGOTIATION IMPLEMENTATION: NO
READY FOR LIVE NEGOTIATION TEST: NO
```

Earliest unambiguous future success signal, after an authorized controlled test is separately planned: a second SETUP request carrying a contextualized alternate type/display identity, or a second listener connection demonstrably correlated to the advertised secondary UUID. A raw TCP connect alone is weaker unless the endpoint and purpose are identified.
