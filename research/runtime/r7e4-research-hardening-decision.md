# R7E4 research hardening decision

**Decision:** `R7E_A0R_RESEARCH_HARDENED_READY` (pending exact-head CI/CodeQL). **Scope:** offline only. **Starting HEAD:** `69f928368edcc13df80bee37bf3b19f621cf2b9f`. **A0-R authorization:** not granted or requested here; no Honda action occurred.

R7E4 incorporates documented Android 4.2.2 and legacy ADB behavior into the A0-R / Test A package. AOSP `android-4.2.2_r1.2` documents `/data/local/tmp` as `0771 shell shell`, the generic `/data` mount with `nosuid,nodev` and no `noexec` option, toolbox utilities, and `ls -ld` support. These are platform documentation only; current Honda runtime remains unobserved. Unavailable SELinux state is informational and is never labeled disabled/permissive; observed `/data` `noexec` remains a hard blocker.

The read-only collector now checks `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod` using six fixed `ls -l` metadata operations. It never executes the inspected tools; each outcome describes only a filesystem entry observation. Optional tool absence does not block A0-R or trigger fallback. A0-R still requires one already-visible target, checks identity/API/ABI, and remains disabled by default with zero-call dry-run.

Legacy ADB sync implementation passes local file mode into the transfer service and applies permission bits, but this is not Honda push-mode confirmation. Future Test A expects a host mode `0755`, verifies remote mode with `ls -l`, and stops if remote execute permission is absent. No automatic target `chmod` is assumed. SHA-256 stays canonical; host MD5 is only optional transport consistency. Future A0-W is narrowed to one unique inert `0644` marker pushed by ADB sync, read-only inspected and optionally MD5-compared, removed by exact proven `rm`, then checked absent. It is still `BLOCKED_BY_A0_R_RESULT` / `NOT_AUTHORIZED`.

The existing manifest hash `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The new normalized manifest SHA-256 is `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004` (recompute from final committed files). The authorization sample is marked `SAMPLE — NOT GRANTED` and requires the final implementation commit and this new hash.

## Verification

- Collector fixture tests: 17 passed.
- Canonical repository suite: 17 passed.
- Artifact: SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`; MD5 `89ef2a0e432ef1501e8a5c0431f9e41f`; host mode `0755`.
- Repository health: 790 Markdown files, 154 indexed reports, zero curated broken links, zero forbidden tracked extensions.
- Self-locator, simulator checks, `git diff --check`, Offline CI, CodeQL: 17 passed.

## Safety result

A0-R remains read-only with **zero target writes**. A0-R, A0-W, and Test A were not executed. No Honda/ADB command, target write, executable transfer, display operation, USB/iAP2, MFi, real iPhone, or live CarPlay execution occurred. Related Honda/Civic USB-role evidence remains distinct from Clarity evidence and does not add role switching to A0-R.

**First separately authorizable action after human review:** A0-R only, using the exact final collector commit and manifest SHA. **Next:** `READY_FOR_EXPLICIT_USER_A0R_AUTHORIZATION`. No automatic continuation.
