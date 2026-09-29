# `jmcs` mapped executable-module inventory

Captured 2026-09-29 with the iPhone disconnected from `/system/bin/jmcs` PID `26577`. Source: ignored local `/proc/26577/maps` capture at `research/captures/jmcs-runtime-diff/20260929T160905Z/disconnected/maps.txt`. Load addresses are ASLR-specific to this session.

| Path | Load base | Executable mapping(s) | File offset(s) |
|---|---:|---|---:|
| `/system/lib/libsync.so` | `0x4005a000` | `0x4005a000-0x4005b000` | `0x0` |
| `/system/lib/libOpenSLES.so` | `0x4005d000` | `0x4005d000-0x4005f000` | `0x0` |
| `/system/lib/libudev.so` | `0x4006e000` | `0x4006e000-0x40078000` | `0x0` |
| `/system/lib/libaudioutils.so` | `0x4007e000` | `0x4007e000-0x40080000` | `0x0` |
| `/system/bin/jmcs` | `0x4008f000` | `0x4008f000-0x403cf000` | `0x0` |
| `/system/lib/libexpat.so` | `0x403ff000` | `0x403ff000-0x40413000` | `0x0` |
| `/system/lib/libc.so` | `0x40416000` | `0x40416000-0x4045b000` | `0x0` |
| `/system/lib/libstdc++.so` | `0x4046b000` | `0x4046b000-0x4046c000` | `0x0` |
| `/system/lib/libm.so` | `0x4046e000` | `0x4046e000-0x40483000` | `0x0` |
| `/system/lib/liblog.so` | `0x40485000` | `0x40485000-0x40488000` | `0x0` |
| `/system/lib/libhardware.so` | `0x4048a000` | `0x4048a000-0x4048b000` | `0x0` |
| `/system/bin/linker` | `0x4048e000` | `0x4048e000-0x4049c000` | `0x0` |
| `/system/lib/libbinder.so` | `0x404a9000` | `0x404a9000-0x404c7000` | `0x0` |
| `/system/lib/libcutils.so` | `0x404cd000` | `0x404cd000-0x404da000` | `0x0` |
| `/system/lib/libutils.so` | `0x404ea000` | `0x404ea000-0x40502000` | `0x0` |
| `/system/lib/libcorkscrew.so` | `0x40505000` | `0x40505000-0x40508000` | `0x0` |
| `/system/lib/libgccdemangle.so` | `0x4050a000` | `0x4050a000-0x4050e000` | `0x0` |
| `/system/lib/libz.so` | `0x40511000` | `0x40511000-0x40527000` | `0x0` |
| `/system/lib/libstagefright.so` | `0x40529000` | `0x40529000-0x4061c000` | `0x0` |
| `/system/lib/libcamera_client.so` | `0x40624000` | `0x40624000-0x4063b000` | `0x0` |
| `/system/lib/libui.so` | `0x40642000` | `0x40642000-0x4064c000` | `0x0` |
| `/system/lib/libgui.so` | `0x4064e000` | `0x4064e000-0x4067b000` | `0x0` |
| `/system/lib/libEGL.so` | `0x40684000` | `0x40684000-0x406c1000` | `0x0` |
| `/system/lib/libGLES_trace.so` | `0x406cb000` | `0x406cb000-0x4070b000` | `0x0` |
| `/system/lib/libstlport.so` | `0x4070d000` | `0x4070d000-0x40741000` | `0x0` |
| `/system/lib/libGLESv2.so` | `0x40745000` | `0x40745000-0x4074a000` | `0x0` |
| `/system/lib/libcrypto.so` | `0x4074c000` | `0x4074c000-0x40812000` | `0x0` |
| `/system/lib/libdrmframework.so` | `0x40827000` | `0x40827000-0x4083b000` | `0x0` |
| `/system/lib/libicui18n.so` | `0x4083f000` | `0x4083f000-0x40950000` | `0x0` |
| `/system/lib/libicuuc.so` | `0x40958000` | `0x40958000-0x40a43000` | `0x0` |
| `/system/lib/libgabi++.so` | `0x40a51000` | `0x40a51000-0x40a55000` | `0x0` |
| `/system/lib/libmedia.so` | `0x40a57000` | `0x40a57000-0x40abf000` | `0x0` |
| `/system/lib/libsonivox.so` | `0x40ad3000` | `0x40ad3000-0x40b21000` | `0x0` |
| `/system/lib/libstagefright_foundation.so` | `0x40b28000` | `0x40b28000-0x40b33000` | `0x0` |
| `/system/lib/libspeexresampler.so` | `0x40b35000` | `0x40b35000-0x40b38000` | `0x0` |
| `/system/lib/libmedia_native.so` | `0x40b3a000` | `0x40b3a000-0x40b3b000` | `0x0` |
| `/system/lib/libssl.so` | `0x40b3d000` | `0x40b3d000-0x40b6f000` | `0x0` |
| `/system/lib/libstagefright_omx.so` | `0x40b75000` | `0x40b75000-0x40b87000` | `0x0` |
| `/system/lib/libstagefright_yuv.so` | `0x40b8a000` | `0x40b8a000-0x40b8c000` | `0x0` |
| `/system/lib/libvorbisidec.so` | `0x40b8e000` | `0x40b8e000-0x40ba6000` | `0x0` |
| `/system/lib/libstagefright_enc_common.so` | `0x40ba8000` | `0x40ba8000-0x40ba9000` | `0x0` |
| `/system/lib/libstagefright_avc_common.so` | `0x40bab000` | `0x40bab000-0x40bb0000` | `0x0` |
| `/system/lib/libcarplay_proxy.so` | `0x40bb2000` | `0x40bb2000-0x40bb5000` | `0x0` |
| `/system/lib/libmdnssd.so` | `0x40bb7000` | `0x40bb7000-0x40bbd000` | `0x0` |
| `/system/lib/libnetutils.so` | `0x40bbf000` | `0x40bbf000-0x40bc4000` | `0x0` |
| `/system/lib/libwilhelm.so` | `0x40bc6000` | `0x40bc6000-0x40bec000` | `0x0` |
| `/system/lib/libjbt_transport.so` | `0x40c18000` | `0x40c18000-0x40c1b000` | `0x0` |

Unique executable-backed file paths: **47** (45 `.so` files, `jmcs`, and the dynamic linker). The five relevant application/media paths are discussed in [the socket and module baseline](jmcs-runtime-sockets.md).
