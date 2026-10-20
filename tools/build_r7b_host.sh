#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$repo/build/r7b/host"
mkdir -p "$out"
fixtures="$repo/build/r7b/fixtures"
mkdir -p "$fixtures"
"${PYTHON:-python3}" "$repo/tools/materialize_r7b_fixtures.py" "$fixtures"
pkgconf=${PKG_CONFIG:-pkg-config}
sanitizer_flags=
if [ -n "${SANITIZERS:-}" ]; then sanitizer_flags="-fsanitize=$SANITIZERS -fno-omit-frame-pointer"; fi
command -v "$pkgconf" >/dev/null 2>&1 || { echo 'pkg-config/pkgconf is required' >&2; exit 2; }
"$pkgconf" --exists libavcodec libavutil libswscale || { echo 'FFmpeg development libraries are required' >&2; exit 2; }
"${CXX:-clang++}" -std=c++17 -O2 -g -Wall -Wextra -Wconversion -Werror=return-type $sanitizer_flags \
  -I"$repo/native/include" $("$pkgconf" --cflags libavcodec libavutil libswscale) \
  "$repo/native/core/receiver.cpp" "$repo/native/tests/receiver_test.cpp" \
  $("$pkgconf" --libs libavcodec libavutil libswscale) -pthread $sanitizer_flags -o "$out/receiver_test"
vector_file="$repo/tests/fixtures/r7b/vectors.json"
primary_id=$("${PYTHON:-python3}" -c 'import json,sys; print(next(x["connection_id"] for x in json.load(open(sys.argv[1]))["setup"] if x["type"] == 110))' "$vector_file")
secondary_id=$("${PYTHON:-python3}" -c 'import json,sys; print(next(x["connection_id"] for x in json.load(open(sys.argv[1]))["setup"] if x["type"] == 111))' "$vector_file")
"$out/receiver_test" "$fixtures/type110-red.h264" "$fixtures/type111-blue.h264" "$primary_id" "$secondary_id"
