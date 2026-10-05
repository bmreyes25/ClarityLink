# R6H1 Gate 1 real readiness

| Item | Status | Evidence / limitation |
|---|---|---|
| R6H merge | `MERGED` | PR #13 merged at `6f9234dc08800fc6a3cd05e2971913ebb1cc488c` |
| R6H1 software base | `CLEAN` | Branch starts at exact R6H merge SHA |
| CPC200-CCPA | `HARDWARE_REQUIRED` | Safe USB/system inventory shows no matching model; absent |
| CPC200 compatibility | `NOT_TESTED` | Provisioner cannot probe absent hardware |
| Ownership/provenance | `NOT_TESTED` | No unit presented |
| LIVI Link toolchain | `PINNED` | LIVI v9.2.0 and macOS ARM provisioner checksum recorded; no binary downloaded/run |
| Provisioning preflight | `BLOCKED` | No model/revision match, backup, or target to inspect; no write performed |
| Stock firmware backup | `NOT_PERFORMED` | Hardware absent; keep future backup outside Git |
| LIVI Link reachable / genuine authority | `NOT_TESTED` | Hardware absent; no auth request |
| LIVI upstream real-iPhone baseline | `NOT_REACHED` | No hardware or phone session |
| R6H delegate and bridge | `HOST_CONFIRMED` | R6H pinned patch + bounded private AF_UNIX provider; tests are synthetic |
| Authenticated handoff | `HOST_CONFIRMED_ONLY` | Lifecycle/provider conformance only; no genuine session |
| Real iPhone | `NOT_REACHED` | No phone connected for this attempt |
| Real `/info` received/sent/accepted | `NOT_REACHED` | No phone control session |
| Real SETUP | `NOT_REACHED` | Gate 1 hardware absent; Gate 2 remains NOT_STARTED |
| Real tier | `BELOW_G1_T0` | No genuine authority proof |

Gate 1 canonical state remains `SOFTWARE_READY_HARDWARE_REQUIRED`; this milestone's execution result is `GATE1_BLOCKED_WAITING_FOR_CPC200`. Gate 2 remains `NOT_STARTED`.

## Required next event

Obtain the exact user-owned CPC200-CCPA target described in [the R6F acquisition specification](r6f-authority-acquisition-specification.md). Confirm authorized genuine-product provenance and the physical model/revision. Then re-read current LIVI Link compatibility/provisioner documentation, perform read-only device/provisioner identification, and complete the provisioning preflight/backup decision before any write. If those gates pass, validate genuine authority and upstream LIVI on a normal user-owned iPhone. Only then enable the R6H delegate and attempt one continuous ClarityLink session to real `/info`.
