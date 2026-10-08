# R7C4 Python and Android test environment recovery

The existing repository `.venv` was usable with Python 3.14.6 and already contained pytest 8.4.2, Unicorn 2.1.4, and cryptography 47.0.0. No package installation or dependency-file change was needed. Validation used `.venv/bin/python -m pytest --version` and `PYTHON=.venv/bin/python ./tools/run_tests.sh`.

Result: **902 passed, 14 skipped**; repository self-locator smoke tests and JavaScript simulator checks passed. `tools/check_repo_health.py` reported 705 Markdown files, 145 indexed reports, zero curated broken links, and zero forbidden tracked extensions. `git diff --check` passed.

API17 runtime used the existing isolated Android 4.2.2 x86 system image, Dalvik, and emulator-only `tools/run_r7c2_emulator.sh`. The final rebuilt test APK SHA-256 was `c3f9308ad912c34fe2507f633ca6c6ab064c560a42f05f6fd1c759f159bf02d5`; native x86 test library SHA-256 was `ab12c856598fb478505463773891d31ac550d84c6eed481e8521f4cd3154e64b`. Build tools were Android build-tools 35.0.0. The final harness passed, including separate Type110/Type111 socket deliveries and 100 lifecycle cycles. No physical device or Honda target was used.

The final R7C4 source revision was not re-audited for ARMv7 because this host inventory contains no NDK r23c (23.2.8568313) required by the pinned build script. The earlier R7C3 ARM build/import audit is historical and does not certify R7C4 source changes.
