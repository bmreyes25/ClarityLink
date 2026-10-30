# Honda read-only runtime preflight collector

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

First inspect every command without ADB contact:

```sh
python3 tools/honda-readonly-preflight/collector.py --serial auto --dry-run
```

**Live use is currently unauthorized by repository policy.** The command below documents the existing exact-serial interface only; it is not permission to run it. Honda ADB requires qualified independent safety review and separate explicit owner authorization. This campaign has neither, so run only the offline dry-run and synthetic tests. The collector requires an exact serial for any future live use and rejects `--serial auto` before ADB initialization; it does not enumerate devices.

```sh
python3 tools/honda-readonly-preflight/collector.py --serial EXACT_PREAUTHORIZED_SERIAL --phase all \
  --vehicle-parked-confirmed --iphone-disconnected-confirmed
```

The existing broad profile captures baseline, connected, and post-disconnect states and is not the proposed campaign capture profile. The new human phase controller is not wired to a fixed campaign-specific operation manifest and does not enforce authorization. Neither it nor the broad profile is field-ready for this campaign. Do not use either for live collection unless the repository gate, qualified review, and separate owner approval are satisfied.

Single-operation flags are not supported. `--phase baseline` captures only the baseline. `--phase connected` collects baseline plus connected state. `--phase post-disconnect` collects all three sequential phases.

## Offline analysis

`parsers.py` contains pure parsers for maps, smaps, status signal masks, task listings, ARM Linux network tables, mapping gaps, exact load-bias arithmetic, FD-inode endpoint joins, and privacy-preserving log event summaries. `analyze.py` compares the saved phases and writes `analysis.json` inside the external capture directory. Synthetic tests do not contact ADB or represent live Honda data. Review and sanitize any derived prose before committing; the redactor is defense in depth, not a guarantee.

Analyze a finalized capture locally with:

```sh
python3 tools/honda-readonly-preflight/analyze.py "$HOME/CLARITY_RUNTIME_<timestamp>"
```
