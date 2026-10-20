#!/usr/bin/env python3
"""Compare ELF dynamic imports against NDK API17 ARM system stubs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--ndk", type=Path, required=True)
    args = parser.parse_args()
    prebuilt = args.ndk / "toolchains/llvm/prebuilt/darwin-x86_64"
    readelf = prebuilt / "bin/llvm-readelf"
    nm = prebuilt / "bin/llvm-nm"
    stub_dir = prebuilt / "sysroot/usr/lib/arm-linux-androideabi/17"
    elf = run(str(readelf), "--dyn-syms", "--wide", str(args.artifact))
    imports = set()
    for line in elf.splitlines():
        fields = line.split()
        if len(fields) >= 8 and fields[6] == "UND":
            imports.add(fields[7].split("@", 1)[0])
    provided: set[str] = set()
    stubs = {}
    for name in ("libc.so", "libm.so", "libdl.so"):
        path = stub_dir / name
        if not path.exists():
            continue
        symbols = run(str(nm), "-D", "--defined-only", str(path))
        stubs[name] = sorted({line.split()[-1].split("@", 1)[0]
                              for line in symbols.splitlines() if line.split()})
        provided.update(stubs[name])
    result = {
        "artifact": args.artifact.name,
        "artifact_sha256": hashlib.sha256(args.artifact.read_bytes()).hexdigest(),
        "api": 17,
        "classifications": {symbol: ("API17_AVAILABLE" if symbol in provided else "UNKNOWN")
                            for symbol in sorted(imports)},
        "unknown": sorted(imports - provided),
        "checked_stubs": sorted(stubs),
    }
    print(json.dumps(result, indent=2))
    return 1 if result["unknown"] else 0


if __name__ == "__main__":
    sys.exit(main())
