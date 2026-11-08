# CL-50 native dependency recovery

## Public checkpoint

This checkpoint updates the existing bounded ARM32 ELF probe with API 17 relocation and symbol-lookup logic based on the pinned [Android 4.2 Bionic linker](https://android.googlesource.com/platform/bionic/+/android-4.2_r1/linker/linker.cpp) and the [Arm ELF ABI](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst). The resolver follows requester and ordered direct-dependency lookup, applies `R_ARM_GLOB_DAT` per the pinned Bionic implementation and `R_ARM_ABS32` as `(S + A) | T`, and rejects unsupported or out-of-range definitions. This restricted model omits process-global preloaded objects and main-executable lookup scope. Hidden visibility fails closed.

Synthetic tests cover provider ordering, load bias, weak and strong unresolved symbols, duplicate definitions, architecture and section bounds, string-table identity, requester-defined `R_ARM_GLOB_DAT`, and relocation arithmetic. They do not model the Honda receiver or its dependencies.

## Private evidence boundary

Local archived-artifact and dependency checks were performed to investigate the prior loader blocker. Artifact paths, hashes, symbol details, dependency inventories, and binary-derived implementation findings remain in private local research storage and are intentionally omitted here. No Honda binary, raw capture, firmware, credential, or identifying device data is published by this report.

## Native execution status

No archived Honda receiver instruction was executed in this checkpoint. The existing Unicorn regression executes generated synthetic fixture instructions only. The current probe does not map and initialize the complete API 17 dependency environment, so synthetic relocation tests are not receiver execution evidence. The screen-registry hypothesis remains unmeasured; this checkpoint does not establish display advertisement, Type111 authorization, SETUP, or video delivery.

`safeForHonda() == false`. Honda Type111 integration remains unproven.

## Verification

Command: `/tmp/cl49-venv/bin/python -m pytest -q tests/honda/test_native_boundary_probe.py tests/negotiation/test_setup_contract.py tests/negotiation/test_type111_setup_contract.py tests/negotiation/test_external_alt_screen_provenance.py` — **142 passed, 21 subtests passed**. `python3 -m py_compile tools/honda_native_boundary_probe.py tests/honda/test_native_boundary_probe.py` passed, as did `git diff --check`. These are local synthetic/unit and regression checks only.
