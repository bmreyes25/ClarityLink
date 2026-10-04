# 43T1-R3C expanded — `libcarplay_proxy.so` interface audit

**Scope:** `HONDA_CONFIRMED` static evidence from the preserved ARM32 `jmcs` (`cbc7ba88…`) and proxy (`dc8bc5c1…`), with `xcrun llvm-objdump -p -T -R -d`. No Honda process or vehicle was contacted. Addresses below are proxy ELF virtual addresses unless stated otherwise.

`jmcs` directly `DT_NEEDED`-loads `libcarplay_proxy.so`. Its `.rel.plt` has `R_ARM_JUMP_SLOT` entries for `mc_carplay_proxy_{auth,audio,screen}_{register,unregister}` (screen at `0x346acc/0x346ad0`). The proxy imports only libc/ABI functions in its dynamic symbols and needs `libexpat.so`, `libc.so`, `libstdc++.so`, and `libm.so`. It has `DT_FINI_ARRAY` but no `DT_INIT_ARRAY`. This is a linked stock implementation boundary, not a plugin loader. See [dependency graph](jmcs-dependency-graph.md) and [native receiver audit](../native/receiver-multidisplay-audit.md).

| Interface | Kind and owner | Static evidence | Session / Setup / cleanup relevance |
|---|---|---|---|
| `mc_carplay_proxy_screen_register` `0x1b7c`; unregister `0x1ca4` | One-shot whole-record registration; Honda `jmcs` calls via PLT | At `0x1ba2–0x1baa` flag test, second call returns `0x16` (`0x1bce/0x1c10`); first call copies six words at `0x1be0–0x1c04`; unregister zeros six words at `0x1cc6–0x1ce2` | `REJECT_REPLACEMENT`. No append, per-session key, user/refcon field, Setup request, or response object. Global unregister would displace stock Type110 callbacks. |
| `ScreenStreamInitialize` `0x1130`; `Finalize` `0x1198`; `SetProperty` `0x11ec`; `Start` `0x1260`; `Stop` `0x12c4`; `ProcessData` `0x1318` | Proxy trampoline/dispatch into six stored Honda callbacks | Each loads one fixed word at offsets `0/4/8/12/16/20` and `blx` calls it; e.g. Initialize `0x114a–0x114c`, Finalize `0x11a0–0x11b0` | Stream object arguments are forwarded, but no additive observer or exposed session map. These functions are media lifecycle wrappers, not Setup response mediation. |
| `mc_carplay_proxy_audio_register/unregister` `0x199c/0x1ab0` | Audio callback registration; Honda-owned | Proxy `.dynsym`; `jmcs` PLT `0x346ac0/0x346ac4` | Separate audio callback record. No evidence of Type111 or Setup context; replacement risks stock audio. |
| `mc_carplay_proxy_auth_register/unregister` `0x1d94/0x1ea8` | Authentication callback registration; Honda-owned | Proxy `.dynsym`; `jmcs` PLT `0x346a7c/0x346a88` | Auth boundary, not an additive session/response extension. Replacing it risks stock authentication. |
| `AudioStream*`, `AudioSession*`, `proxy_uwh_ipod_cp_*` | Proxy forwarding APIs | Proxy `.dynsym` at `0xb38–0x1910` | No recovered project registration, request/response mutation, or session-scoped cleanup callback. |

The proxy exports no `AirPlayReceiverSessionSetup`, `_requestSendPlistResponse`, `CFPropertyListCreateData`, `ScreenStreamCreate`, or session extension factory. Its name and GLOBAL exports do not prove an interposable caller path. The concrete caller/relocation evidence is limited to the proxy registration boundary. See [dynamic-link audit](43t1-r3c-extension-path-matrix.md).

**Classification:** callback dispatch/proxy, with singleton replacement registration. It is neither an observer list, an additive factory, nor a response wrapper. Type110 preservation under a second registration is not evidenced and the observed second registration rejects it.
