# R6G failure attribution matrix

No hardware/authentication/iPhone attempt occurred. Runtime failure attribution is therefore not applicable; these are source/software boundary findings, not failed authentication tests.

| Layer | Status | Evidence / next discriminator |
|---|---|---|
| HARDWARE | HARDWARE_REQUIRED | Current Mac USB inventory did not identify CPC200/Carlinkit/LIVI. Verify a specific owned unit and VID/PID before provisioning. |
| LIVI_LINK | NOT_TESTED | No CPC200 or provisioned LIVI Link. Read compatible revision/provisioner metadata once a unit exists. |
| MFI_AUTH | NOT_TESTED | No genuine coprocessor available; no auth commands sent. |
| IAP2 | NOT_TESTED | No iPhone session. |
| CARPLAY_ACTIVATION | NOT_TESTED | No iPhone session. |
| LIVI_CONTROL | SOURCE_SEAM_FOUND_PATCH_REQUIRED | Pinned source owns control path in `CpStack`; no delegate API. Add and verify the pre-dispatch delegate. |
| CLARITYLINK_ADAPTER | HOST_CONTRACT_IMPLEMENTED | Python provider and synthetic conformance tests exist; real LIVI bridge implementation absent. |
| INFO_SCHEMA | NOT_TESTED | No real request/response. Required /info field readiness remains per R6F audit. |
| SETUP_SCHEMA | NOT_TESTED | No real SETUP observed. LIVI stock SETUP side effects must be bypassed only when ClarityLink owns response. |
| NETWORK | NOT_TESTED | No authority service or phone network used; no receiver listener opened. |
| UNKNOWN | NONE_OBSERVED | No live attempt means no runtime failure to attribute. |

Source evidence is in [LIVI source baseline](r6g-livi-source-baseline.md), [architecture map](r6g-livi-carplay-architecture-map.md) and [control seam](r6g-livi-control-session-seam.md).
