# Tools guide

Tools are research utilities. Read the linked report/runbook and current authorization boundary before invoking any vehicle-facing tool.

| Tool | Category and boundary |
|---|---|
| [`run_tests.sh`](run_tests.sh) | Canonical offline test/smoke runner; safe for CI. |
| [`check_repo_health.py`](check_repo_health.py) | Deterministic local docs/index/proprietary-path checks; no network or Honda access. |
| [`build_cl_imp_03_apks.sh`](build_cl_imp_03_apks.sh), [`run_cl_imp_03_emulator.sh`](run_cl_imp_03_emulator.sh) | Builds the synthetic API17 APKs and runs them only on a private, explicitly identified emulator. The runner requires a marked, bounded build directory; it launches its ADB server as a tracked foreground child, refuses pre-existing AVD paths, and stores retained artifacts in a unique mode-0700 `build/cl-imp-03/runs/` directory. It does not contact Honda or an iPhone. |
| [`run_cl_r7_lab.sh`](run_cl_r7_lab.sh) | One-command CL-R7 API17 demonstration. It builds fresh APKs, runs actual Type110-first and Type111-first reattachment scenarios on separately owned emulators, retains logs/screenshots under a unique ignored `build/cl-r7-lab-*/` directory, and prints the required PASS marker only when pixel, decoded-Type111 warning withdrawal/recovery, reattachment, and cleanup gates pass in both orders. |
| [`run_cl_r4_acceptance.sh`](run_cl_r4_acceptance.sh) | Canonical, resumable CL-R4 API17 acceptance runner. It builds one exact candidate APK, records source/APK hashes and each fault case as PASS/FAIL/NOT_RUN/BLOCKED, preserves logs and a checkpoint under ignored `build/cl-r4-acceptance-*/`, and refuses overall PASS until every matrix case and priority interleaving has executed and passed. Resume with `tools/run_cl_r4_acceptance.sh --resume <evidence-directory>`; source changes invalidate the checkpoint. |
| [`api17_runner_guard.py`](api17_runner_guard.py), [`normalize_api17_png.py`](normalize_api17_png.py), [`verify_api17_pixel_content.swift`](verify_api17_pixel_content.swift), [`verify_api17_padded_crop_content.swift`](verify_api17_padded_crop_content.swift) | Local filesystem ownership checks and synthetic emulator image validation used by the API17 runner. Generated receipts and screenshots remain ignored under `/build/`; they are not publication inputs. |
| [`test_r7e1_target_diag_modes.py`](test_r7e1_target_diag_modes.py) | Host-only regression driver for the compiled target-diagnostic binary; no device access. |
| [`r4b_preview.py`](r4b_preview.py) | Host-only JSON snapshots from checked-in synthetic turn-card fixtures; no device, network, or Android backend. |
| `analyze_43t0d_capture.py`, `step43t0d_offline.py` | Offline analysis of a local, private host bundle; never collect data. |
| `step43t0d3_static_review.py`, `step43t0d3_netcfg_plan.py`, `elf_va_map.py` | Static artifact and plan review helpers. Input provenance and output privacy still apply. |
| `step43t0a_delta_dry_run.py`, `step43t0c_identity_delta_dry_run.py` | Dry-run procedure models; they have no ADB execution path. |
| `step43t0d0_collector.py` | **Vehicle-facing host collector.** Its existence is not authorization. Run only under its separately reviewed milestone and explicit operator gate; stop on any ambiguous target or failed prerequisite. |
| `honda-readonly-preflight/` | Earlier bounded collection/analyzer code; distinguish collection entrypoints from offline parsers and follow only current reviewed authorization. |
| `jmcs_integration/` | Static callsite planning/build utilities; does not itself authorize or perform Honda installation. |

The maintained current boundary is [`NEXT_ACTION.md`](../NEXT_ACTION.md). Install the documented test requirements and use the canonical runner only for offline verification.

The clean public test suite intentionally skips only the exact local-only collector modules listed by [`local_tool_gate.py`](../tests/tools/local_tool_gate.py); a test locks that set to the expected tool names. These tests require ignored local collectors or private binary fixtures and remain available in the full engineering checkout.

## CL-R7 API17 laboratory command

Run `tools/run_cl_r7_lab.sh` from a checkout with the documented API17 SDK and Java 17 toolchain installed. The default locations are `$HOME/Android/r7c2-sdk` and the pinned Java 17 path selected by the existing CL-IMP-03 scripts. To use another SDK or Java toolchain, set `CL_IMP_03_SDK_ROOT` or `JAVA_HOME`. The SDK must include API 17, build-tools 35.0.0, emulator, platform-tools, and cmdline-tools `avdmanager`. The host also needs Python 3, Swift, `shasum`, and `lsof` for existing runner validation and ownership checks.

The command creates a fresh marked build directory and never reuses or removes prior evidence. `CL_R7_BUILD_DIR` can select a fresh path directly under `build/`; it must not already exist. A successful command prints `CL_R7_END_TO_END_LAB_PASS` and leaves runtime logs, screenshots, and evidence in that directory. The scenarios use only synthetic fixtures on isolated API17 emulators; the warning test withdraws a decoded Type111 H.264 frame and checks that a fresh decoded frame renders after warning clearance.
## GitHub publication checkpoints

Every development task uses an explicit scope and verifies the live GitHub ref before claiming completion.

```sh
tools/publish_checkpoint.sh \
  --task CL-GH-LOCAL-01 \
  --branch docs/cl-gh-local-01-publication \
  --file AGENTS.md --file tools/publish_checkpoint.py \
  --message "docs: add verified local publication checkpoints" \
  --verification VERIFIED \
  --public-safe-reviewed \
  --verify-command "python3 -m unittest discover -s tests/tools -p test_publish_checkpoint.py"
```

Repeat `--file` for every intended path. The publisher never stages the whole repository. It requires a public-safety review attestation, rejects ignored paths (including tracked files excluded by ignore rules), private vehicle/Honda research roots, restricted path classes, binary artifacts, credential-like content, pre-staged unrelated files, and direct `main` publication. Shared status files require the designated maintenance-owner flag. A verified checkpoint needs a successful verification command; its executable and arguments are parsed and run without a shell. Existing PR checks require an open PR targeting `main` whose branch and head SHA match the published checkpoint. A public-safe `WIP_UNVERIFIED` checkpoint also needs notes of incomplete work and known failures, keeps its branch, and skips creating a new PR; do not publish restricted or uncertain material to this public repository.

Run `python3 tools/verify_remote_publication.py` to compare local `HEAD` with the live remote branch. Run `python3 tools/check_source_discovery.py` to find source-like files hidden by ignore rules; classify each result manually.

`.codex/hooks.json` configures bounded, read-only `SessionStart` and `Stop` audits. Codex Desktop must load the actual repository root as the project and the user must review/trust these project hooks before they run. The Stop hook can request one continuation but never commits or pushes. Hooks do not protect against crashes or power loss.
