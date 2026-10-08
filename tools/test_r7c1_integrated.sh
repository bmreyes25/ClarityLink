#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$repo/build/r7c1/host"
fixtures="$repo/build/r7b/fixtures"
mkdir -p "$out" "$fixtures"
"${PYTHON:-python3}" "$repo/tools/materialize_r7b_fixtures.py" "$fixtures"
pkgconf=${PKG_CONFIG:-pkg-config}
"$pkgconf" --exists libavcodec libavutil libswscale || { echo 'FFmpeg development libraries are required' >&2; exit 2; }
sanitizer_flags=
if [ -n "${SANITIZERS:-}" ]; then sanitizer_flags="-fsanitize=$SANITIZERS -fno-omit-frame-pointer"; fi
common_flags="-std=c++17 -O1 -g -Wall -Wextra -Wconversion -Werror=return-type"
"${CXX:-clang++}" $common_flags $sanitizer_flags -I"$repo/native/include" \
  "$repo/native/platform/android/surface_sink_core.cpp" \
  "$repo/native/tests/surface_sink_core_test.cpp" -pthread $sanitizer_flags \
  -o "$out/surface_sink_core_test"
"$out/surface_sink_core_test"
"${CXX:-clang++}" $common_flags $sanitizer_flags \
  "$repo/native/tests/opaque_handle_table_test.cpp" -pthread $sanitizer_flags \
  -o "$out/opaque_handle_table_test"
"$out/opaque_handle_table_test"
"${CXX:-clang++}" $common_flags $sanitizer_flags -I"$repo/native/include" \
  -I"$repo/native/platform/android" $($pkgconf --cflags libavcodec libavutil libswscale) \
  "$repo/native/core/receiver.cpp" "$repo/native/platform/android/surface_sink_core.cpp" \
  "$repo/native/tests/r7c1_integrated_adapter_test.cpp" \
  $($pkgconf --libs libavcodec libavutil libswscale) -pthread $sanitizer_flags \
  -o "$out/r7c1_integrated_adapter_test"
"$out/r7c1_integrated_adapter_test" \
  "$fixtures/type110-red.h264" "$fixtures/type111-blue.h264"
