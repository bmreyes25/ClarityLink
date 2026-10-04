# 43T1-R5Z — offline custom receiver laboratory

## Scope and starting state

- Branch/worktree: `experiment/r5z-custom-jmcs` at `../clarity-r5z-custom-jmcs`, created from clean `main` HEAD `500ee9a8ffdd4f3e91a99293c1e873435949533e`. The R5D worktree and canonical current-state files were not changed. Implementation/final HEAD is recorded by the branch history after commit; no merge to `main` is part of R5Z.
- Honda contacted: **NO**; ADB used: **NO**; vehicle connected: **NO**; Honda files modified: **NO**; `jmcs` modified on Honda: **NO**; Type111 used on Honda: **NO**. No real iPhone negotiation, MFi authentication, key use, or deployment occurred.
- R3C still rejects runtime interposition into stock `jmcs`. R5Z explores an offline replacement architecture, not a hook. Rules v2's evidence levels and vehicle authorization gate remain in force.

## Implementation

The `claritylink_jmcs` host package has strict stream ID validation, binary-plist lab response construction before serialization, preserved Type110 model response entries, generation-owned loopback listeners, symbolic event tracing, a bounded 128-byte ScreenStream-family parser, a security-provider interface, public FFmpeg H.264 decoding, host PNG/in-memory sinks, deterministic teardown and resource counts. `tools/r5z_receiver_lab.py` supports `replay`, `captured-setup`, `synthetic-client`, and `lab-receiver` with sanitized/local JSON inputs. The setup order tests cover Type111 before Type110 and vice versa. The Type111 child can be torn down independently while the primary remains active.

The Honda compatibility package maps only confirmed static Type110 fields, response pair and known teardown types. Unknown Honda Type111 response and teardown paths raise `EvidenceRequired`. The ignored local `jmcs` ELF was read only for SHA-256, format and symbol-name confirmation; its hash is `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. No binary, proprietary code, raw capture, key, certificate or private identifier was copied or committed.

`EvidenceRequiredSecurity` is the default and refuses encrypted Type111. `ClearLabSecurity` is opt-in for generated clear fixtures only. The parser follows the **Honda Type110** envelope family as an explicit Type111 lab hypothesis; it is not a verified current-iOS Type111 parser. The FFmpeg adapter decodes Annex-B test access units. VideoConfig/AVCC handling, real encrypted media, full `/info`, MFi/authentication, actual Type110 media/security equivalence, host GUI window, Honda ABI bridge and Honda Display 1 output remain incomplete.

## Evidence and artifacts

- [Compatibility map](../research/runtime/r5z-jmcs-compatibility-map.md), [Honda Setup reconstruction](../research/runtime/r5z-honda-setup-transaction-reconstruction.md), [call graph](../research/runtime/r5z-honda-receiver-callgraph.md).
- [Type111 response schema](../research/runtime/r5z-type111-response-schema.md), [security design](../research/runtime/r5z-type111-screen-security-design.md), [transport reconstruction](../research/runtime/r5z-screenstream-transport-reconstruction.md), [secondary advertisement](../research/runtime/r5z-carplay-secondary-display-advertisement.md).
- [Honda gap map](../research/runtime/r5z-honda-integration-gap-map.md) names the artifact/function/static task and waiting code for each unknown. [Host readiness](../research/runtime/r5z-host-integration-readiness.md) separates successful host components from actual Type111 compatibility.

## Host integration and regression evidence

The full Mac integration test starts a session, creates Type110 and Type111 response entries, binds the second listener to localhost, connects a local client, sends generated clear H.264 inside a bounded lab envelope, decodes through FFmpeg, writes a PNG host frame, tears down Type111, verifies Type110 model state remains active, tears down the parent and observes zero tracked resources. The CLI synthetic-client mode repeats that path. This is **not** a real iPhone/CarPlay or Honda end-to-end test.

Tests cover stream-ID errors, wildcard bind rejection, stale generation, both Setup orders, default security refusal, response preservation, listener/security/decoder/response/commit faults, media/decode/display faults, teardown containment and retry after display-clear failure, sanitized trace, 100 reconnect cycles, CLI replay, and file-output ownership. The 100-cycle test is host lifecycle coverage, not a vehicle soak test.

## ECC review and findings

Manual @ECC security-review and Python-testing guidance applied to input bounds, loopback-only binding, one accepted connection, socket/read timeouts, generation ownership, rollback, fail-closed security, bounded body length, no secrets in traces, public decoder isolation and proprietary artifact handling. No independent ECC service sign-off is claimed. Known residuals: FFmpeg is an external decoder process used on controlled clear fixtures; the host output is not a GUI/cluster display; no real Type111 cryptographic input is accepted. No finding was suppressed.

The existing `step43t0d0_collector.py` could not read the branch ref in a Git worktree because it assumed `packed-refs` lived in the private worktree directory. A narrow host-only `commondir` lookup fixed the full-suite failure. No collector plan hash or device command changed.

## Verification

- Focused R5Z: `34 passed`; worktree Git-ref collector tests: `46 passed`.
- Full `PYTHON=.venv/bin/python ./tools/run_tests.sh`: `834 passed, 14 skipped`; configured standard-library and simulator checks passed.
- Repository health: passed, zero curated broken links and zero forbidden tracked extensions. `git diff --check`: passed.
- CLI `synthetic-client`: one generated frame decoded, final resource counts zero.
- Offline CI and CodeQL on exact pushed experimental branch HEAD: pending at report creation; results will be reported separately. No old run is used as R5Z verification.

## Decision and next milestone

- **Implementation:** `R5Z_CUSTOM_JMCS_RECEIVER_PARTIAL`.
- **Type111:** `R5Z_TYPE111_LISTENER_AND_SETUP_IMPLEMENTED` in the host lab, not Honda or real iPhone.
- **Honda compatibility:** `R5Z_HONDA_COMPAT_LAYER_PARTIAL` for static Type110 fields only.
- **Recommendation:** `GO_FOR_R5Z1_TYPE111_SECURITY_CLOSURE`, coordinated with R5D lawful artifact provenance. The next work needs source-tagged, privacy-cleared Type111 security/framing evidence before a real encrypted media provider or full receiver claim. Honda ABI, complete `/info`, H.264 configuration, and Display 1 remain separate blockers.

Highest continuous success level: **L2**. L5/L6 host components pass on clear generated input, but L3/L4 are not established for real Type111. L7 real iPhone lab negotiation, L8 full Honda ABI, L9 Honda Display 1 and L10 deployment are unachieved. No deployment risk review or vehicle experiment is authorized by this branch.
