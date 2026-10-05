# R6F Type111 evidence map

| Evidence | Status | Needed next |
|---|---|---|
| /info request | CURRENT_IOS_PRIOR_LAB | real ClarityLink request path/type metadata |
| accepted /info response | UNKNOWN | T4 then T5 in same session |
| SETUP request | CURRENT_IOS_PRIOR_LAB | real body field paths/types |
| stream type 110 | CURRENT_IOS_PRIOR_LAB | real descriptor correlation |
| stream type 111 | CURRENT_IOS_PRIOR_LAB | real descriptor correlation |
| streamConnectionID | HOST_IMPLEMENTED | sanitized per-session correlation from real request |
| dataPort | HOST_IMPLEMENTED | real response/listener acceptance |
| security/session context | UNKNOWN | authority-owned opaque context and Type111 derivation |
| screen advertisement | HOST_IMPLEMENTED | real accepted /info capability |
| listener expectation | INFERRED | real peer connection direction/timeout |
| media protection generation | UNKNOWN | real authenticated frame evidence |
| teardown | HOST_IMPLEMENTED | multiple real disconnect/reconnect cycles |

No row is `CONFIRMED_REAL_IOS` for ClarityLink. R6F should first connect an authorized authority, then collect T0–T8 metadata before Type111 security/media changes.
