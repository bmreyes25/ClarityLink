# 43T1-R6B — authentication substrate and real-iOS negotiation boundary

Date: 2026-10-04. PR #4 was merged first at `07f73167cde489448c4706faf1fb93092a88225b`. R6B branch `architecture/r6b-auth-substrate` was created from `origin/main` at that merge commit in `../clarity-r6b-auth`; no pre-merge R6A lineage was reused. The worktree started clean.

## Authentication and session outcome

The [inventory](../research/runtime/r6b-authentication-session-inventory.md) distinguishes the R5Z/R6A synthetic receiver, the earlier PlayPort lab, public hardware-backed receiver projects, and future Honda auth. The old 43P allowance for a recovered shared identity is narrower than R6B's explicit prohibition and was not used. Apple describes MFi accessory authentication as hardware-backed. No user-owned genuine coprocessor or licensed service was established in this checkout, and PlayPort's default recovered-key path is excluded. Thus no real iPhone connection or authentication attempt was made with this receiver.

`AuthenticationProvider` now separates a lab handoff, synthetic replay and Honda evidence-gated stub. `CarPlaySessionTransport` separates authenticated structured control requests/responses from the receiver. `ReceiverSession` handles `/info` and SETUP after a handoff; its fake-channel test is an adapter test, not real authentication. The [transport map](../research/runtime/r6b-host-session-transport.md) locates the absent authenticated control-channel handoff. Live lab binding was not attempted because no legitimate authority is available.

Authentication decision: **R6B_AUTH_ADAPTER_PARTIAL**. iPhone negotiation decision: **R6B_REAL_IOS_NOT_REACHED**. Media decision: **R6B_REAL_TYPE111_MEDIA_NOT_REACHED**. First failed gate: lawful host authentication and control-session handoff.

## /info and receiver work

`InfoProfile` assembles identity, display, modes, audio and HID field families and refuses missing injected capabilities. A stable synthetic lab identity is generated outside Git with owner-only permissions. [Field ledger](../research/runtime/r6b-complete-info-field-ledger.md) explicitly places `altScreenURLs` in the phone request and `enabledFeatures` in session SETUP, rather than inventing them in `/info`. `tools/r6b_info_diff.py` compares known-good and candidate dictionaries by field path/type/family while omitting values. Real audio/HID descriptors and iPhone acceptance remain unknown. Trace events use a strict allowlist and cannot record keys, certificates, MACs or raw identifiers.

R6A Type110/Type111 Setup, response, listeners, generated-key ChaCha, framing, AVCC/H264 and HostWindowDisplay remain intact. Replay exercises Type111-before-Type110 and Type110 preservation. No real request exists to revise the inferred response schema. No real Type111 listener connection, encrypted media, decrypted frame, H264 extraction, decoded frame or host display occurred.

Highest continuous R6B integration tier: **below R6B-T0**. Highest R6 level: **R6_L1**. [Readiness](../research/runtime/r6b-custom-receiver-readiness.md) and [outcome matrix](../research/runtime/r6b-authentication-outcome-matrix.md) record the exact next input. The [dependency review](../research/runtime/r6b-external-receiver-dependency-review.md) prefers wrapping a supported hardware/service API and avoids GPL code copying or restricted identity use.

## Safety, verification, next milestone

No Honda, ADB, vehicle, Honda receiver execution or target adapter work occurred. No authentication bypass, key extraction, certificate copy, phone patch or restricted Apple material was used. Focused auth/session tests include 100 replay initialize/close cycles, redacted logs, invalid Setup containment and stale transport checks. The final local offline suite passed with **855 tests passed, 14 skipped**. Repository health passed with **0 broken curated links**, and `git diff --check` passed. Offline CI and CodeQL were pending at commit time and are not presumed green; their exact-HEAD results will be checked after push.

Next recommendation: **GO_FOR_R6C_AUTH_HARDWARE_INTEGRATION**. Integrate a user-owned genuine MFi coprocessor or authorized licensed authentication service and expose its authenticated control-session handoff to ClarityLink. Then run the first real iPhone `/info` and Setup experiment on the Mac. Do not return to generic firmware hunting or begin Honda deployment.
