# CL-51 — Bounded ARM32 Dependency Segment Mapping

## Question and method

**Question:** Can the existing isolated probe map bounded ELF32 ARM load segments using their program-header metadata while preserving fail-closed behavior?

**Method:** Extended the existing native-boundary probe with a bounded `PT_LOAD` planner and Unicorn mapper. The planner accepts a caller-supplied identity label and binds each mapping plan to that ELF source's bytes with SHA-256; the caller remains responsible for establishing artifact provenance. Symbol-resolver provider objects remain caller-supplied and must be fingerprinted independently. The planner validates program-header and file bounds, load bias, alignment, overlaps, and final page permissions. It maps file-backed bytes, initializes BSS, and applies later segment mappings to shared pages in program-header order, including replacement of earlier page contents. Separate object authority is not established by the identity label. The checked-in tests use public synthetic ELF fixtures. A local archive-backed exercise was also performed; its inventory, per-object results, addresses, and other binary-derived details remain in private research storage. That local result is reported by the author and is not independently reproducible from this public report.

## Result

The synthetic fixtures verify bounded segment placement, BSS zeroing, shared-page mappings and permissions, GNU_RELRO, invalid layouts, load-bias relocation, reserved runtime-range exclusion, and relocation permission gates. The planner accepts only readable PT_LOAD segments. PT_DYNAMIC input is capped at 65,536 entries (512 KiB) before reading or parsing. A zero-file-size unaligned segment maps the corresponding file-page prefix under the API 17 `mmap` length calculation, then initializes its BSS; read-only partial-page BSS is explicitly rejected by this mapper.

For file-backed segments sharing a page, later program headers replace that page's file-backed contents and permissions. Reversed-header fixtures verify this for two file-backed segments. A three-header fixture verifies BSS zeroing for the later segment's specified range. It does not establish Bionic behavior for every BSS-only shared-page layout. For a final file-backed page with no explicit BSS, a read-only segment retains source-file bytes beyond `p_filesz` through the mapped file-page boundary. A writable segment instead zeroes its partial-page tail to the boundary, even when `p_memsz == p_filesz`; a new fixture exercises that case. These behaviors follow the API 17 mapping path.

The loader deliberately implements a supported subset: it rejects writable-executable pages, requires page-offset congruence for PT_LOAD, and rejects GNU_RELRO pages outside mapped load memory. Relocations into other non-writable pages require explicit local textrel opt-in and an ELF textrel declaration. A writable PT_LOAD sharing a page with a later read-only segment can therefore require that gate for a relocation into the now-read-only page. A relocation into a writable PT_LOAD page covered by GNU_RELRO follows a separate path: the mapper temporarily enables RW/NX, applies the relocation, then restores the page read-only without requiring textrel, consistent with GNU_RELRO protection occurring after relocation; an existing fixture covers this. Bionic's `phdr_table_unprotect_segments` adds write permission to each non-writable load segment while retaining its original execute flag; this behavior appears in Android `android-4.2.2_r1` at lines 399–422. This isolated mapper instead uses temporary RW/NX pages and then restores the original page permissions. For a text relocation to a non-writable, non-RELRO page, targets must be 4-byte aligned and cannot cross a page boundary, so it uses at most two protection calls (enable and restore); relocations to already-writable pages need none. The existing 250,000-entry cap applies per ELF image and bounds its relocation count. GNU_RELRO protects every touched page after rounding, which can also make adjacent non-RELRO data on that page read-only; a fixture verifies this behavior.

Any `_load_image` failure marks that emulator object unusable, including a failure during planning before mapping. A segment-mapping failure rolls back newly mapped pages; injected cleanup failure verifies that the same emulator object is marked unusable when single-image rollback is incomplete. The later-image batch failure test verifies successful cleanup of earlier mapped images. Incomplete multi-image rollback, temporary textrel permission-restore failure, and post-mapping `_load_image` failure poisoning are implemented fail-closed paths but were not injected in this checkpoint. The mapper snapshots at most 128 MiB of source bytes before loading, reads segment content a page at a time, hashes source snapshots in 1 MiB chunks, and bounds each image's mapped-page buffers to 64 MiB. Root images remain below the root-image ceiling and outside reserved runtime ranges, including when optional runtime stubs are disabled.

Dependency layout planning assigns deterministic biases but does not itself map or relocate dependencies. Both planning and batch mapping reject more than 64 images or more than 256 MiB of aggregate source bytes; planning also accepts a caller-selected lower source cap. Each plan carries its per-image and dependency-batch mapping budgets, and mapping re-enforces those budgets. The batch mapper rejects out-of-range or overlapping plans. Synthetic tests map two planned dependencies into one emulator and verify their contents and non-overlap; fault-injection tests cover batch rollback and range enforcement.

The resource caps are separately enforced and their storage allowances are summed conservatively: about 832 MiB for 256 MiB of caller-held dependency inputs + 128 MiB for a snapshot copy + 128 MiB for parser storage + 64 MiB of page staging + 256 MiB of emulator mappings, plus up to 136 KiB for the optional 128 KiB stack and two one-page stubs, before Python and Unicorn metadata. The emulator mapping allowance includes root and dependency images; the root-image ceiling is a virtual-address limit, not additional mapped memory. This is a bound calculation, not a measured peak. Snapshot data can remain live during page staging, so the components are summed conservatively.

The author-reported local archive-backed mapping exercise did **not** execute any archived receiver instruction. Its private result does not establish dependency initialization, constructors, TLS, locks, Android services, session behavior, or receiver runtime equivalence. No downstream receiver behavior was assessed. This checkpoint is owner-authorized offline loader engineering only; it does not authorize vehicle access, receiver deployment, or physical display experiments.

Evidence available in this public checkpoint:

- `HOST_MODEL_ONLY` — behavior demonstrated by the synthetic ELF fixtures and Unicorn mapper.
- `AUTHOR_REPORTED_PRIVATE` — a local archive-backed mapping was performed, but its inputs and measurements are withheld and cannot be reproduced from this public checkpoint; no receiver instruction executed.
- `UNKNOWN` — publicly reproducible artifact-specific mapping details, runtime initialization requirements, and all downstream receiver behavior.

## Validation

Focused command:

```sh
/tmp/cl49-venv/bin/python -m pytest -q tests/honda/test_native_boundary_probe.py
```

Author-run result on the final tree: **142 passed**.

Regression command:

```sh
/tmp/cl49-venv/bin/python -m pytest -q tests/honda/test_native_boundary_probe.py tests/negotiation/test_setup_contract.py tests/negotiation/test_type111_setup_contract.py tests/negotiation/test_external_alt_screen_provenance.py
```

Author-run result on the final tree: **192 passed, 21 subtests passed**.

Additional checks:

```sh
/tmp/cl49-venv/bin/python -m py_compile tools/honda_native_boundary_probe.py tests/honda/test_native_boundary_probe.py
git diff --check
```

## Scope and safety

This change modifies the existing loader and its existing probe tests. Archived binaries remain outside Git and unmodified. The work does not access Honda hardware, execute receiver startup, or alter vehicle software. `safeForHonda() == false` remains in effect. Factory Type110 ownership and all Type111 protocol and display claims remain unproven.

References: [Android 4.2_r1 linker and text-relocation policy](https://android.googlesource.com/platform/bionic/+/android-4.2_r1/linker/linker.cpp), [Android 4.2.2_r1 `PT_LOAD` page mapping, file-backed length, and BSS handling](https://android.googlesource.com/platform/bionic/+/android-4.2.2_r1/linker/linker_phdr.c#L280-L347), [Android 4.2.2_r1 segment protection implementation](https://android.googlesource.com/platform/bionic/+/android-4.2.2_r1/linker/linker_phdr.c#L349-L422), [Android 4.2.2_r1 non-writable segment relocation permissions](https://android.googlesource.com/platform/bionic/+/android-4.2.2_r1/linker/linker_phdr.c#L399-L422), [Android 4.2.2_r1 GNU_RELRO page rounding and protection](https://android.googlesource.com/platform/bionic/+/android-4.2.2_r1/linker/linker_phdr.c#L438-L462), [Arm AAELF32, 2025Q4 release](https://github.com/ARM-software/abi-aa/blob/daa7a94ca55973736c0e434a67a6e4bbcd35d7fa/aaelf32/aaelf32.rst).

## Next experiment

Continue only with bounded offline validation of dependency closure and minimum initialization requirements. Segment mapping alone does not establish execution or platform behavior.
