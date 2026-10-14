# R7E4 A0-R host fixture results

**Scope:** offline synthetic fixtures only. The A0-R collector was not run against Honda and no real ADB executable or Honda command was invoked.

| Case | Result |
|---|---|
| Default invocation and dry-run | Default refusal; dry-run makes zero ADB calls or target discovery |
| Target selection | One target pinned; zero, multiple, offline, unauthorized, malformed states stop before shell |
| Identity/platform | Elevated UID, wrong API and wrong ABI stop before later observations |
| Destination/mount | `ls -ld` failure stops without fallback; `/data` noexec is a hard blocker |
| SELinux | enforcing/permissive values are recorded as `1`/`0`; unavailable/invalid is informational `SELINUX_STATE_UNAVAILABLE`; no `getenforce` fallback |
| Tool metadata | toolbox/rm/ps/kill/md5/chmod present/absent states use only fixed `ls -l` metadata argv; absence is informational and no inspected utility executes |
| Timeout/failure | Timeout and required command failure stop with no retry |
| No-write / no-fallback | normalized manifest has only fixed reads; no push/install/delete/chmod/kill/touch/mkdir/dd/setprop/mount/remount/su/reboot, shell `-c`, target mutation, or fallback |
| Redaction / auto-chain | selector is redacted outside private evidence; A0-W and Test A remain separate and cannot auto-run |
| Artifact | canonical SHA-256 matches; MD5 recorded only for transport comparison; host mode exactly `0755` |

The focused collector module passes **17 tests**. The canonical repository suite passed **919 tests, 15 skipped**. Self-locator passed **3 tests**; all configured simulator checks and the Type111 failure twin passed; `git diff --check` passed. Repository health: 790 Markdown files, 154 indexed milestone/support reports, zero curated broken links, zero forbidden tracked extensions. The local artifact checker is `tools/check_r7e1_target_diag_artifact.py`. Manifest SHA-256 is recorded in the authorization packet and R7E4 decision. No A0-R/A0-W/Test A run, Honda command, target write, USB-role change, executable transfer, display activity, iAP2/MFi, or CarPlay operation occurred.
