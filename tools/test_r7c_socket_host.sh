#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
out="$repo/build/r7c/socket-host"
mkdir -p "$out"
flags=
if [ -n "${SANITIZERS:-}" ]; then flags="-fsanitize=$SANITIZERS -fno-omit-frame-pointer"; fi
"${CXX:-clang++}" -std=c++17 -Wall -Wextra -Werror -pthread \
  $flags \
  "$repo/native/platform/android/android_socket_adapter.cpp" \
  "$repo/native/tests/android_socket_adapter_test.cpp" $flags -o "$out/socket-test"
"$out/socket-test"
