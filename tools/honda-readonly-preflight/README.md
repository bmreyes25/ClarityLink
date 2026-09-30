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
- bounded `logcat -d -t 500` (no buffer clear).

The collector rejects all other operations and paths. There is no arbitrary shell string, upload, install, write, signal, service restart, `adb root`, ptrace, `/proc/PID/mem`, or custom-code execution path. Every command has a timeout and output ceiling. Results distinguish success, unavailable command, permission denial, transport failure, process identity change, timeout, output limit, and other command failure. A missing optional utility does not stop collection. Failed reads are saved with exit status and stderr so permission denials remain visible.

The required target fingerprint comes from `/proc/version` and exact `getprop` values for Android release/SDK, product device/board, and hardware. `uname` is captured only as an optional diagnostic because it is absent on some embedded Android builds.

## Denylist

Never add or run: `adb root`; `su`; `setprop`; `sysctl -w`; `mount`/remount; `stop`/`start`/`restart`; `kill`/`pkill`; `chmod`/`chown`; `touch`; `mkdir` on target; target redirection; `tee`; `cp`/`dd` to target; `install`/`push`; `ptrace`; `/proc/PID/mem`; signal/suspend operations; `mmap`/`mprotect` or cache operations on `jmcs`; listener creation; CAN/block-device writes; configuration changes; reboot/flash; log clearing; `/proc/PID/environ` reads.

## Use

First inspect every command without ADB contact:

```sh
python3 tools/honda-readonly-preflight/collector.py --serial auto --dry-run
```

After confirming the vehicle is parked, initial iPhone state is disconnected, and the existing ADB link is ready without escalation:

```sh
python3 tools/honda-readonly-preflight/collector.py --serial auto --phase all \
  --vehicle-parked-confirmed --iphone-disconnected-confirmed
```

`--serial auto` is only accepted for live collection if `adb devices -l` shows exactly one already-authorized device. If zero or more than one is listed, collection stops. Dry-run does not issue that host query. The tool captures baseline, pauses for normal stock CarPlay connect, captures connected state, asks whether ordinary stock Apple Maps is open for an optional lightweight snapshot, pauses for normal disconnect, and captures post-disconnect state. It does not control the car or phone. Stop immediately if either becomes unstable or any behavior differs from this documented read-only allowlist.

Single-operation flags are not supported. `--phase baseline` captures only the baseline. `--phase connected` collects baseline plus connected state. `--phase post-disconnect` collects all three sequential phases.

## Offline analysis

`parsers.py` contains pure parsers for maps, smaps, status signal masks, task listings, ARM Linux network tables, mapping gaps, and exact load-bias arithmetic. `analyze.py` compares the saved phases and writes `analysis.json` inside the external capture directory. Synthetic tests do not contact ADB or represent live Honda data. Review and sanitize any derived prose before committing; the redactor is defense in depth, not a guarantee.

Analyze a finalized capture locally with:

```sh
python3 tools/honda-readonly-preflight/analyze.py "$HOME/CLARITY_RUNTIME_<timestamp>"
```
