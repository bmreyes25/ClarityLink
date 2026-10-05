# R6B external receiver dependency review

Source and license checked against public upstream repositories on 2026-10-04. No external code or credential was copied into R6B.

| Project | License/platform/maintenance | Auth and session ownership | Security/restriction | Adapter verdict |
|---|---|---|---|---|
| [PlayPort](https://github.com/youcci/playport) | GPL-3.0, Mac/JVM, active | owns Bluetooth iAP2, MFi provider, AirPlay session and screen; no exported control handoff | documented default recovered shared identity is forbidden here; separately licensed remote service could be used | interface study only; no key use or code copy |
| [xcertplay](https://github.com/shilapi/xcertplay) | GPL-3.0, Android, active | CH341/I2C chip and remote MFi options; receiver owns session | real hardware/service required; Android-first | possible design reference, not Mac drop-in |
| [OCBM](https://github.com/lvalen91/ocbm) | Unlicense, adapter + Mac host, active | genuine CPC200 coprocessor and iAP2/pairing on adapter, app-driven SETUP on host | requires user-owned adapter and project-specific hardware/possibly licensed SDK context | strongest hardware-backed adapter candidate if available; review exact host API before use |
| [LIVI](https://github.com/seangritthy/LIVI) | GPL-3.0, Linux/macOS, active | genuine MFi coprocessor, complete receiver | physical chip required; no ClarityLink handoff API shown | research candidate |
| [carplayd](https://github.com/lvalen91/carplayd) | Unlicense, CCPA/Pi, active | CCPA MFi hardware oracle and receiver | hardware and non-Mac topology | future adapter reference |

GPL code must not be pasted into the project without a deliberate license decision. Public protocol behavior is evidence, not a grant to use third-party credentials. The [Apple MFi FAQ](https://mfi.apple.com/en/faqs) lists CarPlay authentication coprocessors as MFi components; no software bypass is proposed.
