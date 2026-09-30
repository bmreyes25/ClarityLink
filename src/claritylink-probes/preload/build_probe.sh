#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: $0 ANDROID_NDK_ROOT OUTPUT_DIR_OUTSIDE_REPOSITORY" >&2
  exit 2
fi

ndk_root=$1
output_dir=$2
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)

case "$output_dir" in
  /*) ;;
  *) echo "output directory must be an absolute path" >&2; exit 2 ;;
esac

mkdir -p "$output_dir"
output_dir=$(CDPATH= cd -- "$output_dir" && pwd)
case "$output_dir/" in
  "$repo_root/"*) echo "refusing to place generated binaries in the repository" >&2; exit 2 ;;
esac

toolchain="$ndk_root/toolchains/llvm/prebuilt/darwin-x86_64"
clang="$toolchain/bin/clang"
sysroot="$toolchain/sysroot"
if [ ! -x "$clang" ] || [ ! -d "$sysroot" ]; then
  echo "Android NDK r23c darwin toolchain not found under: $ndk_root" >&2
  exit 2
fi

target=armv7a-linux-androideabi17

# The executable and preload contain only marker writes and return status.
# Never run them on the host; they target Android ARMv7/API 17.
"$clang" --target="$target" --sysroot="$sysroot" -O2 -Wall -Wextra -Werror \
  -fPIE -pie -Wl,-z,relro,-z,now \
  -Wl,--dynamic-linker=/system/bin/linker \
  -o "$output_dir/claritylink_preload_probe_exec" \
  "$(dirname -- "$0")/probe_exec.c"

"$clang" --target="$target" --sysroot="$sysroot" -O2 -Wall -Wextra -Werror \
  -fPIC -shared \
  -Wl,-z,relro,-z,now \
  -Wl,-soname,libclaritylink_preload_probe.so \
  -o "$output_dir/libclaritylink_preload_probe.so" \
  "$(dirname -- "$0")/probe_preload.c"

printf 'built synthetic ARMv7/API17 probe artifacts in %s\n' "$output_dir"
