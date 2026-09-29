# Type-111 request descriptor model

## Honda evidence

Honda's generic Setup reads `streams[]` dictionaries and the integer `type`. For Type 110, its screen branch additionally reads a nonzero `streamConnectionID` with `CFDictionaryGetInt64` as a 64-bit unsigned value and uses it for screen key/IV derivation. Honda has no Type-111 handler, so it does not establish required Type-111 fields or semantics.

| Field | Honda access | Type-111 confidence |
|---|---|---|
| `type` | generic Setup dispatch | Type 111 recognized only as unsupported value |
| `streamConnectionID` | read by Type-110 path; not read by Type-111 path | required for MHI2 prior-art security, Honda Type-111 unknown |
| Other request keys | no Type-111 field access | opaque/unknown |

## Pinned MHI2 source

At MHI2 commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, `src/native/altscreen111-gen2/libaltscreen111_gen2.c` scans `streams[]`, selects the entry with `type == 111`, reads `streamConnectionID`, and clones the entire descriptor for its response. Other incoming descriptor keys are preserved but are not required by the shown selector/KDF/listener setup. The Setup delegate passes the **original request** to stock first; `clone_without_111` is used in the teardown path when forwarding remaining entries, not as the Setup strategy.

MHI2 evidence says `type` and `streamConnectionID` are parsed; all other peer fields remain opaque and are preserved. It does not make them Honda requirements.

## Preservation rule

ClarityLink should parse only `type` and a validated nonzero uint64 `streamConnectionID`; retain every other peer field exactly in the original descriptor and response clone. Never rebuild a Type-111 descriptor from a guessed schema.
