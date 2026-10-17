# Merged-main clean-clone test receipt

**Run date:** 2026-10-17
**Repository:** `bmreyes25/ClarityLink`
**Source:** merged `main` commit `4c448cbd3e2775abbff5aa1bb6074a6b872d0740`
**Checkout:** fresh shallow clone; `git status --short --branch` was clean before the run
**Command:** `PYTHON=/tmp/claritylink-receipt-venv/bin/python bash tools/run_tests.sh`
**Result:** 1,197 passed, 29 skipped, 0 failed; configured runner exited 0. Three self-locator smoke tests passed; simulator checks passed; `git diff --check` passed. Private/capture-backed replay scripts are skipped by the configured runner.

The second run in that same clone returned the same pytest totals and configured-runner result. One run's complete stdout is retained at `/tmp/claritylink-main-4c448cb-configured-suite.log` on the local host, SHA-256 `d9f72a85f3da29e4b3b4f201f654aa7a17992244984a243440841c17a3e1116a`. The log is a local receipt and is not included in the public repository.

Environment and input fingerprints:

- Python: `3.14.6`
- pytest: `8.4.2`
- Node.js: `v24.18.0`
- `tests/` Git tree: `ac68fa4ce5dbd97f52b895f977dedaf3c19290ca`
- `tools/run_tests.sh` SHA-256: `829e34fb31da29a9281192b5da6377b5eb3aaaf1c44eb69363f3095710e890fc`
- `requirements-test.txt` SHA-256: `81f374e189b5f9bff3cc5b852f3141d3342f01edcdb16d41ee95cac18c2782b6`

## Superseded totals

Earlier notes recorded 1,507 passed/15 skipped for candidate `3d6f8bf` and 1,208 passed/18 skipped for merged main `4c448cb`. Neither count is accepted as clean-clone evidence: the former lacks a retained environment/output receipt, and the publication-candidate worktree was later observed to contain ignored local tool scripts; the latter did not reproduce in this clone. A 1,507/15 run was reproduced in that candidate worktree, but the effect of its ignored files was not isolated. The earlier attribution to a clean clone is therefore unverified. The candidate-worktree result is retained only as a historical local-worktree observation, not as a clean-publication result.

The API17 emulator runner was not executed. These results cover the configured offline suite only; they do not establish API17 runtime or Honda compatibility.
