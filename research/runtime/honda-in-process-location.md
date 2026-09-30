# Honda in-process module location

Exact target `jmcs` is ARM32 ET_DYN/PIE-style. The reusable address formula is documented in `honda-jmcs-elf-model.md`. A valid locator must first identify the exact module by canonical pathname plus SHA-256/ELF identity, select the executable PT_LOAD mapping by aligned file offset, calculate load bias with checked arithmetic, and ensure target VA lies within executable mapped bytes.

**HONDA CONFIRMED:** archived API17 `libdl.so` dynsym exports `dladdr`. Its exports match the AOSP `android-4.2_r1` ARM table, including `dl_unwind_find_exidx` and excluding `dl_iterate_phdr`. AOSP tag implementation returns module name and `soinfo->base`; exact Honda implementation equivalence remains high-confidence rather than direct disassembly proof.

For the proxy, a future in-process library can use `dlopen("libcarplay_proxy.so", RTLD_NOW)` and `dlsym(handle,"mc_carplay_proxy_screen_register")` to get a pointer in the exact proxy module; jmcs `DT_NEEDED` confirms it is present before CarPlay session Setup. This locates the proxy, not the private AirPlay functions in jmcs. Honda `AirPlayCopyServerInfo` and other useful private receiver functions are not dynsym exports. The bounded `/proc/self/maps` parser is the realistic jmcs-main-executable fallback: match exact executable pathname plus offset-zero RX segment against the static ELF PT_LOAD table. Target read permission hasn't been exercised because this milestone is offline.

Do not use fixed historical bases. Do not infer that the externally denied procfs access applies to the process reading its own maps. Do not use modern `dl_iterate_phdr` until API17 support is proven.

Decision: **JMCS CAN SELF-LOCATE: READY (offline design)** via `/proc/self/maps` with exact pathname/segment/hash gates; **CarPlay proxy self-location: READY (offline design)** via exported proxy symbol -> `dladdr`. Real target access and exact Honda `dladdr` semantics remain untested. The unresolved architecture blocker is loading the library into jmcs.
