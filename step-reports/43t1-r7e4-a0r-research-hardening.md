# 43T1-R7E4 — A0-R research-backed hardening (offline)

**Starting HEAD:** `69f928368edcc13df80bee37bf3b19f621cf2b9f`
**Implementation HEAD:** `47605adad4e83faa8e05e028cd46282848546139`
**Intermediate documentation/verification HEAD:** `3133e36f82b86ed2fa1a0963115f6745ae752b6c`
**Final verification HEAD at R7E4 close:** `aa2f0f7827cc8f0e0742c03edc2714f6449ee5ec`
**PR:** [#19](https://github.com/bmreyes25/ClarityLink/pull/19), OPEN and MERGEABLE at the verified head
**Decision:** `R7E_A0R_RESEARCH_HARDENED_READY`.

R7E4 applies the Android 4.2.2 and legacy ADB evidence recorded in [research](../research/runtime/r7e4-android42-target-path-research.md). The collector adds six read-only `ls -l` tool-path observations and treats absent future utilities as informational. SELinux unavailability no longer changes a successful A0-R collection result. `/data` `noexec` remains a hard blocker.

A0-W is redesigned around a single inert host marker at mode 0644 transferred with ADB sync and exact-path cleanup; it remains separately unauthorized. Future Test A requires local mode 0755, remote `ls -l` executable-bit verification, optional MD5 transport comparison, and no automatic target chmod. SHA-256 remains canonical identity. Related-platform USB-role evidence does not justify USB-role changes to A0-R.

The old manifest SHA `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. New manifest SHA-256: `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Collector source SHA-256: `8693ac5d9165343bb94b9f56be4c4d0b8f3666884361e2f2d07f65a4b53a9c1d`. The old hash is superseded before authorization.

## Verification and safety

- Collector fixtures: 17 passed.
- Canonical suite: 919 passed, 15 skipped. Self-locator: 3 passed. Simulator contract, dual-screen, guidance-expiry and Type111 failure-twin checks passed.
- Repository health: 793 Markdown files, 156 indexed reports, 0 curated broken links, 0 forbidden tracked file extensions.
- Artifact SHA-256: `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`.
- Artifact MD5: `89ef2a0e432ef1501e8a5c0431f9e41f` (transport consistency only).
- Artifact local mode: `0755`.
- Target writes during A0-R: zero.
- A0-R/A0-W/Test A: not executed.
- Honda commands: none.

**Exact-head hosted checks:** Implementation head `47605adad4e83faa8e05e028cd46282848546139` and final PR head `aa2f0f7827cc8f0e0742c03edc2714f6449ee5ec` passed Offline CI and CodeQL across all configured language scans; intermediate documentation head `3133e36f82b86ed2fa1a0963115f6745ae752b6c` was also green.
