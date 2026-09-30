# Honda in-process module location

Exact target `jmcs` is ARM32 ET_DYN/PIE-style. The reusable address formula is documented in `honda-jmcs-elf-model.md`. A valid locator must first identify the exact module by canonical pathname plus SHA-256/ELF identity, select the executable PT_LOAD mapping by aligned file offset, calculate load bias with checked arithmetic, and ensure target VA lies within executable mapped bytes.

`dladdr` on a known jmcs function pointer would be the simplest route if Honda API17 exports it. The likely pointers are an internal callback passed into ClarityLink, or a known exported/dynamic function in a library. `AirPlayCopyServerInfo` itself is not in `.dynsym`, so `dlsym` cannot be assumed to find it. `dladdr` for the CarPlay implementation is conditional on first obtaining a pointer in that module. `/proc/self/maps` is a plausible self-readable fallback, but exact target policy has not been tested.

Do not use fixed historical bases. Do not infer that the externally denied procfs access applies to the process reading its own maps. Do not use modern `dl_iterate_phdr` until API17 support is proven.

Decision: **JMCS CAN SELF-LOCATE: CONDITIONAL**. **CarPlay module: CONDITIONAL** (known pointer and exact module identity needed). The unresolved issue for a future interposer is primarily its Honda load seam, not the theoretical access to another process's maps.
