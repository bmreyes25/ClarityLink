# 43T1-R7E4A — A0-R authorization packet reconciliation

**Starting PR HEAD:** `aa2f0f7827cc8f0e0742c03edc2714f6449ee5ec`  
**Collector implementation commit:** `47605adad4e83faa8e05e028cd46282848546139`  
**Collector source changed:** NO  
**Collector SHA-256:** `8693ac5d9165343bb94b9f56be4c4d0b8f3666884361e2f2d07f65a4b53a9c1d`  
**Manifest version:** `R7E4-A0R-COMMAND-SET-1`  
**Manifest SHA-256:** `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`  
**R7E4A implementation HEAD:** pending documentation-only reconciliation commit  
**R7E4A final verification HEAD:** pending exact-head hosted checks

## Reconciliation

Recomputed SHA-256 from the current collector file and Git blobs at implementation commit `47605ad...` and starting PR head `aa2f0f...`. The bytes and blob IDs are identical at all three locations and hash to `8693ac5d...`. The authorization packet's prior `fcb4ce3a...` value was incorrect and has been corrected.

The manifest already contained the correct source SHA and command set. Its bytes remain unchanged at SHA-256 `962b25f...`; no new manifest supersession was created. The prior manifest hash `5b73badc...` remains `SUPERSEDED_BEFORE_AUTHORIZATION`.

Command-set integrity: 18 entries total (`A0R-00` host inventory and `A0R-01` through `A0R-17` target reads), target writes `NONE`, retries `0`, fallbacks `[]`. The six utility paths remain operands to fixed `ls -l` metadata reads only; there is no push, delete, chmod, kill, `su`, `setprop`, mount, reboot, or USB-role command.

## Verification and authorization boundary

- Collector fixture suite: 17 passed.
- Canonical repository suite: 919 passed, 15 skipped.
- Self-locator: 3 passed.
- Simulator contract, dual-screen, guidance-expiry, and Type111 failure-twin checks: passed.
- Repository health: 793 Markdown files, 156 indexed reports, zero curated broken links, zero forbidden tracked extensions.
- Artifact checker: SHA-256 and mode gate passed.
- `git diff --check`: passed.
- Starting PR head `aa2f0f...`: Offline CI and CodeQL passed; PR #19 was OPEN and MERGEABLE.
- Honda commands: NONE. A0-R: NOT EXECUTED. A0-W: NOT AUTHORIZED. Test A: NOT AUTHORIZED.

No A0-R execution is authorized by this reconciliation. The package remains `R7E_A0R_RESEARCH_HARDENED_READY`; the first separately authorizable action is A0-R only after explicit user authorization tied to collector commit `47605ad...`, source SHA-256 `8693ac5d...`, manifest version `R7E4-A0R-COMMAND-SET-1`, and manifest SHA-256 `962b25f...`.
