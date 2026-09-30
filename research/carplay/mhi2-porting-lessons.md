# MHI2 AltScreen porting lessons (architecture only)

Public project: `harman-f/mhi2_altscreen_carplay`; current GitHub page describes an active project and a vehicle-proven Škoda MU1440/AID10 reference, not Honda compatibility. Repository/commit metadata must be pinned at the time of a reproducible source audit; no Audi/VW offsets transfer.

| MHI2 property | Honda equivalent/evidence | Portable lesson / proof still needed |
|---|---|---|
| Keep stock receiver; call stock Setup first | Honda Setup call and response ABI recovered, Type110 path known | Stock-first augmentation is sound design; Honda mixed-stream rollback/schema still needs proof. |
| Preserve primary response | Honda response includes Type110/dataPort and reaches binary plist HTTP send | clone/preserve unknown fields; Honda Type111 response shape unknown. |
| Own Type111 listener/dataPort | Honda Type110 opens listener; Type111 unhandled | separate listener ownership is portable, exact lifecycle needs Honda proof. |
| Reuse authenticated session material / per-stream connection ID | Honda Type110 KDF uses session master material + connection ID; stream type not an input | Type111 reuse is plausible but exact ID/key lifecycle unproven. |
| Exact prologue checks and fail-closed hook install | Honda Thumb sites and fingerprints exist | principle portable; Honda current-load identity/patch safety not ready. |
| Session generation, teardown, UI lifecycle, keyframe recovery | Honda teardown and screen lifecycle partially recovered; no exact ViewArea/suggestUI semantics | all require Honda proof; not importable assumptions. |
| Primary stream remains stock while secondary privately owned | Honda Type110 can remain its own route | target architecture, not yet demonstrated with Honda. |

Do not copy addresses, token generation, Type111 fields, or vehicle assumptions from MHI2.
