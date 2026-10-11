# R7E5C A0-WR authorization packet — prepared, not authorized

## Decision

`R7E_A0WR_LEGACY_MODE_PACKAGE_READY`

`READY_FOR_EXPLICIT_USER_A0WR_AUTHORIZATION`

This packet is a request for a **new, separate authorization**. The previous A0-W authorization does not apply. A0-WR has not run. Test A remains `NOT_AUTHORIZED`.

## Frozen package binding

- Collector: `tools/r7e5c_a0wr_collector.py`
- Collector SHA-256: `3ef1808354a78e183a1d4803d10fb0409aa61df2ba0e9d27e3bd97cbf77f3adc`
- Manifest version: `R7E5C-A0WR-COMMAND-SET-1`
- Manifest: `research/runtime/r7e5c-a0wr-plan-manifest.json`
- Manifest SHA-256: `198076c2687c7c1178dd710af509eda3900e6687b819b734a78b592289215b3d`
- Marker: `build/r7e5c/a0wr/claritylink-a0wr-marker.txt`
- Marker bytes: `ClarityLink A0-WR inert transfer marker\nR7E5C\nNO EXECUTION\n`
- Marker size: `59 bytes`
- Host mode: `0444`
- Expected remote mode: `0444`, computed by the reviewed `legacy_adb_v1_remote_mode` model
- Marker SHA-256: `3f84d1ff7d301409d5bebfba84b242ff8f0df20e2928a9fdc91687b40c573b9d`
- Marker MD5: `6cac328b32dad06f736d6a7ab78a20c8`
- Exact remote path: `/data/local/tmp/claritylink_a0wr_r7e5c_5d73b2c42a7e19f0.probe`

The marker is regular, readable, non-writable, and non-executable. Its bytes are inert text. Exact deletion relies on parent-directory permissions.

## Local staging preparation

The build directory is ignored. Before any separately authorized run, materialize these exact frozen bytes at the marker path and set mode `0444`; the collector rejects missing, symlinked, changed, or differently permissioned marker files. The current ignored local staging file has been prepared for package verification.

## Proposed A0-WR scope

If separately authorized, the collector will perform only its eight frozen commands: `adb devices`; destination directory metadata read; exact-path absence read; one `adb push`; exact marker metadata read; `/system/bin/md5` read; exact `/system/bin/rm` of the marker; exact absence read. An exclusive ADB window is mandatory because legacy sync unlinks the destination before sending. It has zero retries, zero fallbacks, no wildcard, no alternate path, no target `chmod`, and no executable transfer or launch.

After any push attempt, the collector records metadata and attempts MD5, then performs the exact cleanup and absence check. Acceptance requires exact regular-file metadata, `shell:shell`, expected size and `0444`, non-executable status, exact MD5, successful cleanup, verified absence, and `STOCK_STATE_UNCHANGED`.

## Explicit exclusions

This packet does not authorize A0-WR by itself. It does not authorize Test A, diagnostic transfer or execution, `chmod`, display activity, USB/iAP2, MFi, CarPlay, root, or any other vehicle change. Test A requires a separate future evidence review and separate explicit authorization. Its planned staging policy is an ignored copy with canonical artifact bytes/hash unchanged and mode `0555`; this is planning only.
