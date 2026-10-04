# 43T1-R5D — Honda/Acura receiver artifact provenance closure

## Decision

- **Artifact decision:** `R5D_HIGH_CONFIDENCE_PACKAGE_LEAD_FOUND`.
- **Type111 decision:** `R5D_TYPE111_NOT_TRIAGED_NO_RECEIVER_ARTIFACT`.
- **Lineage decision:** `R5D_CLARITY_DESCENDANT_LINEAGE_PROMISING` as a research direction only; no descendant receiver code relationship is proved.
- **Recommendation:** `GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`, focused on original publisher custody/hash for the named EU Civic package or an independently publisher-hosted package.

R5D found a reproduced Honda-styled European Civic bulletin that names `MRC_EU_SW_v12_4.zip` and `1.F197.70` for Mitsubishi Electric Civic units. The document says the original distribution channel was PANEX and gives a roughly 900 MB archive with 62 copied items. A forum mirror and an independent researcher's test-key signature report do not authenticate the mirror's unchanged publisher custody. No artifact passed the acquisition gate. The official US 2016/2017 versions remain VIN/dealer selected. Thus the vehicle→exact unit→public payload→SHA256→receiver chain remains open.

## Scope and worktree

| Item | Result |
|---|---|
| Starting HEAD | `500ee9a8ffdd4f3e91a99293c1e873435949533e` (`origin/main`) |
| Branch | `research/r5d-artifact-provenance` |
| Worktree | `/Users/bmreyes24/ClarityLab/clarity-r5d`, separate from main/R5Z |
| Initial state | Clean |
| Honda contacted / ADB used / vehicle connected | NO / NO / NO |
| Runtime reads / writes | 0 / 0 |
| VIN submitted / dealer portal or credentialed service used / vehicle update file used | NO / NO / NO |
| Public artifact acquired / private artifact acquired / target binary executed | NO / NO / NO |
| `jmcs` modified / Type111 used on Honda | NO / NO |

## Evidence and provenance result

The [closure table](../research/runtime/r5d-artifact-provenance-closure-table.md) records each candidate and each open chain link. The [Civic lineage study](../research/runtime/r5d-civic-version-lineage.md) separates official `1.F197.60`/`1.F196.39`, the earlier official `1.F197.00`, reproduced EU `1.F197.70`, and public-research `1.F1A5.15`. The [Clarity lineage study](../research/runtime/r5d-clarity-receiver-lineage-closure.md) keeps the preserved MY16ADA/`1.F1A2.45` target baseline separate from candidate descendants. The [source ledger](../research/runtime/r5d-source-provenance-ledger.md) gives public URLs, source classes and what each proves.

The best package identity is European Civic MRC12.4. Its bulletin copy provides model codes, supplier, PANEX location, filename and version, but the accessible payload is an unauthenticated forum mirror. The [gate](../research/runtime/r5d-public-artifact-acquisition-gate.md) therefore records `QUARANTINE_METADATA_ONLY`. No original public Honda package URL, original SHA256, component inventory or receiver payload is available. No `r5d-static-artifact-triage.md`, artifact inventory, Type111 triage or R5Y adapter map was created because their evidence preconditions were not met.

**Lineage:** Clarity↔Civic `CLARITY_CIVIC_LINEAGE_POSSIBLE`; Clarity↔Accord `CLARITY_ACCORD_LINEAGE_UNPROVEN`; Clarity↔Acura RDX `CLARITY_ACURA_LINEAGE_UNPROVEN`. Honda's 2018 Civic bulletin and the reproduced EU bulletin associate Civic units with Mitsubishi Electric ADA/MELCO; the preserved Clarity target is Mitsubishi/Andromeda. No matched code, ROM type, exact part or package hash establishes ancestry. Accord's Honda-developed Android HMI and Acura's distinct OTA metadata remain separate leads.

**Type111:** No authenticated descendant receiver component exists for static triage. Dispatch, response, `dataPort`, `streamConnectionID`, second screen, security, listener/media, decoder and teardown remain `UNKNOWN`. R3C runtime NO-GO controls. R5Y remains host-only/model-only and contributes no Honda evidence.

The [candidate ranking](../research/runtime/r5d-artifact-candidate-ranking.md) is a search heuristic, the [queue](../research/runtime/r5d-next-artifact-research-queue.md) limits next steps to public sources, and the [negative-evidence rules](../research/runtime/r5d-negative-evidence-rules.md) prevent filename, version and Type111 overclaims. The safety matrix adds research-stage failure controls.

## ECC evidence review

`ecc:research-ops` source discipline was applied throughout: Honda/NHTSA and Acura publications, publicly reproduced bulletin metadata, independent research, forum leads and unauthenticated mirrors are distinguished. The strongest official US version facts were not promoted to package access. The strongest EU package name was not promoted to authenticated bytes. Shared supplier/OS/version syntax was not promoted to receiver lineage. Static Type111 was not inferred from cluster features or literals. No speculative R5Z result entered canonical state.

## Verification

The first full run exposed an existing Git metadata reader assumption in the offline 43T0-D collector: linked worktrees store branch refs in the common Git directory. The reader now checks the worktree and common directories without running Git or changing its Honda command plan. Focused collector tests: **46 passed**. Repeated full suite: **800 passed, 14 skipped**, plus three standard-library smoke checks and simulator checks. Repository health: **passed** (555 Markdown files, 129 indexed reports, no curated broken links or forbidden tracked extensions). `git diff --check`: **passed**. The initial failure was confined to 36 metadata-read tests and resolved by this narrow worktree fix.

Implementation HEAD: `f5f8b3df717fb17125050c24a526d13c821e3e27`. [Offline CI run 37239371654](https://github.com/bmreyes25/ClarityLink/actions/runs/37239371654) and [CodeQL run 37239371550](https://github.com/bmreyes25/ClarityLink/actions/runs/37239371550) both concluded `success` with that exact `headSha`; all five CodeQL language jobs passed. The final report-only verification HEAD is recorded in the completion response. No firmware, package or private artifact is included or staged.

No Honda/ADB/runtime/vehicle work was performed. R5D is the canonical public/offline evidence track and does not authorize receiver modification, Type111 negotiation, installation, or a car experiment.
