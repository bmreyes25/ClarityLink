# Step 43P — current-iOS Type111 oracle session

**Status: OBSERVATION COMPLETE.** Two sessions appeared in the PlayPort append-only diagnostics during the controlled run. The later session is preserved as the canonical redacted trace; the earlier session is recorded as an additional observation. No experimental fields or profile settings were changed by the operator. No Honda device or Honda artifact was used.

## Base and preflight

| Check | Result |
|---|---|
| ClarityLink | `4940b06497e9ef8fcd46f357fce88462909b23b0`, branch `main`, clean before report edits |
| PlayPort lab | `f2679a26a593f544ba7822dfbac870544b4af92a`, branch `claritylink-type111-lab`, clean before report edits; required `a068602ebcec18bf922a0e8bbae30e4a6c4301a2` is an ancestor |
| Auth class | `EXPERIMENTAL_LAB_ONLY`; identity stored outside both repositories, owner-only files (`0600`), not tracked |
| `MfiIdentityTest` | PASS: 2 tests, 0 failures, 0 skipped; includes local identity challenge signing and certificate/key match |
| ClarityLink full offline suite | PASS: 301 passed, 4 expected skips; simulator checks and `git diff --check` passed |
| PlayPort | PASS: focused `MfiIdentityTest`, Gradle `build`, web tests, and web build |
| Honda ADB | No attached Android targets |
| Network / transport | Wireless PlayPort run; Bluetooth iAP2 bootstrap accepted, then Wi-Fi CarPlay session reached both data ports |
| macOS | 27.2, build `26B5091g` |
| iPhone model / iOS build | UNKNOWN; not retained in the allowlisted capture |

The local PlayPort authentication identity is intentionally shared and extractable. Its passing consistency test proves only that the configured key and certificate match; it does not make the identity private, production-ready, Apple-certified, or Honda evidence.

## Canonical profile

The later session advertised PlayPort `sourceVersion` `366.0`, two displays, and the opt-in `--wireless --cluster --type111-diagnostics` profile. Main display 110 was synthetic `1280×720@60`; cluster display 111 was synthetic `800×480@30` with `maps:/car/instrumentcluster/map`. These values are lab profile values, not Honda geometry. The secured Wi-Fi name and password are omitted.

The source append log contained two session setups. The earlier session proposed `hevc`; the later canonical session did not. This difference was observed in the phone's feature proposal; the operator did not change PlayPort's feature set, geometry, `sourceVersion`, URL, or codec preference. The canonical trace includes only the later session.

## Live observations

| Question | Canonical observation |
|---|---|
| `altScreenURLs` | Key present in the INFO request. The sanitized advertised values were empty; no safe `maps:/` URL value was returned in this field. |
| Requested features | `uiContext`, `viewAreas`, `cornerMasks`, `focusTransfer`, `h.264Level5.1`, `mainBuffered`, `altScreen`, `enhancedSiri`, `vehicleStateProtocol`, `sessionManagement`, `videoPlayback`, `logTransfer`, `iAPChannel` |
| Enabled features | `iAPChannel`, `viewAreas`, `altScreen` |
| Displays / view areas | Two displays; viewAreas and initialViewArea present for both descriptors. UUID values were not recorded. |
| Type110 / Type111 | Both requested. Type111 SETUP/listener came before Type110. |
| `streamConnectionID` | Present for both; the redacted comparison reported them distinct. Raw IDs were not persisted. |
| Data ports | Type111 `59841`; Type110 `59842`. |
| Socket connection | Both listeners accepted a socket; both streams became active. |
| VideoConfig | Received for Type110 and Type111; config size 39 bytes each. |
| First frame | Type110: 639 bytes, keyframe. Type111: 7,765 bytes, keyframe. Sustained per-stream frame summaries followed. |
| Codec | UNKNOWN; no codec value was retained in the diagnostic event. Do not infer from PlayPort defaults. |
| Security/parser branch | `MODERN_CHACHA_SCREEN` for both streams, based on the active PlayPort parser branch. This is not Honda security evidence. |
| Controls | Four `suggestUI` events. No `forceKeyFrame`, `showUI`, or `stopUI` event was observed. |
| Teardown / restart | Server shutdown stopped both streams. No Type111-only teardown while 110 remained active and no Type111 restart were observed. Independent lifecycle remains NOT TESTED. |
| Type110 audio | UNKNOWN; this diagnostic capture did not report audio state. |

The full canonical allowlisted event trace and structured summary are in [the 43P capture directory](../research/lab/captures/43p/session-summary.json) and [event file](../research/lab/captures/43p/oracle-events.redacted.jsonl). Session metadata and limitations are in [session-metadata.md](../research/lab/captures/43p/session-metadata.md).

## Evidence and decision

All live protocol findings above are `CURRENT_IOS_LAB_CONFIRMED`, scoped to this PlayPort build/profile and an iPhone whose exact model/iOS build was not retained. The display geometry is `SYNTHETIC_TEST_VALUE`. The authentication identity is `EXPERIMENTAL_LAB_ONLY`. None of this changes Honda Type111 fields, renderer support, or crypto from `HONDA_UNKNOWN`.

The live run confirms that this phone requested Type111, that PlayPort negotiated a distinct connection ID and data port, and that the Type111 socket delivered configured video while Type110 remained active. This independently supports the two-stream topology needed for the offline 43Q model. The observed modern ChaCha parser branch differs from Honda's confirmed legacy Type110 AES-CTR path, so it is not used to derive Honda crypto behavior. **43Q is authorized as an offline model only**, using Honda-confirmed Type110 primitives and synthetic second-stream inputs; it must preserve Honda Type111 crypto as unknown and must not touch Honda runtime.

The capture contains no raw connection IDs, UUID values, authentication material, session/media keys, Wi-Fi credentials, browser token, or media payload. `SESSION_SETUP` event fields are allowlisted names/features only. The canonical JSON was independently checked against the event and metadata allowlists and scanned for secret-shaped material before being added.

## ECC review

No dedicated ECC reviewer was available in this workflow. The relevant ECC security-review and Kotlin/Python testing checklists were applied manually: secret handling and file permissions were checked; capture fields were checked against the allowlist; diagnostics and identity tests passed; and Honda/runtime boundaries were reviewed. This is a manual review record, not an independent third-party audit.

## Verification and repository state

- ClarityLink focused redaction/lifecycle/provenance tests: PASS (104 passed); `./tools/run_tests.sh`: PASS (301 passed, 4 skipped).
- PlayPort `:server:test --tests '*MfiIdentityTest*' --tests '*OracleDiagnosticsTest*'`: PASS; the identity test ran 2 tests with none skipped.
- PlayPort `./gradlew build`: PASS.
- PlayPort `web/npm test` and `web/npm run build`: PASS.
- ClarityLink `git diff --check`, capture allowlist/secret scan, JSON validation, and changed-file Markdown relative-link checks: PASS.
- Honda used: NO. 43Q runtime execution: NOT AUTHORIZED / NOT DONE.
