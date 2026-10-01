# Step 43O — isolated PlayPort Type111 lab

**Result: PLAYPORT TYPE111 LAB READY_OFFLINE. No iPhone, Honda, pairing, or MFi material was used.**

## Bases and preservation

- ClarityLink base before Step 43O: `80e4c53191ee8d8c7a5df0c01be9eeeb015c8839`; it contains remote CI fix `6144222d59e1b2678725afd8ed9735ab01eee710` in ancestry.
- The intentional AES cross-reference and oracle-plan research was preserved and committed separately as `80e4c53 ClarityLink: document legacy AES Type111 evidence`.
- PlayPort base: `9a0882dd0ffe48e467b59d58b12d81391df55ade`; checkout: `../playport-type111-lab`, branch `claritylink-type111-lab`; local lab commit `57df00125f2aedde5c2ab1a3d6e3295e242cd6f3` (not pushed upstream).
- xcertplay reference pin: `17c92439413638dfd1d7f91d7e1c2e7358398762`; MHI2 AES-era material remains `EXTERNAL_PRIOR_ART`. Neither was copied into ClarityLink.

## Findings and changes

The pinned PlayPort profile already supports optional `AirPlayConfig.cluster`, display types 110/111, independent `(session,type)` media ownership, stream type in its wire bridge, and browser parsing of that type. Its default cluster is null and its UI had one canvas. The lab adds an opt-in `--cluster` profile (synthetic default 800×480@30, optional physical dimensions, URL, FPS and dimensions), two independent canvases/decoders, per-stream keyframe readiness/recovery, dimensions and statistics, and Type111-only teardown/restart behavior. The Type111 socket EOF no longer closes the parent CarPlay session; a protocol test verifies the main screen/session survive.

`--type111-diagnostics` enables structured JSON events with centralized field allowlisting. The implementation observes `/info` display metadata, SETUP feature names where available, stream key names and order, connection-ID presence/distinctness, response type/dataPort, socket open, video config/frame metadata, control verbs/UUID presence, and teardown. IDs are compared in memory but not emitted. Existing raw request/stream/teardown debug dumps and raw connection-ID log output were removed.

Security classification is limited to the local PlayPort parser branch. Its current pinned screen implementation uses 128-byte framing and a modern ChaCha20-Poly1305 path. `CLEAR_OR_UNKNOWN` is intentionally ambiguous. This cannot establish Honda Type111 security or the current iPhone's selected mode. Honda Type110 legacy behavior remains Honda-confirmed; Honda Type111 remains `HONDA_UNKNOWN` with legacy per-screen KDF only strongly supported by external prior art.

## Verification

- Baseline before changes: PlayPort `./gradlew build` passed after configuring an isolated temporary JDK; `web/npm test` and `web/npm run build` passed.
- After changes: `JAVA_HOME=/tmp/cl-jdk25/Contents/Home PATH=/tmp/cl-jdk25/Contents/Home/bin:$PATH ./gradlew build` passed: 105 tests total, 104 passed and 1 skipped (`MfiIdentityTest.localIdentitySignsAChallengeWithTheCertificateKey`, local credential fixture unavailable).
- After changes: `web/npm test` passed; `web/npm run build` passed.
- ClarityLink precheck: `tools.elf_va_map` import smoke passed; focused map tests 8 passed; full suite 301 passed, 4 skipped, 3 self-locator smoke checks passed, simulator JavaScript checks passed. Capture-backed skips remain due unavailable fixtures.
- ECC: no dedicated ECC reviewer was invoked; manual engineering/evidence review was applied. Diagnostics allowlist and Type110/Type111 separation were checked in code/tests.

The first pushed Offline CI run exposed that the earlier `6144222` fix had committed `tools/__init__.py` but the broad `/tools/*` ignore rule still kept `tools/elf_va_map.py` out of GitHub. The local source matched its committed tests; I added a narrow `.gitignore` exception and am committing the missing module so CI can run the same ELF-map tests present locally. The follow-up CI result is recorded after it completes.

No live phone observation was performed. Current-iOS negotiation, phone connection to the second dataPort, actual Type111 media-security variant, and physical cluster rendering remain unobserved. Step 43P is the next separate phone-observation task; Step 43Q is conditional after reviewing its trace.
