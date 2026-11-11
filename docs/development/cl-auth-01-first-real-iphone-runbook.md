# CL-AUTH-01 first real-iPhone session runbook (NOT EXECUTED)

**Status: plan only.** Nothing here is authorized by CL-AUTH-01. No hardware has been purchased, provisioned or connected, no iPhone has been used, and no Honda or vehicle is involved. Running any tier below requires a separate, documented owner authorization for that exact tier and the exact equipment, written before the step begins. `safeForHonda() == false` throughout.

This runbook extends the [R6E real-iOS ladder](../../research/runtime/r6e-real-ios-negotiation-ladder.md). Tiers must be reached in order within one continuous real session; no tier may be skipped, and synthetic, replay, or bridge-contract tests earn none.

## 1. Scope and what a success would mean

A Mac-based authenticated Type111 session would show only that ClarityLink can obtain and process Type111 in its own supported environment. It would not show Honda factory-session sharing, Type110 continuity with ClarityLink attached, Display 1 access, cluster admission, warning priority, safe rendering or reversibility. Those are separate gates (see the [readiness matrix](../../research/runtime/cl-auth-01-type111-readiness.md), section "Evidence classes").

## 2. Hardware readiness (reverified 2026-10-21 from public documentation)

| Item | Finding | Status |
|---|---|---|
| Candidate | A user-owned, genuine Carlinkit CPC200-CCPA provisioned as LIVI Link (selected in R6F). It is an engineering candidate, not a guarantee. | `AUTHORIZED_HARDWARE_REQUIRED` |
| Current LIVI Link docs | Supported on Linux and macOS. Documented firmware families: i.MX6UL with IW416, RTL8822CS or RTL8822BS (Wi-Fi only); Allwinner V821B + AIC8800D80; Axera AX520 + AIC8800D80. The provisioner probes the connected unit. A product name alone does not establish the SoC, Wi-Fi module, MFi part or revision. | SOURCE_VERIFIED_EXTERNAL |
| Provisioning and recovery | The provisioner backs up before writing. i.MX6UL restore is via the same tool ("back to the vendor firmware"); V821B/AX520 restore is by uploading the saved backup in the web interface. Flashing is at the user's own risk. A restore path is documented, not guaranteed for a particular unit. | Documented, unverified |
| Control-session ownership | Stock LIVI owns the RTSP control session. ClarityLink needs a delegate seam. The recorded patch targets the TypeScript stack, which upstream removed in `v9.3.0` ([currency check](../../research/runtime/cl-auth-01-livi-upstream-currency.md)). | **Seam not available on current upstream** |
| Version compatibility | Current release `v9.4.0` states the dongle needs its latest firmware. The pinned patch matches `v9.2.0`-era software. Compatibility between the two is UNKNOWN. | UNKNOWN |
| Mac environment | Apple Silicon macOS is documented as supported. The Mac in this lab has Node and pnpm but no Rust toolchain; the current upstream core needs Rust >= 1.88. | Gap |
| Licensing | LIVI is GPL-3.0. Any patch to LIVI code carries GPL obligations. ClarityLink code is a separate process speaking a local socket. | Review before distribution |
| Clones | Do not use an unverified clone as an authenticated receiver. Reject CP2A/CP2/CCPW variants unless the provisioner explicitly recognizes them and genuine MFi provenance is confirmed. | Rule |
| Alternative | An Apple MFi-licensed accessory authentication path is the other legitimate route. It requires an Apple program licence and its specifications are not public, so it was not assessed. No other documented, properly licensed alternative with an exposed control-session was identified. | `UNSUPPORTED` in reviewed scope |
| Purchase | No purchase is authorized. | Not authorized |

**Blocking prerequisite before T0:** design, review and test a delegate seam for the current LIVI Rust core, or formally re-pin to `v9.2.0` and establish firmware compatibility. Either is a separate, explicitly approved change.

## 3. Common rules for every tier

- Location: the Mac and a legitimate independent receiver, never the Honda. Loopback or private-network only. Offline except the iPhone's link to the dongle.
- Equipment: the user's own iPhone and the authorized authority hardware. No hidden service credentials, factory Honda keys, extracted credentials, identity spoofing, or broad packet capture of personal device data.
- Software: record the exact ClarityLink commit, the LIVI source revision and patch hash, the provisioner version, and the dongle firmware version, in the private lab record.
- Logging: only generation, event order, status, method and path, and sanitized dictionary field paths/types/counts (the existing `SanitizedTrace`). Never log pairing identifiers, certificates, challenges, keys, session identifiers, device names, MAC addresses, UDIDs, serial numbers or raw `/info` bodies.
- Evidence category: private lab record only. Public documents carry the tier reached and sanitized observations.
- Stop immediately on: any unexpected device, prompt, or network; malformed input; timeout; authority loss; a request outside the delegated set (`GET /info`, `SETUP`); any step needing an action outside the approved plan. Do not retry outside the approval.
- A tier result only counts if the previous tier's evidence came from the same continuous session.

## 4. Tier plan

### T0 — Genuine, authorized authority verified and initialized
- Equipment: the verified authority hardware, the Mac, no phone.
- Preconditions: written approval for hardware inspection and provisioning; prerequisite seam resolved; vendor backup location chosen outside Git; privately recorded provenance of the unit.
- Software: provisioner and LIVI revision per section 2, recorded.
- Expected event: the provisioner identifies a supported family read-only; backup is created; the firmware is written only after a backup check; the authority answers its status interface.
- Success: authority reachable, backup verified, `LiviAuthority` opens only a `REAL_LIVI_BRIDGE`.
- Failure/stop: unrecognized unit, failed backup, unexpected network behavior.
- Secrets: backup contains device-specific data and must stay private. Safe to log: model family, firmware version string, pass/fail.
- Cannot conclude: that the authority is genuine MFi hardware (a bridge assertion is `UNVERIFIED_HARDWARE`, never `ATTESTED`), or anything about a phone.

### T1 — Real iPhone establishes an authenticated CarPlay-capable session
- Equipment: authority and the user's own iPhone, on the dongle's network as documented.
- Preconditions: T0 evidence; written phone-use approval.
- Expected event: upstream LIVI alone (ClarityLink delegate disabled) completes the documented pairing and authenticates; the phone shows CarPlay as connected.
- Success: LIVI reports an authenticated session. This validates the dongle and LIVI, not ClarityLink.
- Failure/stop: pairing prompts for unexpected data; the phone stalls (upstream notes a Wi-Fi setup stall on transition networks).
- Secrets: pairing records and keys exist in LIVI/phone; never copy them.
- Cannot conclude: that ClarityLink receives anything.

### T2 — Real authenticated control request reaches ClarityLink through the approved delegate
- Preconditions: T1; the reviewed delegate seam is enabled; the ClarityLink bridge is listening on its private socket.
- Expected event: the delegate connects, sends the authenticated hello, receives `session_ready`, and forwards one request frame.
- Success: `ReceiverSession.open()` completes with a handoff of trust `UNVERIFIED_HARDWARE` and the first request is read.
- Failure/stop: UID mismatch, wrong hello, a synthetic bridge, a repeated session identifier.
- Safe to log: generation, handoff trust class. Not: session identifier.
- Cannot conclude: that a request type matches expectations.

### T3 — Real `/info` request received
- Expected event: a `GET` ending `/info`, forwarded as `/info`, with an empty or plist body.
- Success: `INFO_REQUEST` trace; body field paths recorded only as types/counts.
- Failure/stop: any other first request, which is a result to report, not to work around.
- Cannot conclude: that the phone accepts our response.

### T4 — Real `/info` response sent
- Expected event: ClarityLink writes one response (status 200) paired to the request.
- Success: `INFO_RESPONSE`; the delegate returns the response to the phone with no transport error.
- Failure/stop: write failure, duplicate response, timeout.
- Cannot conclude: that the phone found the content acceptable.

### T5 — iPhone continues with a subsequent protocol request
- Expected event: any later request from the same session after the response.
- Success: a further request frame arrives (this is the first evidence of `/info` acceptance).
- Failure/stop: disconnect or silence; record which and stop.
- Cannot conclude: which fields the phone relied on.

### T6 — Real SETUP received
- Expected event: a `SETUP` forwarded as `/session`, after `/info`.
- Success: `SETUP_REQUEST`; counts of stream entries and their `type` values only.
- Failure/stop: SETUP before `/info` (`info_required`), unsupported method, oversize.
- Cannot conclude: that Type111 was requested.

### T7 — Stream descriptors identified
- Expected event: SETUP contains stream entries; the types present (100/101/110/111 or others) are recorded.
- Success: the descriptor set is recorded as sanitized field paths. If no Type111 entry appears, report that outcome; it is a valid result.
- Cannot conclude: security parameters of any stream.

### T8 — Genuine Type111 SETUP observed and accepted under the authorized contract
- Preconditions: T7 shows a Type111 entry.
- Expected event: the receiver allocates a Type111 listener; the SETUP response carries its data port; the phone then connects.
- Success: a Type111 stream is listed in the response and a connection is accepted. This is a **SETUP proof only**.
- Failure/stop: duplicate IDs, listener failure, a request with stream types the adapter does not support.
- Secrets: any security parameters in the SETUP body (keys, salts) are private and are never logged or committed.
- Cannot conclude: Type111 security, KDF, frame decryptability, rendering, or anything about Honda.

## 5. After T8 (not authorized here)

Protected media needs the real Type111 security context. It stays `EvidenceRequiredSecurity` until a reviewed contract exists. A `Type111SecurityGrant` that is not synthetic is accepted only for an `ATTESTED` handoff, and no attestation verifier exists. Establishing the real key derivation is a separate evidence task and must not reuse the Honda Type110 KDF or the previously observed modern profile by assumption.

## 6. Offline pre-checks (allowed now)

```sh
python -m pytest -q tests/jmcs tests/negotiation tests/transport tests/integration
python tools/r6e_real_ios_lab.py preflight   # must report authority not available
```

## 7. Approval packet required before T0

Exact tier list, equipment and provenance, software revisions and hashes, privacy and logging plan, stop criteria, rollback path (stock firmware restore), and the operator. Approval for one tier does not extend to the next.
