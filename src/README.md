# Source tree guide

`src/` contains offline models, parsers, host-side utilities, and bounded research helpers. Names that refer to Honda code describe modeled or researched boundaries and do not imply deployment.

| Directory | Role |
|---|---|
| `carplay-session-model/` | Screen and project-session state models. |
| `claritylink-honda/` | Fingerprint, addressing, hook-gate, and runtime-safety models. No target attachment is performed by the package. |
| `claritylink-hook/` | Self-location and target descriptor utilities. |
| `claritylink-interposer/` | Host-side interposer, transaction, and listener models. |
| `claritylink-negotiation/` | Offline SETUP, response, lifecycle, and Type111 contract models; native transaction core and shim artifacts. |
| `claritylink-probes/` | Source for bounded preload probe experiments; builds/artifacts are not part of normal CI. |
| `claritylink-renderer/` | Existing frame prototype/API-17 boundary plus R4B pure Python synthetic turn-card model. Real Honda handoff is unproven. |
| `claritylink-sim/` | Synthetic replay and visual-demo helpers. |
| `claritylink-transport/` | Screen parser, media extraction, and crypto/session models. Synthetic paths remain labeled. |

For test ownership and evidence scope, see [`tests/README.md`](../tests/README.md). For execution boundaries and commands, see [testing instructions](../docs/development/testing.md) and the [tools guide](../tools/README.md).
