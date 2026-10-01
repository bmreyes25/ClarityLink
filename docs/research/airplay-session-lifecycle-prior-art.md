# AirPlay receiver session lifecycle prior art

**Classification: `EXTERNAL_PRIOR_ART`.** This note records source-lineage comparison only. None of these repositories establishes that Honda uses the same ABI or behavior; Honda evidence is in [its separate lifecycle audit](../../research/carplay/honda-session-delegate-lifecycle.md).

| Source | Pinned revision | Relevant material | Evidence classification |
|---|---|---|---|
| [WirelessCarPlay](https://github.com/45clouds/WirelessCarPlay/tree/51145ef55f8dd9f1cbadd58353cacb5e0ca215e9) | `51145ef55f8dd9f1cbadd58353cacb5e0ca215e9` | `AirPlayReceiverSession.h/.c`, receiver server, application stub | `EXTERNAL_PRIOR_ART` |
| [R11B lineage](https://github.com/cvetaevvitaliy/carplay/tree/76e97ff9a1070e8b509339e3e7deef9cc6b92bff) | `76e97ff9a1070e8b509339e3e7deef9cc6b92bff` | Session header/implementation and server | `EXTERNAL_PRIOR_ART`; delegate layout differs by generation |
| [Hyundai MeeGo 2018 source](https://github.com/suburbazine/hyundai-meego/tree/270425b6f174ff95b90296ae03b0d2a3781a2dc8) | `270425b6f174ff95b90296ae03b0d2a3781a2dc8` | `CarPlayAppFrameworkServerCallbacks.c` | `EXTERNAL_PRIOR_ART`; era-matched automotive example |
| [MHI2 AltScreen](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md) | `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` | teardown/control hook map and implementation | `EXTERNAL_PRIOR_ART` |

## Pattern in the pinned source lineages

The WirelessCarPlay session header defines a session delegate with a context and lifecycle/event callbacks, including `finalize_f`, and exposes `AirPlayReceiverSessionSetDelegate`. Its implementation copies the complete structure into the session. Its CF runtime finalizer invokes the delegate finalizer before platform and session resources are finalized. The application stub installs this delegate from a session-created callback. These are implementation details of that source revision, not a promise about other binaries.

The R11B lineage contains the same broad delegate/finalizer mechanism, but its delegate layout is not assumed to match either WirelessCarPlay or Honda.

The Hyundai 2018 application callback receives a newly created session, initializes a delegate, sets its context and finalizer plus other callbacks, installs it, and then forwards the session-created notification. This shows an automotive application using the mechanism as an application-level lifecycle callback; it remains external evidence.

In the external session implementation, `AirPlayReceiverSessionTearDown` separately sends a `tearDownStreams` platform-control command with teardown parameters before performing stream teardown. The MHI2 project likewise documents separate roles for stream teardown and session teardown. These examples support a two-level conceptual model: request-aware stream lifecycle and final session-object lifetime.

## Implications for ClarityLink

The comparison motivates auditing Honda for (1) a request-aware stream teardown path and (2) a session-object finalizer callback. It also warns that a whole-structure SetDelegate operation can replace existing callbacks. Any future design must preserve Honda's current callback table and ordering; it must not install a project-only delegate blindly.

Honda's `jmcs` independently proves a session CF runtime finalizer, a 44-byte copied session delegate, an installed `_AirPlayHandleSessionFinalized` callback, and a `tearDownStreams` platform-control call. That is Honda-specific evidence, not proof that Honda's complete ABI is identical to any source listed above. No Type111 support or project-child integration is established by this prior art.
