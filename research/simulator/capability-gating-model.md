# Synthetic Type111 capability gating

This gate is a digital-twin control, not a Honda negotiation claim.

## Modes

| Mode | Behavior | Evidence |
|---|---|---|
| STRICT_HONDA | Never extends Setup with Type111. Stock-shaped result remains Type110/audio only, reflecting Honda's confirmed unsupported Type111 branch. | Honda stock behavior + synthetic response values |
| HYPOTHETICAL_TYPE111 | Allows a candidate replay only when every synthetic prerequisite is available and unresolved Honda fields are explicitly listed. | MHI2-derived hypothesis + synthetic test values |

## Required gates

Session active; Type110 established; capability advertisement present; candidate display descriptor available; stream fields available; synthetic security placeholder available; renderer target available; and unknown Honda fields explicitly unresolved. Missing any prerequisite rejects the hypothetical path. Strict mode skips even when every input is true.

Hypothetical capability advertisement uses a synthetic descriptor. Its UUID does not correlate to the synthetic stream ID. Current iPhone/Honda capability generation and descriptor requirements remain unknown.

## Evidence labels

- HONDA_CONFIRMED: stock Type111 is skipped/unsupported in the recovered Setup path.
- MHI2_DERIVED_HYPOTHESIS: candidate cloned response and streamID field profile.
- SYNTHETIC_TEST_VALUE: IDs, ports, descriptor values, session state and frame.
- UNKNOWN: whether a real iPhone requests/accepts these fields and how display/stream identity is bound.

Never interpret HYPOTHETICAL_TYPE111 success as Honda or iPhone support.
