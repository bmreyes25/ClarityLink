# Test tree guide

The normal test suite is host-only and vehicle-independent. Tests use synthetic values, mocks, preserved static artifacts where available, and localhost sockets; they do not contact Honda or require ADB.

| Directory | Coverage |
|---|---|
| `carplay-session-model/` | Synthetic session and display lifecycle. |
| `honda/` | Static-plan and fail-closed safety-model checks; no live vehicle access. |
| `hook/` | Host self-locator smoke and model tests. |
| `integration/` | Synthetic Type111 and visual twin composition. |
| `interposer/`, `native/` | Host loopback and C transaction-core behavior. |
| `negotiation/`, `prep2/` | Offline response/setup/runtime gates and synthetic failure cases. |
| `offline-decoder/`, `sim/`, `transport/` | Synthetic media/transport behavior. |
| `preload-probe/` | Probe artifact validation. |
| `tools/` | Offline parsers, analyzers, and plan validators. |

`tests/fixtures/` contains generated test material, not raw vehicle capture data. Some environment-dependent native or capture-replay cases may skip when their private or platform-specific prerequisites are absent. CI runs [`./tools/run_tests.sh`](../tools/run_tests.sh), which does not run a vehicle collector. See [testing instructions](../docs/development/testing.md).
