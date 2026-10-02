# Step 43P session metadata

- Evidence class: `CURRENT_IOS_LAB_CONFIRMED` (specific to this PlayPort profile; phone model/iOS build not retained)
- Canonical capture: later of two sessions in the external append-only log
- ClarityLink base: `4940b06497e9ef8fcd46f357fce88462909b23b0`
- PlayPort lab: `f2679a26a593f544ba7822dfbac870544b4af92a`, branch `claritylink-type111-lab`
- macOS: 27.2, build `26B5091g`
- Transport: wireless Bluetooth iAP2 bootstrap, followed by Wi-Fi CarPlay
- PlayPort sourceVersion: `366.0`
- Flags: `--wireless --cluster --type111-diagnostics`
- Main display: Type110, synthetic 1280×720 at 60 FPS
- Cluster display: Type111, synthetic 800×480 at 30 FPS; initial URL `maps:/car/instrumentcluster/map`
- Wi-Fi SSID/password: omitted
- iPhone model and iOS build: unknown; not retained by diagnostics
- Authentication: shared experimental identity, `EXPERIMENTAL_LAB_ONLY`; files outside both repositories, mode 0600
- Source log: two session setups; first proposed `hevc`, later canonical session did not. No profile setting was intentionally varied. The canonical event file contains only the later session (945 allowlisted events).
- Session stop: PlayPort server shutdown emitted `stopped` for both streams. This was not a Type111-only lifecycle test.
- Honda: not used; `adb devices -l` returned no attached targets.

The companion [summary JSON](session-summary.json) and [redacted event trace](oracle-events.redacted.jsonl) contain only the diagnostic allowlist. No raw UUIDs, connection IDs, credentials, access token, key material, authentication bodies, or media payloads are included.
