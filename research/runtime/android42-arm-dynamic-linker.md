# Android 4.2 ARM dynamic linker — evidence status

Honda target is Android API 17 / ARM32. AOSP `android-4.2_r1` source was not successfully pinned and retrieved in this pass; current AOSP source must not be substituted for that release. Therefore API17 ARM claims below remain provisional until checked against the tag's `libdl` map/source and archived Honda `/system/lib/libdl.so` exports.

| Method | API17 ARM conclusion | Constraints |
|---|---|---|
| `dlsym(handle,name)` | likely available; Honda jmcs imports it | Needs exported/dynamic symbol and correct handle/scope. Internal jmcs `.symtab` names are not dlsym-visible. |
| `dladdr(ptr,info)` | UNKNOWN for exact API17 Honda until archived `libdl.so` symbol table/tag is inspected | Requires a pointer into target module; useful to identify containing object and base if supported. |
| `dlopen(NULL)` + `dlsym` | UNKNOWN / conditional | Main-program symbol visibility and local executable exports matter; cannot discover non-dynamic symbols. |
| `/proc/self/maps` | Linux procfs design makes own maps a plausible read-only source; Honda policy/config not proven | Bounded parser; verify self access on exact target in a later authorized test. |
| `dl_iterate_phdr` | UNKNOWN for android-4.2_r1 ARM in this audit | Do not build around it until exact tagged ARM map proves export. Search results for newer Bionic are not evidence for API17. |
| `link_map` / `r_debug` | unsupported as a design dependency | No Honda/AOSP API17 availability established; private linker internals are version-sensitive. |

Research results surfaced modern Bionic `libdl` maps containing both `dladdr` and `dl_iterate_phdr`; those are specifically not adequate to establish the API17 surface. Required next source check: fetch AOSP tag `android-4.2_r1` `libdl/libdl.arm.map`, `libdl.c`, and linker implementation; compare exports in Honda's archived `libdl.so` and linker without executing them.

Interim: self-location architecture is CONDITIONAL, not ready to ship. `/proc/self/maps` plus static ELF segment matching is the fallback candidate; external `/proc/<jmcs>/maps` is no longer inherently required.
