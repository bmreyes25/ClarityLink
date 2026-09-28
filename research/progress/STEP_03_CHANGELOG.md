# Step 3 — CarPlay-coexistence decoder probe preparation

**UTC:** 2026-09-28T08:55Z (final tests and staged review before push)

**Starting Git HEAD:** `d79719fb8ba161600d83bd3ca5b1ca43c81c33df`

**Branch / remote:** `main` / `origin` → private Clarity CarPlay cluster repository
**Scope:** Mac-only Step 3 preparation. No ADB/device command was executed; no car, pristine backup, or forensic dataset was accessed or changed.

## Changes

- Added an API-17 no-permission diagnostic package under `research/probes/carplay-coexistence/`, separate from and preserving the historical `decoder-capacity` app/results. The foreground service selects `OMX.Nvidia.h264.decode`, decodes 900 frames at 800×480/15 fps over 60 seconds to codec output buffers without a Surface, then drains EOS for up to five seconds. It records submitted/output PTS and monotonic arrival times, actual codec format, input buffer misses/errors, EOS, global available/total memory, and thermal status explicitly unavailable on Android API 17. A persistent notification offers STOP.
- Added a local-only build/sign/inspect script and API-17-v1-signing helper. The ignored APK is `research/probes/carplay-coexistence/build/carplay-coexistence-probe-signed.apk`, SHA-256 `59e7505e9b53fdb5bc6ee73ab10efcd9b377bc953a6e36dd9f6aaac42a5a7ea6`. The ignored `build/BUILD-RECEIPT.json` records source, manifest, fixture, and APK hashes. The historical 30-frame fixture is read from the prior package and not modified.
- Tightened `evaluate_trace.py`: output PTS must have been submitted earlier; trace timestamps must be monotonic; the scorer requires all planned inputs, duration, real NVIDIA codec identity, actual 800×480 format confirmations, no gap above 250 ms, and positively confirmed EOS. It reports missing output PTS and input deadline drops. Picture/audio remain unobserved by the scorer.
- Added `extract_logcat.py`, which extracts JSONL from saved tagged logcat and immediately applies the scorer; added host tests for package/permissions/signature receipt, constraints, event order, gaps, duration, format, EOS, codec identity, historical 28/30 result, and extraction.
- Added [DESIGN.md](../probes/carplay-coexistence/DESIGN.md) and the unapproved [ON_CAR_RUN_CARD.md](../probes/carplay-coexistence/ON_CAR_RUN_CARD.md). Updated status index and public research overview with the candidate and its limits.

## Verification performed

1. Before editing: `git status --short --branch` was clean at the starting HEAD; `git ls-remote origin refs/heads/main` matched `d79719f...`. Verified remote URL and repository exclusions. The pristine September 18 backup and original forensic dataset were not read or written by this task.
2. `python3 research/probes/carplay-coexistence/build_probe.py` — exit 0. ECJ emitted only expected deprecated-API warnings (`Notification` constructor and `setLatestEventInfo`, kept for Android 4.2 compatibility); Apktool packaged/decoded the APK; Google apksig verified the v1 signature for min API 17. Build receipt recorded exact hashes. Build script contains no ADB/device action.
3. Two consecutive `python3 research/probes/carplay-coexistence/build_probe.py` runs with the same local disposable key produced identical SHA-256 `59e7505e9b53fdb5bc6ee73ab10efcd9b377bc953a6e36dd9f6aaac42a5a7ea6` after deterministic ZIP timestamp normalization.
4. `python3 -m unittest discover -s research/probes/carplay-coexistence -p 'test_*.py' -v` — **19 passed, 0 failed**. The 28/30 historical trace is still 93.33% and fails; 29/30 satisfies only short-sample quality and cannot pass the full-duration gate; 855/900 over 60 seconds passes the synthetic decoder-only threshold. Malformed chronology, incomplete duration, long gaps, wrong format, false EOS and software codec tests fail as intended.
5. `python3 -m unittest discover -s research/probes/decoder-capacity -p 'test_*.py' -v` — **3 passed**, with historical APK hash unchanged at `162cae47046ad144946c3fc889297c9f6f62c037ece6c3e45b35d5229db3aac7`.
6. Candidate APK manifest decoded and checked: package `org.claritylab.carplaycoexistence`, one explicit service, no Activity, no requested permissions. Source-level checks confirm one 900-frame/15-fps workload, bounded five-second drain, NVIDIA selection, no Surface/audio/network/root/Honda interfaces, and explicit thermal unavailability. `python3 -m py_compile` on all new/changed Python files and `git diff --check` exited 0. Generated APK, receipt and signing key match `.gitignore` and remain local.

## Evidence, confidence, and limits

- **High confidence (build artifact only):** APK source compiled, packaged, signature-verified, ignored from Git, and its declared package/artifact hashes match local files; host scoring behavior is covered by 19 tests. Two consecutive same-machine builds with the same local signing key produced the same APK hash; a fresh checkout will use a new key and requires a new hash review.
- **Not established:** Android 4.2 service launch/lifecycle, actual runtime codec configuration with `surface=null`, real 60-second timing, frame output, EOS cleanup, CarPlay continuity, spoken audio continuity, or secondary iPhone display support. No emulator/device was used. A successful synthetic scorer test is not a car result.
- **Separate human condition:** CarPlay picture and voice must be observed before/during/after any later approved run. Decoder data cannot assert either.
- **Run state:** awaiting independent supervising Codex review of exact source/hash/run card and a separate user authorization for installing this new package. Do not execute the card yet. Step 4 remains pending and cannot advance until review and the one parked measurement.

## Rollback and next gate

No vehicle change occurred, so there is no vehicle rollback. To undo this repository change, revert the explicitly staged Step 3 source/docs/tests/status changes; preserve the ignored candidate APK/receipt until the review decision is recorded. The existing decoder-capacity APK and evidence remain untouched. Next: independently inspect the service's API-17 compatibility and bounded lifecycle, verify the exact APK and run card, then obtain separate user authorization before any install. Until that is done, status remains Step 3 in progress; Step 4 is not authorized by this offline preparation.

## Checkpoint publication

This changelog is part of the source-only checkpoint. The final commit ID and remote `main` verification are reported in the task handoff because a commit cannot contain its own ID.
