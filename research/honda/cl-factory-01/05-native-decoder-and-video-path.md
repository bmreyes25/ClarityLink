# CL-FACTORY-01 / M2 (G-01/G-05) — Native CarPlay receiver & video path (sanitized)

Status: COMPLETE for the proxy binding; receiver decode path established. Evidence OBSERVED_STATIC (nm symbols +
Ghidra decompile of the preserved native binaries). Offline only. No keys/secrets extracted. `safeForHonda() == false`.
Exact symbol names and decompiled bodies are retained in private evidence.

## Type110 native video path (reconstructed)
```mermaid
flowchart LR
  iPhone[iPhone CarPlay] -->|USB/iAP2| Recv[native AirPlay-family receiver\n(jmcs)]
  Recv -->|AES-encrypted screen stream| Cfg[screen-config read]
  Cfg -->|android_mediacodec_ctx| MC[Android MediaCodec decoder]
  MC -->|decoded frames| VOut[platform video-out driver]
  Recv <-->|callback bind (register)| Proxy[libcarplay_proxy]
  Proxy -->|single screen callback set| VOut
```

## Findings
- **Receiver:** the factory CarPlay receiver daemon is an **AirPlay-family receiver stack** (session/screen/thread
  objects, frame processing, event handling). The CarPlay screen stream is **AES-encrypted**; the crypto exists but
  **no key or secret was extracted or derived** in this research.
- **Decoder ownership:** the receiver reads the screen configuration into an **Android MediaCodec** context —
  i.e. **decoding is performed by the platform MediaCodec**, not inside the proxy. Decoded frames flow to the
  platform video-out driver.
- **Proxy registration is singleton — code-confirmed.** `libcarplay_proxy` exposes symmetric register/unregister
  for three families (screen, audio, auth). Each is backed by a **single global callback set guarded by a single
  global flag**. The screen-register function was decompiled: if the flag is already set it **returns an
  "already-registered" error**; otherwise it sets the flag and installs the one callback set. Unregister clears it.
  This makes the **single-screen-sink constraint architectural** across the proxy binding, not a property of one
  callback interface — confirming and extending the CL-SYS-01A singleton observation.

## Secondary-stream (Type111) assessment at the native layer
- The **Honda proxy binding admits exactly one screen stream** (singleton registration). There is **no second
  screen-registration path** exposed to the platform.
- The underlying AirPlay-family stack contains general display-information concepts, but a protocol-level concept is
  **not** a Honda-exposed second-stream handoff. Therefore: **no supported secondary-stream handoff exists at the
  native binding** — this is *not* a proof that the Apple protocol is incapable, only that the factory does not
  expose it.
- Consequently, a genuine second CarPlay stream would require a **separately authorized receiver** (hardware +
  legitimate authentication), consistent with report 09 (Option B/C gate). No authentication bypass, key extraction,
  or identity spoofing is performed or proposed.

## Failure / teardown
Stream stop/finalize plus unregister clear the global callback set; the receiver session screen object is deleted on
teardown. Reconnect re-registers the single screen sink. Detailed sequencing is in private evidence.

## Limits
Static code presence; not runtime-verified. Decoder/driver identity is from symbols and the decompiled register
path; downstream composition beyond the Android video-out driver is out of scope here (see reports 07/08).
