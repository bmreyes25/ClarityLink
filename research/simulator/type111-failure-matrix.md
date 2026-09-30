# Step 42D Type111 failure matrix

All cases are injected into the host-only twin. Expected center/audio behavior is a synthetic isolation invariant, not a claim about Honda's absent Type111 code.

| Stage/case | Model outcome | Type110/audio expectation | Exercised |
|---|---|---|---|
| Missing descriptor / unknown display correlation / missing response field | Reject candidate, preserve stock response | Unchanged | yes |
| Honda unsupported/skips Type111 | Log skipped; no candidate state | Type110 stays active | yes |
| Duplicate request | Reject duplicate; retain current generation | Unchanged | yes |
| Request before Type110 session | Reject precondition | No stock state mutation | precondition test |
| Malformed request / missing or invalid ID | Candidate failure, clear only candidate | Unchanged | missing ID; malformed + invalid modeled |
| Request after Type110 setup | Candidate can prepare only in synthetic profile | Unchanged | yes |
| dataPort allocation / invalid port / bind / listen | Roll back candidate listener/state | Unchanged | allocation, bind, listen |
| Accept timeout / teardown while accepting | Close candidate listener | Unchanged | yes |
| Disconnect before header / mid-header / mid-body | Reset candidate parser and close generation | Unchanged | yes |
| Reconnect after disconnect | Allocate fresh generation | Unchanged | yes |
| Missing ID / unavailable derivation / bad IV / missing CTR | Reject candidate before announcement | Unchanged | yes |
| Opcode 1 before security readiness / decrypt failure | Fail candidate generation | Type110 CTR untouched | yes |
| Opcode 0 before VideoConfig | Reject candidate video | Unchanged | yes |
| Malformed 128-byte header / oversized body / unknown opcode | Close candidate parser | Unchanged | yes |
| Missing/malformed VideoConfig / unsupported NAL width / truncated SPS/PPS | Clear candidate codec/transport state | Unchanged | yes |
| Truncated AVCC / H.264 extractor failure | Clear candidate generation | Unchanged | yes |
| Renderer unavailable / invalid dimensions / timeout | Clear candidate renderer and Type111 only | Type110/audio unchanged | yes |
| ExternalDisplay host unavailable / crop unknown / dropped frame | Drop/fail candidate render, no center mutation | Unchanged | yes |
| Type111 disconnect while Type110 active | Clear only Type111 | Type110/audio remain active | yes |
| Type110 disconnect while Type111 active | Tear down Type111 child and Type110 stream | Session audio policy remains separate in this model | yes |
| Full CarPlay disconnect / subsequent reconnect | Clear both stream states and session audio; new session starts clean | Full-session clear | yes |

The model does not synthesize real payloads or cryptographic keys. Parser/config cases inject semantic failures at stage boundaries; detailed malformed-byte coverage remains in the existing transport parser tests.
