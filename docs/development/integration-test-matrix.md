# End-to-end integration test matrix

This matrix is a planning contract. Current passes only cover the API17 laboratory rows described in the [current status](../status/current.md); no row below authorizes Honda or iPhone operation.

| Area | Offline/API17 proof | Authorized bench proof | Future target proof |
|---|---|---|---|
| Type110 continuity | Both setup orders; UI/audio/touch model; assert no secondary-stream teardown reaches main owner. | Genuine single-session main stream remains active during secondary setup/stop. | Factory center display, audio, touch, and navigation unaffected. |
| Type111 authenticity/config | Synthetic stream identity/VideoConfig and codec fixture. | Authenticated iPhone session, actual Type111 request and frames, distinct stream identity, authoritative config. | Same authenticated factory session delegates Type111 through documented contract. |
| Session and generation | Wrong session, stale generation, duplicate setup, restart and revocation. | Type111-only teardown/restart while Type110 continues. | Same plus receiver/host restart via supported ownership boundary. |
| Frames/queue/performance | Bounded queue, drop/latency and resource metrics on API17. | Actual frame decode and output stats on approved independent receiver. | Measured target path against declared performance gates. |
| Navigation geometry | Synthetic geometry and page-selection model. | Separate output geometry only. | Verified physical safe area, transform, page switching, and factory Navigation ownership. |
| Warning priority | Simulated warning withdrawal/fresh-frame recovery. Do not call this Honda evidence. | No Honda-warning claims. | Approved non-hazardous evidence of factory warning priority and no masking. |
| Failure and cleanup | Producer/View death, malformed IPC/frame, decoder close, queue pressure, disconnect, reconnect and resource cleanup. | Stream loss/recovery and independent teardown. | Approved integration loss, app exit, process death, restoration, and rollback. |
| Security / authorization | Negative tests for fake owner, unapproved source, wrong generation and malformed metadata. | Legitimate MFi authority and privacy boundary only. | Approved receiver/display contracts, no private replay/bypass, independent safety review. |

For each run record objective, baseline, source/version, method, evidence class, exact pass/fail receipts, limits, security implications, private/public boundary, decision, blockers, next task, acceptance criteria, commit and PR. No `PASS` transfers from one column to another.
