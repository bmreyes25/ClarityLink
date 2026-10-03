# Tools guide

Tools are research utilities. Read the linked report/runbook and current authorization boundary before invoking any vehicle-facing tool.

| Tool | Category and boundary |
|---|---|
| [`run_tests.sh`](run_tests.sh) | Canonical offline test/smoke runner; safe for CI. |
| [`check_repo_health.py`](check_repo_health.py) | Deterministic local docs/index/proprietary-path checks; no network or Honda access. |
| `analyze_43t0d_capture.py`, `step43t0d_offline.py` | Offline analysis of a local, private host bundle; never collect data. |
| `step43t0d3_static_review.py`, `step43t0d3_netcfg_plan.py`, `elf_va_map.py` | Static artifact and plan review helpers. Input provenance and output privacy still apply. |
| `step43t0a_delta_dry_run.py`, `step43t0c_identity_delta_dry_run.py` | Dry-run procedure models; they have no ADB execution path. |
| `step43t0d0_collector.py` | **Vehicle-facing host collector.** Its existence is not authorization. Run only under its separately reviewed milestone and explicit operator gate; stop on any ambiguous target or failed prerequisite. |
| `honda-readonly-preflight/` | Earlier bounded collection/analyzer code; distinguish collection entrypoints from offline parsers and follow only current reviewed authorization. |
| `jmcs_integration/` | Static callsite planning/build utilities; does not itself authorize or perform Honda installation. |

The maintained current boundary is [`NEXT_ACTION.md`](../NEXT_ACTION.md). Install the documented test requirements and use the canonical runner only for offline verification.
