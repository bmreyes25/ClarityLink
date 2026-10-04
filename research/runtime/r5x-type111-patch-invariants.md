# R5X — Type111 theoretical patch sandbox invariants

**MODEL_ONLY · NOT_DEPLOYABLE · NOT_HONDA_BINARY · NOT_REAL_CARPLAY · NOT_MFI · NO_REAL_JMCS_PATCH.** These are executable host-model checks, not Honda receiver properties.

| Invariant | Sandbox check | Proof boundary |
|---|---|---|
| Type110 response remains byte-for-byte/model-identical unless explicitly modeled otherwise | Frozen primary descriptor is the same object; opaque synthetic bytes and stock-only tuple remain unchanged | No Honda serialization or runtime proof |
| Type111 augmentation belongs to one session generation | Child descriptor, listener, security, decoder and sink carry the same generation | Generation is invented, not a Honda session ID |
| Type111 listener never outlives its session | Exact-generation teardown sets mock listener `open=False` | No real socket exists |
| Type111 cleanup is idempotent | First exact teardown returns true; subsequent returns false without mutation | No target finalizer proof |
| Type111 failure does not break Type110 model state | Failure restores stock response and retains primary object | No Honda Type110 coexistence proof |
| Mock sink clears on stale/lost/teardown | Displayed string becomes `None`; reason is recorded | No physical pixels or window |
| No Type111 setup without explicit flag | Requested child with `enable_type111=False` raises `PatchError` | Host policy only |
| No path claims Honda compatibility | Labels and docs retain `MODEL_ONLY`; no Honda artifact import | Review must reject promotion |
| No path produces deployable artifacts | No writer/backend; forbidden artifact names rejected; test verifies no file created | Does not audit unrelated repo code |

## Stop conditions

The following remain `UNKNOWN` and block any claim of Honda compatibility: Honda response schema; Honda Type111 security behavior; Honda Display 1 sink; warning/z-order policy; same-session cleanup ownership; stock Type110 coexistence. Discovery of one item does not imply the others. R3C still controls receiver runtime NO-GO; Rules v2 requires a separate high-risk review and exact authorization before any future car activity.
