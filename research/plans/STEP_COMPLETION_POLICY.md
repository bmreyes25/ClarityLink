# Required checkpoint after every project step

Requested by the user on 2026-09-25. This applies to every subsequent ClarityLab step, including acquisition substeps.

1. Preserve the pristine September 18 backup and the read-only partial forensic original. Work only on separate working copies. Before a later vehicle change, identify its exact original files/images, verified hashes, and reversible restoration procedure. A backup alone is not proof of boot-independent recovery.
2. Codex verifies the step against its declared exit criteria using the actual files, hashes, logs, tests, and physical observations where required. A user report, model response, shell exit code, or completion marker alone does not establish success. Record any incomplete or unavailable evidence explicitly.
3. Update `STEP_STATUS.md` and the relevant research report/run card with what changed, what was verified, test commands/results, limitations, and the next gate. Never mark a partial step complete.
4. Check Git exclusions and staged content. Raw firmware/images, archives, private runtime logs, phone/route/account data, generated per-device scripts/manifests, and credentials remain local and outside Git. Only source and sanitized derived documentation/fixtures may be pushed.
5. Commit and push the verified checkpoint to the private GitHub repository. Verify that the commit reached `origin/main`, record the commit ID, and report the verification result. If a step fails, push a sanitized failure/status checkpoint rather than implying it passed.

The local model gives advice only; Codex performs the verification and repository checkpoint. No unattended model output may authorize or execute a vehicle write. Do not proceed through a dependent gate until the required verification passes.
