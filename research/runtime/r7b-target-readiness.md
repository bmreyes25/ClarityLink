# R7B target readiness inventory

| Capability | R7B classification | Basis / limits |
|---|---|---|
| Native receiver core | HOST_NATIVE_CONFIRMED | generation-scoped C++17 owner, native host harness |
| Native Type110 | HOST_NATIVE_CONFIRMED | independent ownership, media decode/output fixtures only |
| Native Type111 | HOST_NATIVE_CONFIRMED | independent synthetic path; real framing/security unknown |
| Native media | HOST_NATIVE_CONFIRMED | bounded vector transport and 15-byte test framer; no real transport |
| Native decoder | HOST_NATIVE_CONFIRMED | actual H.264 decoded by host libavcodec; target library linked but not executed |
| Native dual output | HOST_NATIVE_CONFIRMED | two independent logical memory sinks, concurrent receive and teardown tests |
| API17 compatibility | ANDROID_ARMV7_BUILD_CONFIRMED | API17 NDK wrapper/sysroot link; 114 imports checked against API17 stubs |
| ARMv7 ABI | ANDROID_ARMV7_BUILD_CONFIRMED | ELF32 ARM EABI5, little-endian, armeabi-v7a attributes |
| Host/native conformance | HOST_NATIVE_CONFIRMED | shared H.264 assets and JSON vector exercised by Python and C++ tests |
| Memory/resource safety | PARTIAL | RAII, limits, ASan/UBSan host run; TSan result and target runtime remain separate |
| Real authentication | EVIDENCE_REQUIRED | no genuine MFi/iPhone authority |
| Real Type111 security | EVIDENCE_REQUIRED | production provider intentionally fails closed |
| Honda executable compatibility | EVIDENCE_REQUIRED | no Honda execution; output is a native shared library |
| Honda Display0 | EVIDENCE_REQUIRED | no Honda display adapter/admission test |
| Honda Display1 | EVIDENCE_REQUIRED | no cluster admission/safe-area/warning-z-order test |
| Honda USB/iAP2 | EVIDENCE_REQUIRED | interfaces only; ownership unresolved |
| Honda audio/controls | EVIDENCE_REQUIRED | interfaces only; no audio/Siri/steering integration |

Other unresolved gates are preserved from R7A: real `/info` and SETUP
acceptance, Type110/Type111 production media security, Type111 framing, stock
session ownership and restoration, decoder capability on the Honda, audio,
Siri, process lifecycle, warning visibility, and physical cluster dimensions.
No item is promoted from inference.
