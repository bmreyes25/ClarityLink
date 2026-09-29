# Honda runtime address resolution — Step 40

No live /proc access is used. src/claritylink-honda/addressing.py parses synthetic maps fixtures and PT_LOAD metadata from the offline ELF.

For an executable PT_LOAD and a matching executable file mapping:
- align p_offset and p_vaddr down to the target page size;
- load_bias = mapping.start - aligned_p_vaddr;
- runtime_va = load_bias + (static_va & ~1);
- restore bit 0 for Thumb callable pointers when the static input carried the Thumb bit.

The resolver requires one executable mapping for the exact expected path and aligned segment file offset. It rejects missing/ambiguous/wrong-permission mappings, invalid segment coverage, negative bias, range overflow, and resolved addresses outside the mapping. This models PIE/ASLR without hard-coding a historical base.

The actual ELF is ET_DYN with two PT_LOAD segments. Its first executable PT_LOAD starts at file offset and VA zero; runtime maps still need exact segment/path correlation before any hypothetical address is used. Tests use synthetic mappings only.
