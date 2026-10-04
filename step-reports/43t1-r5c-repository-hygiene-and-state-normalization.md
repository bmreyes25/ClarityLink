# 43T1-R5C — repository hygiene and state normalization

## Baseline and recovery

- Starting HEAD / origin/main: `2e32be77d18064080980ce96a6e77e3bbb88ba70` on `main`.
- Initial dirty tree: six tracked modifications (`EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, `step-reports/README.md`, `tools/check_repo_health.py`) and untracked R3 drafts plus R5Y host sandbox source, fixtures, and docs. During inspection `ROADMAP.md`, the R5Y report, and an ignored R5Y checker became visible, and the R5Y package path changed. See the [per-path inventory](../research/repo/r5c-precleanup-worktree-inventory.md).
- Recovery: ignored `.local-backups/r5c-repo-recovery/` contains `git diff --binary`, HEADs, initial short status, initial untracked path list, and SHA256 values for text drafts. It copies no firmware, private capture, or secret. The narrow `.gitignore` additions explicitly protect `.local-backups/`, `.local-artifacts/`, and `private-captures/`.

## Disposition

The six R3 draft files are coherent historical static analysis from before R3A/B/C. Their decision is superseded by expanded R3C, but wrapper, Setup, callback, and seam detail is useful. Preserve them in their original milestone paths and index them as a historical draft; see [R3 disposition](../research/repo/r5c-r3-draft-disposition.md). No R3 draft is deleted.

The R5Y source, docs, fixtures, report, boundary checker, and mixed tracked edits were separate concurrent host-model work. They were not authored by R5C and changed during inventory. They were committed and pushed separately at `a88d679`, which now matches `origin/main`. R5C did not stage those files. No R5Y file was deleted or overwritten; the original tracked diff and untracked hashes remain in the local recovery record.

Current-state drift was identified in `NEXT_ACTION.md`, `PROJECT_STATE.md`, `ROADMAP.md`, `EVIDENCE_INDEX.md`, and `step-reports/README.md`. The top current sections now identify R5B as the latest completed public research milestone, with `R5B_NO_LAWFUL_ANALYZABLE_ARTIFACT_FOUND` / `GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`, Civic `1.F1A5.15` metadata, no lawful receiver payload, R5X model-only, R4D possible but unproven, R3C runtime NO-GO, Rules v2, and offline/public-research-only authorization. `NEXT_ACTION.md` no longer has two competing current-action headings. Historical decisions remain in dated sections. See the [consistency audit](../research/repo/r5c-current-state-consistency-audit.md).

The existing safety matrix R3 and R5Y rows are preserved. The separate R5Y tracker/checker edits are now in `a88d679` and are not staged by R5C. The R5B index links the report, acquisition log, lineage map, shortlist, gate, and Type111 triage; Rules v2 and R4A/B/C/D, R5X, and R5B remain indexed.

## Artifact and private-data audit

The baseline `.gitignore` already has a root allowlist, private capture exclusions, and `*.pcap`/`*.pcapng`/binary/archive rules. R5C added explicit narrow local paths. No tracked APK, ELF-style payload extension, packet capture, signing key, or archive was found by tracked-path inspection. A bounded content scan flagged one OCR fixture with a VIN-shaped string, one synthetic lifecycle token, and synthetic identifier fixtures in five tests. Their context identifies them as fixtures; no actual credential, private VIN/MAC capture, firmware signing material, or proprietary firmware payload was identified. The audit records categories and paths only; no token or identifier value is reproduced here. No history rewrite was attempted.

## Phase A decision

**Repo hygiene decision: `R5C_REPO_CLEAN`** after the R3 historical draft and R5C state documents are committed and the worktree is verified clean. R5Y resolved independently at `a88d679`, so R5C can stage only its own files. The final commit hashes and status are recorded after verification. Phase B begins only after that clean state is reached. No Honda/ADB/runtime action was performed during Phase A.
