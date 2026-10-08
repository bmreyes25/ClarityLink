#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK r23c (23.2.8568313).}"
ndk_version=$(sed -n 's/^Pkg.Revision = //p' "$ANDROID_NDK_HOME/source.properties")
[ "$ndk_version" = 23.2.8568313 ] || { echo "Expected NDK 23.2.8568313, found $ndk_version" >&2; exit 2; }
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64"
target=i686-linux-android17
CC="$toolchain/bin/$target-clang"
CXX="$toolchain/bin/$target-clang++"
AR="$toolchain/bin/llvm-ar"
RANLIB="$toolchain/bin/llvm-ranlib"
STRIP="$toolchain/bin/llvm-strip"
src="$repo/build/r7c/ffmpeg-6.1.6-api17-x86"
out="$repo/build/r7c/ffmpeg-x86"
r7c_out="$repo/build/r7c/android-x86"
mkdir -p "$out" "$r7c_out"
if [ ! -d "$src" ]; then cp -R "$repo/build/r7c/ffmpeg-6.1.6-api17" "$src"; fi
if [ ! -f "$out/ffmpeg/lib/libavcodec.a" ] || [ ! -f "$out/ffmpeg/lib/libavutil.a" ] || [ ! -f "$out/ffmpeg/lib/libswscale.a" ]; then
  cd "$src"
  make distclean >/dev/null 2>&1 || true
  export CC CXX AR RANLIB STRIP
  export CFLAGS='-O2 -fPIC -fno-strict-aliasing'
  export CXXFLAGS="$CFLAGS -std=c++17 -fexceptions -frtti"
  ./configure --prefix="$out/ffmpeg" --target-os=android --arch=x86 --cpu=i686 \
    --enable-cross-compile --cc="$CC" --cxx="$CXX" --ar="$AR" --ranlib="$RANLIB" --strip="$STRIP" \
    --sysroot="$toolchain/sysroot" --disable-shared --enable-static --enable-pic --disable-programs \
    --disable-doc --disable-debug --disable-network --disable-autodetect --disable-everything \
    --disable-avformat --disable-avdevice --disable-avfilter --disable-swresample --disable-postproc \
    --enable-avcodec --enable-avutil --enable-swscale --enable-decoder=h264 --disable-asm \
    --disable-gpl --disable-nonfree --disable-version3 --disable-iconv --disable-zlib --disable-bzlib \
    --disable-lzma --disable-symver --extra-cflags="$CFLAGS" --extra-cxxflags="$CXXFLAGS" \
    --extra-ldflags='-Wl,--no-undefined'
  make -j"${JOBS:-4}"
  make install
fi
"$CXX" -std=c++17 -O2 -g -fPIC -fvisibility=hidden -fno-rtti -DCLARITYLINK_TEST_DIAGNOSTICS \
  -I"$repo/native/include" -I"$repo/native/platform/android" \
  -I"$out/ffmpeg/include" -fexceptions -shared "$repo/native/core/receiver.cpp" \
  "$repo/native/platform/android/surface_sink_core.cpp" \
  "$repo/native/platform/android/android_surface_sink.cpp" \
  "$repo/native/platform/android/android_socket_adapter.cpp" \
  "$repo/native/platform/android/r7c6_race_controller.cpp" \
  "$repo/native/platform/android/jni_bridge.cpp" -L"$out/ffmpeg/lib" \
  -Wl,--no-undefined -Wl,--exclude-libs,ALL -Wl,-soname,libclaritylink_android.so \
  -lavcodec -lswscale -lavutil -landroid -llog -lm -ldl -static-libstdc++ -o "$r7c_out/libclaritylink_android.so"
cp "$r7c_out/libclaritylink_android.so" "$r7c_out/libclaritylink_android.unstripped.so"
"$toolchain/bin/llvm-strip" --strip-unneeded "$r7c_out/libclaritylink_android.so"
"$toolchain/bin/llvm-readelf" -h -d "$r7c_out/libclaritylink_android.so" > "$r7c_out/elf-report.txt"
shasum -a 256 "$r7c_out/libclaritylink_android.so" > "$r7c_out/SHA256SUMS"
printf 'NDK=%s\nCompiler=%s\nTarget=%s\nAPI=17\nRuntime ABI=x86 (test only)\n' \
  "$ndk_version" "$("$CC" --version | head -1)" "$target" > "$r7c_out/build-manifest.txt"
cat "$r7c_out/SHA256SUMS" >> "$r7c_out/build-manifest.txt"
echo "Built $r7c_out/libclaritylink_android.so"
