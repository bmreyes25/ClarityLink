# Android 4.2 ARM dynamic linker — Step 41B result

Honda target is Android API 17 / ARM32. The exact tagged `android-4.2_r1` source `linker/dlfcn.c` was opened and checked. ARM `ANDROID_LIBDL_STRTAB` includes `dlopen`, `dlclose`, `dlsym`, `dlerror`, `dladdr`, and `dl_unwind_find_exidx`; only x86/MIPS branch includes `dl_iterate_phdr`. The same source's `dladdr` locates `soinfo` with `find_containing_library`, returns `si->name` and `si->base`, and conditionally finds a containing dynamic symbol. [AOSP tagged source](https://android.googlesource.com/platform/bionic/+/android-4.2_r1/linker/dlfcn.c)

| Method | API17 ARM conclusion | Constraints |
|---|---|---|
| `dlsym(handle,name)` | likely available; Honda jmcs imports it | Needs exported/dynamic symbol and correct handle/scope. Internal jmcs `.symtab` names are not dlsym-visible. |
| `dladdr(ptr,info)` | AOSP YES; Honda YES export confirmed | Requires pointer into target module; Honda semantic equivalence high-confidence but stripped linker implementation not fully disassembled. |
| `dlopen(NULL)` + `dlsym` | UNKNOWN / conditional | Main-program symbol visibility and local executable exports matter; cannot discover non-dynamic symbols. |
| `/proc/self/maps` | Linux procfs design makes own maps a plausible read-only source; Honda policy/config not proven | Bounded parser; verify self access on exact target in a later authorized test. |
| `dl_iterate_phdr` | AOSP NO on ARM; Honda NO in archived `libdl.so` dynsym | Do not use it. |
| `link_map` / `r_debug` | unsupported as a design dependency | No Honda/AOSP API17 availability established; private linker internals are version-sensitive. |

Honda archive SHA-256s and export table are in `honda-bionic-dladdr.md`; exact Honda linker semantics remain an implementation-level inference, not a claim based solely on AOSP.

Interim: external `/proc/<jmcs>/maps` is no longer required. The in-process methods have exact API/export coverage; target execution and an in-process entry seam remain separate gates.
