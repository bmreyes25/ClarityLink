# R6E real-iOS ladder

No ClarityLink iPhone session occurred in R6E. Highest tier: `BELOW_R6E_T0`. Every tier requires all earlier events in one continuous real authenticated session. Synthetic contract/replay tests earn no tier.

| Tier | Required observation | R6E |
|---|---|---|
| T0 | authorized genuine authority initialized | BLOCKED |
| T1 | real iPhone authenticated CarPlay-capable session | BLOCKED |
| T2 | real control request reached ClarityLink | BLOCKED |
| T3 | request identified as /info | BLOCKED |
| T4 | real /info response sent | BLOCKED |
| T5 | next iPhone protocol request after response | BLOCKED |
| T6 | real SETUP request | BLOCKED |
| T7 | Type110 or Type111 descriptor | BLOCKED |
| T8 | Type111 SETUP confirmed | BLOCKED |

An eventual run should record generation, event order, status, method/path and sanitized dictionary field paths/types/counts. It must stop at disconnect, malformed input, timeout or authority loss. No raw identifier, certificate, pairing secret or challenge material is stored.
