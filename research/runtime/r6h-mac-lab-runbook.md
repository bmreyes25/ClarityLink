# R6H Mac lab runbook (hardware-gated)

This runbook prepares the first lawful Mac session but does not authorize provisioning or claim a real session.

1. Obtain the exact R6F-selected user-owned Carlinkit CPC200-CCPA with compatible LIVI Link revision. Keep purchase/provenance details private; do not use a Honda unit or identity.
2. Re-pin/review the LIVI upstream source and apply the maintained patch from `third_party/patches/livi/0001-control-delegate-dispatch-and-bounds.patch`. Build LIVI and verify the app-root control delegate plus authenticated-state assertion. The patch wires `CLARITYLINK_LIVI_BRIDGE_SOCKET` from the LIVI process environment into the per-session delegate.
3. Confirm the Mac USB inventory shows the intended unit and validate model/revision against current upstream LIVI Link support. Do not provision while compatibility or rollback is unknown.
4. Only use upstream-documented backup/provision/restore instructions. Preserve backups outside Git; if reliable backup is unavailable, stop before modification.
5. Configure ClarityLink with a stable local identity/profile and private AF_UNIX socket path. Preflight must fail if same-UID peer credentials, socket permissions, bounded frames, generation, INFO profile validation, redacted logging, or Mac-only binding fails.
6. Start ClarityLink with `.venv/bin/python tools/r6h_livi_receiver.py serve --profile <reviewed-profile.json> --confirm-user-owned-cpc200`. Start LIVI with `CLARITYLINK_LIVI_BRIDGE_SOCKET` set to the same socket path. The lab tool checks the CPC200 USB product label, lawful-user confirmation, profile evidence, Mac platform and forbidden credential/vehicle environment variables. Start `ReceiverSession` and LIVI. A real attempt counts only if LIVI proves the successful MFi auth response, verified pair session, and subsequent decrypted control request in the same session; ClarityLink then receives exactly one real `/info` request and owns the response. Preserve only sanitized ordering/type evidence.
7. On disconnect, close receiver listeners and bridge, invalidate that generation, and reconnect with a fresh generation. No synthetic peer may be reported as iPhone progress.

Current R6H status: software path is implemented and host-tested, but the CPC200 is absent; hardware/phone steps were not executed. No hardware was provisioned or connected.
