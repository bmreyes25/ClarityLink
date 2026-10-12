# P1-C5 — evidence and production-ingress gates

The [versioned manifest](p1c5-ingress-decision.json) has evidence ID, source category, exact report path and SHA-256, original artifact identity where available, verification method, supported claim, scope/version, independent review status, contradictions and unresolved conditions. The [engine](../../src/carplay-session-model/ingress_decision.py) accepts only exact records in its reviewed catalog and rehashes the local report. This guards against accidental report drift or a fixture self-attesting a new claim; it is not cryptographic attestation of authorship. The P1-C3 Binder report includes decompiled APK evidence whose original APK hash is unavailable; the `jmcs` hash does **not** identify that APK.

| Gate | Required proof for a deployable ingress | Current status across candidates |
|---|---|---|
| A | Authentic active-iPhone secondary video or route source, with app provenance | Unknown; PlayPort other-receiver video is a different scope. |
| B | Actual stock session-bound media or metadata endpoint | Unknown; status Binder is not content. |
| C | Authorized authentication and per-stream security contract | Unknown for a separate ClarityLink consumer. |
| D | Stable stock session identity, generation, stream binding | Unknown outside `jmcs`. |
| E | Effective caller permission and ClarityLink admission | Unknown; exported symbol/service name is insufficient. |
| F | No displacement or corruption of stock Type110 | Conditional design intent, no coexistence proof. |
| G | Honda audio, calls and Siri retained | Conditional design intent, no coexistence proof. |
| H | Secondary stop, parent teardown and failure isolation | Project model only; stock callback absent. |
| I | Actual Android 4.2.2/API17 boundary compatibility | Host/emulator evidence cannot prove Honda admission. |
| J | No prohibited stock change | Candidate design can avoid changes; actual interface still required. |
| K | No Honda APK installation | A separate process needs proven UID/service admission. |
| L | Narrow, separately reviewable validation path | Offline new-artifact task exists; later device action remains unauthorized. |

Allowed gate values are `PROVEN`, `CONDITIONAL`, `UNKNOWN`, `FAILED`, and `NOT_APPLICABLE`. Every mandatory gate must be `PROVEN` by a reviewed positive source record for deployment; `NOT_APPLICABLE` does not silently waive one. The nine source categories remain distinct: `HONDA_STATIC_VERIFIED`, `HONDA_LIVE_READ_ONLY_VERIFIED`, `REAL_IPHONE_LAB_VERIFIED`, `API17_EMULATOR_VERIFIED`, `HOST_SIMULATION_ONLY`, `OFFICIAL_DOCUMENTATION`, `EXTERNAL_PRIOR_ART`, `HYPOTHESIS`, and `UNKNOWN`. Evidence scope must match the exact candidate and gate. A report that establishes absence in reviewed artifacts cannot prove a positive extension. Contradictory, missing or stale records fail closed.

**Four independent properties:** an internally consistent symbolic owner model is `MODEL_ONLY`; interface sufficiency needs a reviewed external boundary; live validation needs a matching Honda session observation; production eligibility needs all gates and no contradictions. Original-goal validation additionally needs active Apple Maps/Waze source identity and Display 1 output evidence. The present catalog approves no positive external interface or Honda-live proof. The engine's computed `deployment_eligible` and `original_goal_validated` are false for all seven candidates. It does not alter production code or enable any runtime feature.

**Decision classifications:** `FULLY_SUPPORTED_EXISTING_INTERFACE`, `FEASIBLE_NEW_USER_SPACE`, `ADDITIONAL_APPROVED_DATA_PATH_REQUIRED`, `CONDITIONAL_MISSING_INTERFACE_PROOF`, `LAB_ONLY_ORACLE`, `PROHIBITED_STOCK_MODIFICATION_REQUIRED`, and `UNSUPPORTED_OR_NO_EVIDENCE`. They express architectural disposition, not permission to execute. Current A/B are conditional; F is lab-only; G needs another approved source; C/D/E have no usable original-goal interface. The current final decision is `P1_C5_NO_GO_PENDING_NEW_INTERFACE_EVIDENCE`.
