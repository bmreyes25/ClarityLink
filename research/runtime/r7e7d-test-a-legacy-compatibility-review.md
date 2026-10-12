# R7E7D Test A legacy Android compatibility and package review

## Decision

The previous Test A attempt stopped before any push because the parent-directory parser required a size and absolute path that the Honda's Android 4.2.2 `ls -ld` did not return. R7E7C corrected that behavior. R7E7D compared remaining collector parsing with preserved A0-R/A0-WR output and found two additional concrete issues; both are corrected below. Test A remains unexecuted and unauthorized.

## Evidence reviewed

- A0-R metadata: `/data/local/tmp` was `drwxrwx--x`, `shell:shell`; actual captured output ended in `tmp` and contained date/time without a size.
- A0-WR parent metadata had the same legacy listing form.
- A0-WR transfer: exactly one file was pushed; `adb` wrote its success line to stderr, with a relative source path and `0 skipped`. The collector accounts for stdout and stderr and now executes the same relative source path declared in its manifest.
- A0-WR regular-file listing: a single toolbox line used `-r--r--r--`, owner/group `shell:shell`, decimal size, date/time, and the exact basename, with variable spacing. `_mode` accepts that grammar, requires a regular-file type and numeric size, and Test A compares every identity field against the frozen executable.
- A0-WR MD5: `/system/bin/md5` emitted one 32-hex digest, **two ASCII spaces**, and the exact remote path. The previous Test A parser required exactly one space. It now accepts exactly one or two ASCII spaces and still binds the digest to the exact path.
- A0-WR cleanup returned empty stdout/stderr; final absence output was one exact `<path>: No such file or directory` line. The strict Test A parser accepts that exact line, does not infer absence from host status or empty output, and now rejects unobserved prefixed variants.
- R7E7C live read-only observation: same mode and owner/group; exact sanitized output was `drwxrwx--x shell    shell             2026-10-11 09:20 tmp\r\n`.
- Previous Test A failure evidence: `push_attempted=false`, `diagnostic_started=false`, `process_state=NOT_STARTED`, cleanup `NOT_ATTEMPTED`, final absence `NOT_CHECKED`; only ADB version, device inventory, and parent metadata commands were recorded. The authorization attempt did not test executable transfer or launch.

Raw evidence remains ignored/private and unchanged. The R7E7C metadata file is mode 0600 in a mode-0700 directory. No raw target selector is reproduced here.

## Corrections and parser contracts

1. **Parent metadata:** one output line, exact directory mode `drwxrwx--x`, owner and group `shell`, final token exactly `tmp` or `/data/local/tmp`. Historical Android output may omit size and display the basename.
2. **Device inventory:** exact `List of devices attached` header; device records must be tab-delimited. Nonblank malformed rows fail closed rather than being silently ignored. The preserved Honda inventory format is covered.
3. **Remote regular-file metadata:** `_mode` accepts the observed toolbox spacing/date layout, requires a regular-file mode token, shell owner/group, numeric size, and a final basename. Execution compares mode `-r-xr-xr-x`, `shell:shell`, exactly 7904 bytes, and the exact frozen basename. Symlinks, directories, missing size, extra lines, and unrecognized mode characters fail closed.
4. **Push:** execution now uses the relative staging path in the manifest and runs from the repository root. One recognized success line must report that exact source, `1 file pushed`, `0 skipped`, and the exact byte count; stdout/stderr are both checked and combined output must contain exactly one line. The historical A0-WR transfer was in stderr and its relative source path is supported. The exact 7904-byte transfer has not yet been observed on Honda; its output line remains a future Test A gate, not a claimed result.
5. **MD5:** exactly one 32-hex digest, one or two ASCII spaces, and the exact remote path. Historical two-space formatting is covered. Wrong path/digest, empty, truncated, duplicate, or noisy output is rejected.
6. **Absence:** only the exact path-specific ENOENT line is accepted. Empty output, host return status alone, unrelated paths, prefixed/unrecognized errors, extra lines, stderr plus stdout, and existing file types fail closed.
7. **Diagnostic output and process checks:** source strings match the audited production diagnostic; the isolated API17 x86 runtime evidence covers both normal modes, child reaping, watchdog bounds, and exact process absence. The collector requires exactly one matching start/reap pair, exact bound PID absence sentinel and positive procfs controls before it accepts completion. No process is externally killed. Honda ARM execution remains unproven by emulator results.
8. **Timeout/cleanup:** child 2 s, parent 4 s, host target command 12 s, push 30 s; no retry or fallback. Any timeout stops without further target commands. Uncertain process state blocks cleanup. A single exact-path cleanup is allowed only under the frozen pre-execution or verified-exit conditions.

## Artifact and frozen identity

- Repository: `bmreyes25/ClarityLink`, PR #19
- R7E7D manifest version: `R7E7D-TEST-A-COMMAND-SET-4`
- Collector SHA-256: `7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129`
- Manifest SHA-256: `553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e`
- Artifact size: 7904 bytes
- Artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- Artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Canonical artifact is a regular ELF32 little-endian ARM EABI5 PIE; prior pinned API17 import audit found only `libdl.so` and `libc.so` and zero unknown imports.
- Current staging copy is regular, mode `0555`, 7904 bytes, and byte-identical to the canonical artifact. Artifact checker passed on the canonical mode-0755 build; staging hashes match.
- Exact remote destination: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`; expected remote mode `0555`; no target chmod.

## Verification and review status

- Focused collector tests after the compatibility corrections: 75 passed.
- Full repository runner: 1,057 passed, 15 skipped; self-locator and simulator checks passed; configured offline checks passed.
- Repository health: passed locally. Artifact audit: passed; canonical/staged bytes match, staging mode is `0555`, size and both hashes match.
- Collector dry-run: `DRY_RUN_NO_ADB`, zero ADB operations; sequence matches the manifest including relative push source.
- `git diff --check`: passed.
- Exact-head Offline CI and CodeQL remain required after committing and pushing this candidate.
- No R7E7D Honda command was run. No push or diagnostic launch occurred.
- Independent ECC reviewer was not available in the current capabilities. Manual ECC security-review, Python-testing, and safety-guided reviews were performed; no independent approval is claimed.

## Authorization status

R7E7B Test A authorization and R7E7C read-only authorization are both consumed. Neither applies to R7E7D. Test A remains **NOT_AUTHORIZED** and **NOT_EXECUTED**. A new user authorization must bind the final R7E7D repository HEAD, collector and manifest hashes, artifact hashes, exact path, one push, two diagnostic invocations, exact process checks, cleanup, and current operator observations. The next step after exact-head verification is to present that authorization request and stop.
