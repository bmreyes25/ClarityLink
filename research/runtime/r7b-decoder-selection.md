# R7B decoder selection and dependency review

## Selected implementation

FFmpeg **6.1.6**, built from the upstream release tarball with SHA-256
`d4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a`; the
detached release signature verified against the published FFmpeg release
signing key `B4322F04D67658D8`.
The chosen backend is native `libavcodec` H.264 software decode plus
`libswscale` RGBA conversion. NDK r23c builds ARMv7/API17 static archives;
the receiver links those archives into `libclaritylink_receiver.so`. The
host-native harness uses the system FFmpeg development libraries available
on the build host; this host build has been tested with FFmpeg 9.0.2. It has
not yet been runtime-tested against the target ARM archive.

Configure enables only libavcodec, libavutil, libswscale, and H.264 decode.
The receiver supplies complete bounded access units, so the standalone parser
is not enabled. It disables shared libraries, programs, docs,
network support, autodetection, filters, format/device/resample/postproc
libraries, encoders, hardware acceleration, GPL/nonfree/version-3 code,
assembly optimizations, NEON, and VFP assembly. No external libraries are
enabled. License reported by the upstream build is LGPL 2.1 or later. LGPL
notices/source obligations must be preserved in any future distribution.

The pinned FFmpeg source is from the upstream release directory. The decoder
does parse untrusted H.264 internally, so receiver limits cap payloads at 2 MiB,
dimensions at 4096x4096, and RGBA output at 64 MiB. FFmpeg remains a substantial
codec attack surface; only H.264 decode is enabled and production encryption
providers fail closed pending real protocol evidence. [FFmpeg releases](https://ffmpeg.org/releases/),
[FFmpeg security](https://ffmpeg.org/security.html).

## Alternatives reviewed

* Generic `MediaCodec` was not selected as a decoder fallback because hardware
  codec availability and usable output formats on the Honda are unobserved.
  API17 framework adapter work is deferred to R7C and will not imply Honda
  hardware support.
* FFmpeg CLI alone was rejected for Android. The target artifact contains
  `libavcodec` and performs decode in the native library.

## Dependency inventory

| Dependency | Version / license | Purpose | Target/support | Build scope |
|---|---|---|---|---|
| Android NDK | r23c 23.2.8568313; Android toolchain license | clang/LLD/sysroot | ARMv7 API17 | pinned wrappers, no bundled SDK |
| FFmpeg | 6.1.6; LGPL-2.1-or-later configuration | H.264 decode, RGBA conversion | static ARMv7/API17 cross-build | only codec/util/swscale and H.264 decoder, no parser/demuxer/protocol, C-only asm-disabled build |
| C++ standard library | NDK r23c libc++ static | RAII/core | bundled into `.so` | C++17, exceptions enabled for rollback, RTTI disabled, static runtime |
| Python test reference | repository dependency set | differential vector driver | host only | existing R7A Python receiver |
| FFmpeg host dev libraries | local 9.0.2; CI distro package | native host harness | host only | not a shipped dependency |

No separate parser/compression libraries are added. Android artifact NEEDED
libraries are `libc.so`, `libm.so`, and `libdl.so`; `libc++` is statically
linked. Android target runtime execution is not claimed.
