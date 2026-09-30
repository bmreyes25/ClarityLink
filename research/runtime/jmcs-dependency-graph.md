# jmcs dependency graph

**HONDA CONFIRMED STATIC DT_NEEDED:** `jmcs` has direct `DT_NEEDED` edges to `libexpat.so`, `libbinder.so`, `libstagefright.so`, `libstagefright_foundation.so`, `libmedia.so`, `liblog.so`, `libutils.so`, `libmedia_native.so`, `libcarplay_proxy.so`, `libgui.so`, `libc.so`, `libstdc++.so`, `libm.so`, `libudev.so`, `libmdnssd.so`, `libcrypto.so`, `libnetutils.so`, `libOpenSLES.so`, and `libdl.so`. It has no `DT_SONAME` shown by its dynamic section.

`libcarplay_proxy.so` directly needs `libexpat.so`, `libc.so`, `libstdc++.so`, and `libm.so`; SONAME `libcarplay_proxy.so`. Its ELF has no `.init_array`, so no constructor entry was found. This file is statically loaded before main executable startup constructors complete because it is a direct jmcs dependency. jmcs itself has an `.init_array` at VA `0x3442a0` (size 12 bytes). AirPlay session Setup is later, during connection handling.

CarPlay/AirPlay implementation is linked into jmcs itself (symbols/source paths in DWARF identify CommunicationPlugin receiver sources); proxy is the Honda callback glue. Transitive Android dependency closure not fully expanded in this note. `DLOPEN` edges are documented separately; exact runtime `dlopen` sites are SQLite extension support, not evidence of CarPlay plugin loading.
