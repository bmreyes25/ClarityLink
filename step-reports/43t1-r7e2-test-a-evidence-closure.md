# 43T1 R7E2 — Test A evidence closure and A0 preparation

**Decision:** `R7E_TEST_A0_READONLY_PREFLIGHT_READY`  
**Starting HEAD:** `858ab1e91769b3023226758b9ba609b72af02fb0`  
**Branch:** `architecture/r7e-parked-car-compatibility-preparation`  
**PR:** #19, remains open  
**Scope:** preparation only; no Honda command executed and no Honda write.

## Evidence review

ECC evidence review exhausted the preserved R7E Honda material relevant to target path, shell, mounts, SELinux, and power state, including the 40E unprivileged captures, 40E4 privilege review, 41D static UDA evidence, 41F historical mount evidence, and 43T0-D4 read-only attempt. The UDA image records `/data/local/tmp` as `/local/tmp`, mode `0771`, owner/group `shell:shell` (2000:2000). This is HONDA_STATIC, not current runtime proof. A historical `/proc/mounts` record showed `/data` `rw,nosuid,nodev` without `noexec`; it is historical runtime evidence, not a current guarantee. `/sys/fs/selinux/enforce` was absent and historical `getenforce` was unavailable; active state/domain remain unknown.

40E/43T0 evidence records ordinary ADB shell UID 2000 and successful legacy `adb shell` identity/property/proc reads. It does not prove path write/delete or executable sufficiency. 43T0-D4 records stationary/parked normally powered operation for a prior read-only observation but gives no named ACC/ON/READY mode; its later `adb devices` returned zero targets and no target operation ran. No current Honda target observation is inferred.

Official Honda 2018 owner's manual distinguishes Accessory/ON and READY-to-drive, but does not establish ADB reachability or the minimum safe mode for Test A: [Honda owner's manual](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2018%2FClarity+Plug-In+Hybrid%2F2018_Clarity_PHEV_Push_Button_Start.pdf).

## ECC decisions

- `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT`: successful mapping/launch is what Test A exists to measure. Requiring prior proof of successful execution is circular. A0-R screens known mount/policy blockers; absence of a known blocker does not promise success.
- `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`: no need to prove the least-powered theoretical mode. A future separately approved test must use an exact operator-observed state, stationary/parked car, fully booted center display, normal cluster/no warnings, unique verified target, and operator able to stop. Actual mode remains A0-R evidence.
- Ordinary shell is preferred; root/SuperSU/HondaHack are not introduced. A0-R UID mismatch/elevation is a stop condition.
- A0-R Tier 1 read-only plan is ready for separate authorization. A0-W is Tier 2 and `BLOCKED_BY_A0_R_RESULT`; it may only test one exact inert marker create/read/delete, never execute. Test A is Tier 2 execution and remains `BLOCKED_BY_A0` / `NOT_AUTHORIZED`.
- Exact shell command availability remains partial: `id`, selected `getprop`, `cat`, legacy `adb shell`, and plain `ls` are evidenced; `ls -ld` exact flags, `chmod`, `rm`, `kill`, target `sha256sum` are not established; `ps` evidence is incomplete. Test A rollback is not ready until exact commands and process disposition are supported.

The A0-R plan uses an explicit `adb -s "$TARGET"` on every target command, where TARGET is validated locally and never committed. Zero or multiple targets means STOP. A0-R commands perform reads only; expected target writes: **NONE**. No shell redirect, push, file creation, chmod, execution, display, service, process, USB/iAP2, MFi or CarPlay action is included.

## Readiness matrix

- Test A: `BLOCKED_BY_A0`, `NOT_AUTHORIZED`; artifact unchanged: `claritylink-target-diag`, SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`.
- A0-R: ready for separate authorization, Tier 1; no Honda commands executed.
- A0-W: `BLOCKED_BY_A0_R_RESULT`, Tier 2, separate future authorization.
- B–D remain blocked by prior test/Honda display evidence; E `BLOCKED_BY_EVIDENCE`; F `PLAN_PARTIAL`; G `PERFORMANCE_UNRESOLVED`; H `AUTHORITY_REQUIRED`.

## Repository verification

Repository health passed (782 Markdown files; no broken curated links or forbidden extensions). Canonical suite passed: 902 passed, 15 skipped; self-locator 3/3; all configured simulator checks passed; `git diff --check` passed. Exact-head Offline CI and CodeQL must pass after push. PR #19 remains open; merging is not requested by this preparation result.

**Honda actions:** NONE. **Honda writes:** NONE. **Test A/A0 execution:** NONE.
