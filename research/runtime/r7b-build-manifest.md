# R7B build manifest

The target builder writes the reproducible build metadata to
`research/runtime/r7b-build-manifest.json` with
`ANDROID_NDK_HOME=/path/to/23.2.8568313 tools/write_r7b_manifest.py` after
`tools/build_android_api17_armv7.sh` succeeds. The JSON records source commit,
NDK/compiler/linker, target/API/ABI, FFmpeg release and configure feature set,
compiler/linker flags, and the final artifact SHA-256. It deliberately excludes
local SDK paths.

The generated `.so`, FFmpeg archives, and NDK are ignored build inputs/outputs;
the source build script and manifest generator are tracked. The artifact is
not committed. Its hash and ELF details are also summarized in
`r7b-armv7-abi-report.md`.
