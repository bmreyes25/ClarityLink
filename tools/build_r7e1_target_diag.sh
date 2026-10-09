#!/bin/sh
set -eu
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK r23c (23.2.8568313).}"
ndk_version=$(sed -n 's/^Pkg.Revision = //p' "$ANDROID_NDK_HOME/source.properties")
[ "$ndk_version" = 23.2.8568313 ] || { echo "Expected NDK 23.2.8568313, found $ndk_version" >&2; exit 2; }
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/darwin-x86_64"
compiler="$toolchain/bin/armv7a-linux-androideabi17-clang"
[ -x "$compiler" ] || { echo 'NDK lacks the API17 ARMv7 C compiler wrapper.' >&2; exit 2; }
source_sha=$(git -C "$repo" rev-parse HEAD)
case "$source_sha" in *[!0-9a-f]*|'') echo 'Could not determine a source commit SHA.' >&2; exit 2;; esac
[ "${#source_sha}" -eq 40 ] || { echo 'Source commit SHA must contain 40 hex digits.' >&2; exit 2; }
out="$repo/build/r7e1/native-armv7"
mkdir -p "$out"
"$compiler" -std=c11 -O2 -Wall -Wextra -Werror -Wformat=2 -Wconversion \
  -fno-builtin -fno-ident -DCLARITYLINK_BUILD_SHA=\"$source_sha\" \
  "$repo/native/diagnostic/claritylink_target_diag.c" -Wl,--no-undefined \
  -Wl,-z,relro -Wl,-z,now -o "$out/claritylink-target-diag"
"$toolchain/bin/llvm-strip" --strip-unneeded "$out/claritylink-target-diag"
"$toolchain/bin/llvm-readelf" -h -A -d --dyn-syms --wide "$out/claritylink-target-diag" > "$out/elf-audit.txt"
shasum -a 256 "$out/claritylink-target-diag" > "$out/SHA256SUMS"
printf 'NDK=%s\nCompiler=%s\nTarget=armv7a-linux-androideabi17\nAPI=17\nABI=armeabi-v7a\nSourceSHA=%s\n' \
  "$ndk_version" "$($compiler --version | head -1)" "$source_sha" > "$out/build-manifest.txt"
cat "$out/SHA256SUMS" >> "$out/build-manifest.txt"
echo "Built $out/claritylink-target-diag"
