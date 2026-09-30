# Honda runtime address resolution — Step 40

No live /proc access is used. src/claritylink-honda/addressing.py parses synthetic maps fixtures and PT_LOAD metadata from the offline ELF.

For an executable PT_LOAD and a matching executable file mapping:
- align p_offset and p_vaddr down to the target page size;
- load_bias = mapping.start - aligned_p_vaddr;
- runtime_va = load_bias + (static_va & ~1);
- restore bit 0 for Thumb callable pointers when the static input carried the Thumb bit.

The resolver requires one executable mapping for the exact expected path and aligned segment file offset. It rejects missing/ambiguous/wrong-permission mappings, invalid segment coverage, negative bias, range overflow, and resolved addresses outside the mapping. This models PIE/ASLR without hard-coding a historical base.

The actual ELF is ET_DYN with two PT_LOAD segments. Its first executable PT_LOAD starts at file offset and VA zero; runtime maps still need exact segment/path correlation before any hypothetical address is used. Tests use synthetic mappings only.

## Step 40E status

The host collector and offline mapping parser are now available in `tools/honda-readonly-preflight/`. It checks the pinned ELF's `p_offset=0`, `p_vaddr=0` relation against the live executable mapping and then requires each computed runtime callsite to fall in an executable VMA. The corrected three-phase read-only capture completed and confirmed the same `jmcs` PID/start time throughout, but `/proc/<jmcs>/maps` and `smaps` were denied to the unprivileged shell. There is no live load bias or runtime callsite address; synthetic fixtures do not fill that gap. See [Step 40E report](../../step-reports/40e-readonly-runtime-preflight.md).
