# CL-T111-01B — genuine `/info` caller execution boundary

**Date:** 2026-11-11
**Result:** The original `/info` callsite and the PR #117 stock-delegating wrapper remain unexecuted through Honda's caller. The one bounded startup hypothesis is supported by the preserved stock/modified traces. The required receiver-owned session and Screen were not available in the offline runtime.
**Disposition:** CL-T111-01 acceptance remains incomplete. `NATIVE_WRAPPER_EXECUTED` is not earned. `HONDA_TYPE111_NOT_PROVEN` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remain in force. `safeForHonda() == false`.

## Baseline and provenance

The public task worktree was created clean from `origin/main` at `f32f87d3f5737f3fda8d50e06ab9663c4087a810`, branch `codex/cl-t111-01b-info-caller-20261111`. The original `cl-r4-reliability-completion` checkout remains dirty and two commits ahead of its upstream; no files in that checkout or private archive were changed. The original hook's `PREFLIGHT_UNAVAILABLE` result was not bypassed; this task uses the modern guard in the new worktree.

At the start, related PRs were open:

| PR | Head | State/check note |
|---|---|---|
| #117 stock pass-through | `cfd64183b02840ff75646d93babbac6e17eb3f71` | Open; offline tests pass, `api17-navigation` fails |
| #153 native display augmentation | `a945ead50a4cd36db935b7865a15bb88f6a1f56f` | Open; no checks reported |
| #156 CL-T111 roadmap | `00d2e74da69e492de77a2e942df53f42abd987e7` | Open; offline test failure is the known source-lock issue |
| #158 CL-T111-01 checkpoint | `6fa05aa6ea55c900a8c2b59998db04999a0d2e59` | Open; offline test failure is the known source-lock issue |

The baseline `collector.py` source-lock failure remains tracked separately in issue #157; this task did not weaken verification or alter its expected hash. The report uses the existing CL-T111 roadmap and F1–F13 contract. No milestone status or finish-line item is inferred from this result.

## Caller and execution boundary

Static research confirms that the stock receiver has an `/info` construction path, separate from SETUP handling. The callsite and PR #117 wrapper were not reached in the offline runtime, so the actual receiver-owned arguments, original-callee invocation count, and stock-versus-modified response equivalence are not established here.

The existing displays augmentation path depends on a receiver-owned session and its Screen. The prior constructor/helper checkpoint used genuine Honda CFLite objects but did not create that session association. The detailed private caller and argument map remains outside public Git.

## Bounded startup hypothesis

The test plan was recorded in a nonpublic execution note before the trace comparison.

- **Question:** Did the stock-delegating modification cause the startup stop before the `/info` handler?
- **Hypothesis:** No. Stock and modified receivers stop at the same archived Bionic fatal event before the target request path.
- **Expected observation:** Both paired receiver runs exhibit the same normalized runtime failure signature as the standalone API17 control, without reaching the `/info` handler.
- **Control:** The preserved API17 control and paired stock/modified receiver run under the same archived offline runtime.
- **Stop condition:** One comparison. If both images match and neither reaches `/info`, stop; do not add simulated services or retry with speculative guest changes.

The archived stock and modified traces match the control at the Bionic failure boundary, and neither shows evidence of reaching the `/info` handler or session-creation path. This supports the hypothesis that the pass-through modification did not cause the stop, but the receiver-side trigger remains unknown. Earlier missing Android service paths are correlations, not established causes. Raw trace details remain private.

One initial parser attempt incorrectly required control mapping data that the preserved control log did not record; it exited before reaching a conclusion. The corrected bounded comparator verified the receiver mappings and compared only captured control fields. It completed. No QEMU image was rebuilt or booted for this checkpoint. The first local documentation-check invocation used `python`, which is not installed on this host; rerunning the repository check with `python3` passed. The first public-safety invocation selected the base diff before the new report was staged and inspected zero files; the authoritative staged checks subsequently scanned both files and passed.

## Execution result and evidence class

- The genuine stock `/info` callsite was **not reached** in the archived runtime.
- The PR #117 wrapper was **not entered through Honda's caller**.
- The original Honda `/info` builder was **not invoked** in this checkpoint; its original-callee exactly-once behavior and stock/modified output equivalence at the caller remain untested.
- The existing CL-61 direct constructor and candidate-helper results remain bounded `HONDA_CF_INTEGRATION_TESTED` / `TYPE111_INFO_CANDIDATE_TESTED` evidence only. They are not repeated or promoted here.
- The startup comparison is **archived paired-runtime evidence reanalyzed**. It is not new receiver execution, a Honda session, or `NATIVE_WRAPPER_EXECUTED` evidence.
- Existing PR #117 ARM/Thumb tests and PR #153 host/NDK tests are not rerun or represented as this checkpoint's runtime proof.

The exact private original and modified image fingerprints were recomputed against the preserved files and match the CL-61 evidence record. Proprietary target hashes, addresses, disassembly, raw traces, and runtime artifacts remain private. No original executable segment or archive was modified.

## Tests and checks

| Check | Result | Boundary |
|---|---|---|
| Archived signal-frame extractor / receiver mapping / normalized stock-vs-modified comparison | Pass | Reanalysis of preserved CL-61 offline runtime logs; receiver child identified by its paired launch and startup output |
| Initial control-map comparator | Failed before conclusion | Standalone control log has no `SIGNAL_MAP`; corrected comparison did not infer one |
| Original / modified private artifact identity check | Pass; matches private CL-61 record | Identity check only; no publication of proprietary hashes |
| Original-callee invocation, wrapper boundary, ABI preservation, CF ownership, stock `/info` equivalence, Type110 runtime isolation | Not run / not established | Genuine receiver caller/session unavailable |
| Repository documentation/hygiene (`python3 tools/check_repo_health.py`) | Pass; 902 Markdown files, 153 indexed reports, zero broken links/unindexed local paths | Exact staged two-file working tree |
| Public-safety gate (`--staged`) and `git diff --cached --check` | Pass | Exact staged two-file working tree |
| Broader repository tests and source-lock baseline suite | Not run | Documentation-only checkpoint; the known collector source-lock issue remains tracked in #157 |
| Initial PR #159 offline CI | Failed on missing report-index entry | Corrected by adding the report to `step-reports/README.md`; this replacement checkpoint requires fresh CI |
| ECC read-only code/documentation review | Pass; no actionable findings | Reviewed the exact staged public diff |
| Independent security/public-safety review | P2 findings resolved by redaction | Final pass confirmed no remaining issue in the current staged diff |

## Private dependency map and next experiment

The earliest confirmed blocker is the receiver startup failure before a session context was observed. Its exact trigger and the point at which the receiver creates its session remain unknown. The existing displays augmentation path needs Honda-owned session and Screen state, but this checkpoint did not establish an authentication-stage requirement.

The current offline environment can execute genuine Honda native constructor and CFLite code in bounded probes, but has not reached a receiver-owned session. The next experiment should observe a genuine receiver-created session and its Screen in a process-aware API17 runtime, then follow the real `/info` request. It must stop if startup fails before session creation. No session or callback state should be synthesized.

**CL-T111-01B acceptance: NOT PASSED.** The required original-caller wrapper execution is absent. **`HONDA_TYPE111_NOT_PROVEN`; `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`; `safeForHonda() == false`.**
