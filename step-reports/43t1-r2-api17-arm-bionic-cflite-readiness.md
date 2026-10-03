# 43T1-R2 — API-17 ARM/Bionic and CFLite static readiness

**Decision: `RETURN_TO_OFFLINE_WORK`**

## Scope and repository state

- Starting branch/HEAD: `main` / `b603859c089915547070eb8d6b63af5afca57d14`.
- Final R2 implementation HEAD: `ff90d02d1d1c6c3427d34917e4611dfbd4874810` (`Add 43T1-R2 offline runtime safety evidence`). Hosted outcomes below are tied to this commit; the report-only result update follows it.
- Honda contacted: NO.
- ADB used: NO.
- Vehicle/runtime writes: 0.
- No RAM attachment, live listener, Type111 negotiation, or Honda runtime behavior was attempted.
- Sources: versioned AOSP Android 4.2.2/API 17 Bionic, ARM AAPCS32/AAELF32/ARMv7 architecture references, public Apple CoreFoundation references (reference only), preserved hash-matched Honda `jmcs` artifact, and existing ClarityLink reports. Evidence labels are defined in [the API-17 note](../research/runtime/api17-arm-bionic-harness-analysis.md) and [CFLite audit](../research/runtime/honda-cflite-ownership-static-audit.md).

## Findings

- Harness result: modeled two-halfword patching exposes mixed instruction states for both write orders. The Honda Setup BL at `0x28af72` crosses the configured 4-byte fetch-group boundary. Cache synchronization does not imply atomicity or stop threads. Host restoration succeeds only for modeled bytearray states; this is not target recovery evidence.
- Inline patch viability: `INLINE_PATCH_REQUIRES_UNPROVEN_THREAD_STOP_AND_REMAINS_NO_GO`.
- CFLite ownership: static callback tables and retain/release edges are resolved for the observed stock response dictionary, streams array, and Type110 entry. The observed getters return borrowed pointers. PREP2 remains a clean-room model; no project-created Type111 entry was exercised in Honda. Callback re-entry, all-field compatibility, serializer failure behavior, and independent lifecycle cleanup remain unknown.
- Remaining blockers: API-17 all-thread rendezvous, PC exclusion and re-entry prevention; actual Honda permissions/cache completion; interruption-safe and independent restoration; Type111 native field/callback compatibility; serializer/recovery behavior under failure; supported non-inline control transfer.
- Another offline milestone is justified: inventory naturally mediated/non-inline seams and decide whether runtime patching must be abandoned pending a supported integration path.
- A future ECC RAM experiment review is not justified by R2 evidence.

## ECC safety review

ECC security-review, research-ops, Python testing, and safety guidance was applied as a manual review. No independent ECC reviewer was available; this is not independent sign-off. Findings: do not equate cache maintenance with atomicity; do not infer stop-the-world from signal/syscall availability; preserve the mixed-instruction counterexample; treat model restoration as model-only; distinguish stock callback facts from arbitrary Type111 ownership; retain unknown serializer re-entry and independent-recovery risks; keep Apple CF and generic AOSP claims out of Honda proof.

## Verification and hosted status

- Focused Honda runtime safety, ownership/PREP2, listener/interposer tests: **349 passed**.
- Full offline suite (`./tools/run_tests.sh`): **674 passed, 3 skipped**; self-locator smoke and all configured simulator checks passed.
- Repository health: **passed**; 451 Markdown files, 113 indexed milestone/support reports, 0 broken curated links, 0 forbidden tracked extensions.
- Diff/whitespace check: **passed**.
- Hosted Offline CI: **passed** on the R2 implementation HEAD ([run 37145662690](https://github.com/bmreyes25/ClarityLink/actions/runs/37145662690)).
- Hosted CodeQL: **passed** on the R2 implementation HEAD across all configured language jobs ([run 37145662714](https://github.com/bmreyes25/ClarityLink/actions/runs/37145662714)).
- CodeQL `py/bind-socket-all-network-interfaces`: GitHub code scanning reports the alert as **fixed**; there are no open alerts for this rule. It was fixed by the earlier listener code change, not dismissed or suppressed.

## Branch protection and hygiene

GitHub's branch-protection API confirms `main` has force pushes disabled and deletion disabled; required status checks are not configured. This milestone makes no branch protection change. GitHub CLI authentication was available for repository inspection and push. Only source, tests, and sanitized reports are added; no new firmware, private capture, binding values, endpoint, key, binary output, or compiled harness output is included.

## Required decision

`RETURN_TO_OFFLINE_WORK`

This is an offline readiness result and does not authorize a Honda experiment.
