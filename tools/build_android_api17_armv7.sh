#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -z "${ANDROID_NDK_HOME:-}" ]; then
  echo 'Set ANDROID_NDK_HOME to Android NDK r23c (23.2.8568313).' >&2
  exit 2
fi
ndk_version=$(sed -n 's/^Pkg.Revision = //p' "$ANDROID_NDK_HOME/source.properties")
[ "$ndk_version" = 23.2.8568313 ] || { echo "Expected NDK 23.2.8568313, found $ndk_version" >&2; exit 2; }
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64"
[ -x "$toolchain/bin/armv7a-linux-androideabi17-clang++" ] || { echo 'NDK lacks API17 ARMv7 compiler wrapper' >&2; exit 2; }
target=armv7a-linux-androideabi17
CC="$toolchain/bin/$target-clang"
CXX="$toolchain/bin/$target-clang++"
AR="$toolchain/bin/llvm-ar"
RANLIB="$toolchain/bin/llvm-ranlib"
STRIP="$toolchain/bin/llvm-strip"
out="$repo/build/r7b/android-armv7-r7b"
cache="$repo/build/r7b/cache"
src="$repo/build/r7b/ffmpeg-6.1.6-r7b-api17"
mkdir -p "$out" "$cache"
archive="$cache/ffmpeg-6.1.6.tar.xz"
if [ ! -f "$archive" ]; then curl -L --fail --retry 3 https://ffmpeg.org/releases/ffmpeg-6.1.6.tar.xz -o "$archive"; fi
echo 'd4fcb164028dd3beee5d92c0ac72e46aac6973c75ea12dc14de07bf8f407370a  '"$archive" | shasum -a 256 -c -
if [ ! -d "$src" ]; then
  tar -xJf "$archive" -C "$repo/build/r7b"
  mv "$repo/build/r7b/ffmpeg-6.1.6" "$src"
fi
if [ ! -f "$out/ffmpeg/lib/libavcodec.a" ] || [ ! -f "$out/ffmpeg/lib/libavutil.a" ] || [ ! -f "$out/ffmpeg/lib/libswscale.a" ]; then
  cd "$src"
  export CC CXX AR RANLIB STRIP
  export CFLAGS='-O2 -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -fPIC -fno-strict-aliasing'
  export CXXFLAGS="$CFLAGS -std=c++17 -fexceptions -frtti"
  if [ ! -f config.h ]; then ./configure --prefix="$out/ffmpeg" --target-os=android --arch=arm --cpu=armv7-a \
    --enable-cross-compile --cc="$CC" --cxx="$CXX" --ar="$AR" --ranlib="$RANLIB" --strip="$STRIP" \
    --sysroot="$toolchain/sysroot" --disable-shared --enable-static --enable-pic --disable-programs \
    --disable-doc --disable-debug --disable-network --disable-autodetect --disable-everything \
    --disable-avformat --disable-avdevice --disable-avfilter --disable-swresample --disable-postproc \
    --enable-avcodec --enable-avutil --enable-swscale --enable-decoder=h264 \
    --disable-asm --disable-neon --disable-vfp \
    --disable-gpl --disable-nonfree --disable-version3 --disable-iconv --disable-zlib --disable-bzlib \
    --disable-lzma --disable-symver --extra-cflags="$CFLAGS" --extra-cxxflags="$CXXFLAGS" \
    --extra-ldflags='-Wl,--no-undefined'; fi
  make -j"${JOBS:-4}"
  make install
fi
target=armv7a-linux-androideabi17
"$toolchain/bin/$target-clang++" -std=c++17 -O2 -fPIC -fvisibility=hidden -fno-rtti \
  -march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16 -I"$repo/native/include" -I"$out/ffmpeg/include" \
  -fexceptions -shared "$repo/native/core/receiver.cpp" -L"$out/ffmpeg/lib" -Wl,--no-undefined -Wl,--exclude-libs,ALL \
  -Wl,-soname,libclaritylink_receiver.so -lavcodec -lswscale -lavutil -lm -ldl -static-libstdc++ \
  -o "$out/libclaritylink_receiver.so"
"$toolchain/bin/llvm-strip" --strip-unneeded "$out/libclaritylink_receiver.so"
"$toolchain/bin/llvm-readelf" -h -A -d "$out/libclaritylink_receiver.so" > "$out/elf-report.txt"
shasum -a 256 "$out/libclaritylink_receiver.so" > "$out/SHA256SUMS"
printf 'NDK=%s\nCompiler=%s\nLinker=%s\nTarget=%s\nAPI=17\nABI=armeabi-v7a\n' \
  "$ndk_version" "$("$CC" --version | head -1)" "$("$toolchain/bin/ld.lld" --version | head -1)" "$target" > "$out/build-manifest.txt"
cat "$out/SHA256SUMS" >> "$out/build-manifest.txt"
echo "Built $out/libclaritylink_receiver.so"
