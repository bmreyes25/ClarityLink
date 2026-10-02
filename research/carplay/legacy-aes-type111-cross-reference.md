# Legacy AES Type111 cross-reference — external prior art only

## Pins and handling boundary

This note compares two pinned external sources. Neither establishes Honda behavior. No source code is copied into ClarityLink.

| Source | Exact revision | Inspected material | Evidence class |
|---|---|---|---|
| `harman-f/mhi2_altscreen_carplay` | `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` (`runtime: defer FPS bridge restart until source renegotiates`) | `docs/research/STREAM111_PROTOCOL.md`, `docs/research/MU1440_GEN2_HOOK_MAP.md` | `EXTERNAL_PRIOR_ART` for MU1440 / AirPlay 210.81-era target |
| `45clouds/WirelessCarPlay` | `51145ef55f8dd9f1cbadd58353cacb5e0ca215e9` (`Merge pull request #16 from uzhhhhh/biuld`) | `AirPlayReceiverSession.c`, `AirPlayReceiverSessionScreen.c`, `AirPlayCommon.h` | `EXTERNAL_PRIOR_ART`; repository contains Apple-derived/MFi-licensed source, research-only; no reuse or redistribution |

## What the sources support

The pinned MHI2 protocol document describes keeping the stock main screen on its native path while handling Type111 in a project-owned secondary path. For the old AirPlay 210.81-era receiver, it uses the authenticated session's existing AES material together with the requested screen `streamConnectionID`, calls the stock `AirPlay_DeriveAESKeySHA512ForScreen`, and gives the Type111 screen its own AES key/IV. It records the stock lifecycle as `AirPlayReceiverSessionScreen_SetSecurityInfo → AES_CTR_Init`, frame processing → `AES_CTR_Update`, and stop → `AES_CTR_Final`. The hook map describes a stock-first Setup extension and warns that its ABI, symbol, and hook compatibility facts are specific to its audited MU1440 binary.

At the pinned WirelessCarPlay revision, `AirPlayReceiverSessionScreen_Setup` reads the screen descriptor's `streamConnectionID`; on the legacy/non-PairVerify path it passes the receiver session's `aesSessionKey` and that ID to `AirPlay_DeriveAESKeySHA512ForScreen`, then installs the resulting key/IV through `AirPlayReceiverSessionScreen_SetSecurityInfo`. This independently supports the important dataflow claim that the screen KDF is keyed by the screen's own connection ID. The same source has a PairVerify path using DataStream key derivation and ChaCha, so the AES branch is generation/session-mode-specific.

These sources strengthen the **legacy receiver design hypothesis**:

```text
existing authenticated session AES material
        + per-screen streamConnectionID
        ↓
legacy screen key/IV derivation
        ↓
independent screen AES-CTR state
```

For Honda, the left branch (Type110) is separately `HONDA_CONFIRMED`: its recovered screen KDF consumes receiver-session master material and Type110's `streamConnectionID`, then uses AES-CTR. The right branch (Honda Type111) remains `HONDA_UNKNOWN`. Cross-platform evidence makes `LEGACY_PER_SCREEN_KDF_STRONGLY_SUPPORTED` a useful hypothesis, with **Honda ABI/state validation still required**. It does not prove Honda's Type111 setup is accepted, that an arbitrary call can create a second context, or that all parser/socket/lifecycle state is independent.

## 43Q-A offline isolation result

Step 43Q-A implements `LegacyDualScreenTwin` with explicit `TYPE110` and `TYPE111_SYNTHETIC` roles. It accepts only synthetic session material in its offline tests and independently instantiates each screen's derived key/IV, CTR, receiver, and parser. Deterministic tests prove interleaved output/state matches separate control runs; advancing, resetting, failing, destroying, or recreating B leaves A's CTR/parser state intact. Duplicate IDs are rejected with a structured fail-closed error. Synthetic B destruction/recreation is `LAB_SYNTHETIC_CONFIRMED` only. Generation numbering/restart integration is deliberately deferred to 43Q-B. See the [43Q-A report](../../step-reports/43q-a-legacy-dual-screen-crypto-twin.md). These results describe ClarityLink's model, not Honda runtime behavior.

## 43O and 43P implications

Step 43O prepared a controlled, opt-in PlayPort oracle and redacted diagnostics. Step 43P then observed the phone request Type111 before Type110, use a distinct `streamConnectionID`, connect to a separate dataPort, and deliver Type111 video while Type110 remained active. The selected PlayPort parser classified both streams as `MODERN_CHACHA_SCREEN`. This confirms two-stream topology for that lab profile; it does not prove Honda compatibility or Honda Type111 crypto. See the [43P report](../../step-reports/43p-current-ios-type111-oracle.md) and [sanitized trace](../lab/captures/43p/oracle-events.redacted.jsonl). Honda Type111 crypto/lifecycle remain `HONDA_UNKNOWN`.

Step 43Q-A is complete as an **offline-only** state-isolation twin. 43Q-B may separately add the synthetic generation/restart lifecycle. The current-iOS modern ChaCha observation is not used as legacy AES derivation evidence. Neither milestone establishes Honda Type111 crypto; Honda Type111 remains `HONDA_UNKNOWN`. No Honda runtime action was performed for 43Q-A.

## Pinned source links

- [MHI2 Type111 protocol](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/STREAM111_PROTOCOL.md)
- [MHI2 hook map](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md)
- [WirelessCarPlay legacy receiver session source](https://github.com/45clouds/WirelessCarPlay/blob/51145ef55f8dd9f1cbadd58353cacb5e0ca215e9/source/Sources/AirPlayReceiverSession.c)
- [WirelessCarPlay ScreenStream source](https://github.com/45clouds/WirelessCarPlay/blob/51145ef55f8dd9f1cbadd58353cacb5e0ca215e9/source/Sources/AirPlayReceiverSessionScreen.c)
