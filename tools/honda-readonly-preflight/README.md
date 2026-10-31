# Honda read-only runtime preflight and fixed campaign runner

This is a host-side Python collector for Step 40E. It stores target command output on the Mac under `~/CLARITY_RUNTIME_<timestamp>/`, with mode-restricted files, a per-command manifest, and SHA-256 records. Raw output can include sensitive platform, socket, log, and display details: never copy the capture tree into Git.

## Legacy collector operation inventory (not the C-P live allowlist)

The legacy collector's offline-analysis surface exposes only these fixed operations. This inventory does not authorize live execution: C-P live collection is limited to the exact ordered operations, arguments, timeouts and output ceilings in `campaign_profile.json`, enforced by `campaign_runner.py`.

- host-selected existing ADB serial + legacy `adb shell` service (compatible with API-17 adbd; `exec-out` is not used);
- target `id`, optional `uname -a`, `ps`, `service list`, fixed `sha256sum /system/bin/jmcs`, fixed `ls -l /system/bin/jmcs`;
- `cat` of enumerated `/proc`, `/sys` CPU-topology/cache, process, task, and network paths;
- `ls` of fixed proc/sys directories and validated numeric PID task/FD directories (the output parser accepts API-17 toolbox's default whitespace columns);
- symlink target inspection via fixed `ls -l` on validated process exe/cwd/root and numeric FD paths (the collector does not assume a standalone `readlink` applet exists);
- `getprop` for an enumerated build/device property set;
- read-only `dumpsys display`, `SurfaceFlinger`, and `window`;
- bounded `logcat -d -t 500` (no buffer clear); its exact API17 support on this head unit is unverified, so unsupported or unexpected output stops the session without substitution. New captures summarize event markers in memory and persist only counts, timestamp bounds, result status, and a SHA-256 digest. Source log lines and stderr are not written to capture files.

The collector rejects all other operations and paths. There is no arbitrary shell string, upload, install, write, signal, service restart, `adb root`, ptrace, `/proc/PID/mem`, or custom-code execution path. The campaign controller additionally enforces each phase's exact ordered operation, arguments, timeout, and byte limit from the pinned manifest before execution. Every command has a timeout and output ceiling. API-17 legacy `adb shell` may not reliably report remote exit status; required outputs are checked for known shell errors, empty dumpsys results, and malformed nonempty logcat output. These checks cannot recognize every target-specific error message, so actual API-17 command behavior remains unverified. No status field alone proves a remote command succeeded.

The required target fingerprint comes from `/proc/version` and exact `getprop` values for Android release/SDK, product device/board, and hardware. `uname` is captured only as an optional diagnostic because it is absent on some embedded Android builds.

## Denylist

Never add or run: `adb root`; `su`; `setprop`; `sysctl -w`; `mount`/remount; `stop`/`start`/`restart`; `kill`/`pkill`; `chmod`/`chown`; `touch`; `mkdir` on target; target redirection; `tee`; `cp`/`dd` to target; `install`/`push`; `ptrace`; `/proc/PID/mem`; signal/suspend operations; `mmap`/`mprotect` or cache operations on `jmcs`; listener creation; CAN/block-device writes; configuration changes; reboot/flash; log clearing; `/proc/PID/environ` reads.

## Use

The campaign-specific controller is the only live entry point that enforces the pinned operation profile, private review/authorization records, phase attestations, and exact serial. Its offline plan is:

```sh
python3 tools/honda-readonly-preflight/campaign_runner.py dry-run
```

The dry-run verifies the canonical profile and source lock, and prints all ordered phases, fixed argv, expected output, bounds, failure behavior, and private artifact destinations. It does not locate ADB, enumerate devices, create files, or contact a vehicle. `campaign_profile.sha256` pins the exact profile, which itself binds the source-hash lock.

`campaign_runner.py run` requires adopted `C-P-MA-OWNER-ASSUMED-RISK` policy and an owner-only private record binding the exact commit, source/profile hashes, manifest, phases, serial and owner risk acceptance. Codex and Claude exact-source reports are required. ECC may be recorded as `UNAVAILABLE` only when unavailable, with a truthful reason and `no_completed_review_withheld: true`; the owner attests that no completed or received ECC report is withheld; any such report must be included and pass hash/findings validation. This is an owner attestation, not an independently enforceable control: the validator cannot inspect external services or independently prove availability or truthfulness. No saved record grants a run: the runner requests a fresh nonce-bound owner confirmation for each invocation. During the bounded final challenge, SIGINT, SIGTERM and SIGHUP are held only until the prompt resolves and exact YES atomically consumes the unique authorization ID in an owner-only host ledger. Pending signals are delivered once the marker is durable, before revalidation, capture creation or ADB; the same ID is rejected later. A non-YES response or prompt timeout does not consume the ID. Termination signals received during the prompt are deferred until it resolves; exact YES consumes the ID before a pending signal is delivered. The ledger is anchored to the current UID’s passwd home rather than mutable `HOME`. It prevents ordinary accidental replay, not deliberate modification or deletion by the local owner. If ledger persistence fails, execution stops before ADB. If no marker was created, the ID remains technically unused; a no-retry/new-owner-decision requirement applies until the failure is resolved, but the validator cannot enforce a new record when no marker exists. Interruption during the final owner prompt stops before capture creation, so no capture directory or failure card is created. SIGTERM/SIGHUP during collection or normal completion use the failure-finalization path; SIGKILL and power loss are not guaranteed to produce a failure card. AI review is not human safety certification. Root, HondaHack, instrumentation and deployment remain outside this C-P exception.

The fixed eight phases contain only read-only host diagnostics around owner-guided normal CarPlay connect/disconnect and factory Navigation select/deselect/reselect transitions. The manifest has 135 command entries (sum of timeout ceilings 2,425 seconds; output ceilings 158,400,512 bytes). These are upper bounds, not measured load or proof of safety. Diagnostics may affect head-unit resources, timing or connectivity, and raw evidence can contain personal data. The required state is ON mode, brake pedal not pressed, READY absent; Honda's 2018 manual describes automatic engine start/stop during vehicle operation and defines READY as indicating the vehicle is ready to drive. Whether the head unit and ADB work in ON is unknown. If not, stop without changing to READY or escalating privilege. Require stationary Park, parking brake, owner presence and outdoor operation; the live controller rechecks Park, READY, warning state, and visible display/cluster condition at each phase, plus parking-brake and brake-pedal state at baseline. A long ON-mode session may drain the 12 V battery; its condition and head-unit response are not measured. Stop on unexpected behavior; no retry or scope expansion. ADB loss during a transition means stop and restore stock operation using ordinary controls only; do not retry. There is no root, `adb root`, `su`, installation, process attachment/modification, firmware/CAN/display change, warning interference, driving test or deployment. HondaHack remains separately gated. The runner fetches `origin/main` using fixed local Git arguments and requires a clean checkout at current `main`, an adopted policy commit on current `origin/main`, and rechecks current profile/source/manifest hashes against the review records. A passing validator does not itself authorize a vehicle session.

The runner closes stdin for every ADB client and attempts to stop the host client on command timeout, output limit, or KeyboardInterrupt; it issues no target-side cleanup. Whether an API-17 remote child exits when the host client is killed is unverified, so it may outlive the client. SIGTERM, SIGHUP and SIGKILL are not all guaranteed to produce a failure card. If interrupted or disconnected, do not retry; use ordinary controls to restore stock operation if needed, preserve the partial private capture, and run offline recovery only. A long ON-mode session may drain the 12 V battery. The shared host ADB server may remain running; stopping it could disrupt other host sessions and is outside this campaign's scope. Final restoration confirms visible factory behavior and owner observation; it cannot prove no remote child or shared ADB server remains active.

The legacy broad `collector.py` profile is offline-analysis infrastructure only; its live CLI now refuses execution so it cannot bypass the campaign gate. Use `campaign_runner.py recover <private-capture-directory>` only for offline integrity review of an interrupted host capture. Recovery never resumes collection or contacts a vehicle.

The legacy collector's live CLI is disabled. Its historical phase-selection options do not define a live C-P procedure; use only the fixed campaign controller and full pinned phase sequence.

## Offline analysis

`parsers.py` contains pure parsers for maps, smaps, status signal masks, task listings, ARM Linux network tables, mapping gaps, exact load-bias arithmetic, FD-inode endpoint joins, and privacy-preserving log event summaries. `analyze.py` compares the saved phases and writes `analysis.json` inside the external capture directory. Synthetic tests do not contact ADB or represent live Honda data. Review and sanitize any derived prose before committing; the redactor is defense in depth, not a guarantee.

Analyze a finalized capture locally with:

```sh
python3 tools/honda-readonly-preflight/analyze.py "$HOME/CLARITY_RUNTIME_<timestamp>"
```
