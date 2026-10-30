# Honda read-only runtime preflight and fixed campaign runner

This is a host-side Python collector for Step 40E. It stores target command output on the Mac under `~/CLARITY_RUNTIME_<timestamp>/`, with mode-restricted files, a per-command manifest, and SHA-256 records. Raw output can include sensitive platform, socket, log, and display details: never copy the capture tree into Git.

## Pre-capture allowlist

The collector exposes only fixed operations:

- host-selected existing ADB serial + legacy `adb shell` service (compatible with API-17 adbd; `exec-out` is not used);
- target `id`, optional `uname -a`, `ps`, `service list`, fixed `sha256sum /system/bin/jmcs`, fixed `ls -l /system/bin/jmcs`;
- `cat` of enumerated `/proc`, `/sys` CPU-topology/cache, process, task, and network paths;
- `ls` of fixed proc/sys directories and validated numeric PID task/FD directories (the output parser accepts API-17 toolbox's default whitespace columns);
- symlink target inspection via fixed `ls -l` on validated process exe/cwd/root and numeric FD paths (the collector does not assume a standalone `readlink` applet exists);
- `getprop` for an enumerated build/device property set;
- read-only `dumpsys display`, `SurfaceFlinger`, and `window`;
- bounded `logcat -d -t 500` (no buffer clear); new captures summarize event markers in memory and persist only counts, timestamp bounds, result status, and a SHA-256 digest. Source log lines and stderr are not written to capture files.

The collector rejects all other operations and paths. There is no arbitrary shell string, upload, install, write, signal, service restart, `adb root`, ptrace, `/proc/PID/mem`, or custom-code execution path. Every command has a timeout and output ceiling. Results distinguish success, unavailable command, permission denial, transport failure, process identity change, timeout, output limit, and other command failure. A missing optional utility does not stop collection. Failed reads are saved with exit status and stderr so permission denials remain visible.

The required target fingerprint comes from `/proc/version` and exact `getprop` values for Android release/SDK, product device/board, and hardware. `uname` is captured only as an optional diagnostic because it is absent on some embedded Android builds.

## Denylist

Never add or run: `adb root`; `su`; `setprop`; `sysctl -w`; `mount`/remount; `stop`/`start`/`restart`; `kill`/`pkill`; `chmod`/`chown`; `touch`; `mkdir` on target; target redirection; `tee`; `cp`/`dd` to target; `install`/`push`; `ptrace`; `/proc/PID/mem`; signal/suspend operations; `mmap`/`mprotect` or cache operations on `jmcs`; listener creation; CAN/block-device writes; configuration changes; reboot/flash; log clearing; `/proc/PID/environ` reads.

## Use

The campaign-specific controller is the only live entry point that enforces the pinned operation profile, private review/authorization records, phase attestations, and exact serial. Its offline plan is:

```sh
python3 tools/honda-readonly-preflight/campaign_runner.py dry-run
```

The dry-run verifies the canonical profile and source lock, and prints all ordered phases, fixed argv, expected output, bounds, failure behavior, and private artifact destinations. It does not locate ADB, enumerate devices, create files, or contact a vehicle. `campaign_profile.sha256` pins the exact profile, which itself binds the source-hash lock.

`campaign_runner.py run` is only eligible under the prospective `C-P-MA-OWNER-ASSUMED-RISK` category after that policy is adopted on protected `main`. It requires a mode-0600 private owner authorization record outside the repository. The record binds exact source/profile hashes, command-manifest digest, all eight phase IDs, exact reviewed commit, policy adoption SHA, exact serial, owner risk acceptance and separate owner authorization. It also binds three separately produced Codex, Claude and ECC AI engineering reports. These are not independent human safety certifications; the validator checks scope and file hashes but cannot authenticate agent identity, independence, competence or safety. Each report must record a nonblank tool/model version or explicitly unavailable value, findings by severity, nonempty test and assumption entries (use `none` when appropriate), proposed changes and GO/CHANGES REQUIRED/NO-GO recommendation. The profile pins `AGENTS.md`, `docs/safety/vehicle-testing.md`, `docs/security/vehicle-safety-gates.md`, and `docs/security/single-owner-cp-review-policy.md` alongside the fixed command manifest. The exact reviewed profile and source hashes are therefore invalidated by changes to any pinned content.

The fixed eight phases contain only read-only host diagnostics around owner-guided normal CarPlay connect/disconnect and factory Navigation select/deselect/reselect transitions. The manifest has 135 command entries (sum of timeout ceilings 2,425 seconds; output ceilings 158,400,512 bytes). These are upper bounds, not measured load or proof of safety. Diagnostics may affect head-unit resources, timing or connectivity, and raw evidence can contain personal data. The required state is ON mode, brake pedal not pressed, READY absent; Honda's 2018 manual describes automatic engine start/stop during vehicle operation and defines READY as indicating the vehicle is ready to drive. Whether the head unit and ADB work in ON is unknown. If not, stop without changing to READY or escalating privilege. Require stationary Park, parking brake, owner presence and outdoor operation. Stop on unexpected behavior; no retry or scope expansion. There is no root, `adb root`, `su`, installation, process attachment/modification, firmware/CAN/display change, warning interference, driving test or deployment. HondaHack remains separately gated. The runner fetches `origin/main` using fixed local Git arguments and requires a clean checkout at current `main`, an adopted policy commit on current `origin/main`, and rechecks current profile/source/manifest hashes against the review records. A passing validator does not itself authorize a vehicle session.

The runner terminates its ADB client on interruption and does not issue target-side cleanup. The shared host ADB server may remain running; stopping it could disrupt other host sessions and is outside this campaign's scope. Final restoration attests that no campaign command remains active, not that the shared host server has stopped.

The legacy broad `collector.py` profile is offline-analysis infrastructure only; its live CLI now refuses execution so it cannot bypass the campaign gate. Use `campaign_runner.py recover <private-capture-directory>` only for offline integrity review of an interrupted host capture. Recovery never resumes collection or contacts a vehicle.

Single-operation flags are not supported. `--phase baseline` captures only the baseline. `--phase connected` collects baseline plus connected state. `--phase post-disconnect` collects all three sequential phases.

## Offline analysis

`parsers.py` contains pure parsers for maps, smaps, status signal masks, task listings, ARM Linux network tables, mapping gaps, exact load-bias arithmetic, FD-inode endpoint joins, and privacy-preserving log event summaries. `analyze.py` compares the saved phases and writes `analysis.json` inside the external capture directory. Synthetic tests do not contact ADB or represent live Honda data. Review and sanitize any derived prose before committing; the redactor is defense in depth, not a guarantee.

Analyze a finalized capture locally with:

```sh
python3 tools/honda-readonly-preflight/analyze.py "$HOME/CLARITY_RUNTIME_<timestamp>"
```
