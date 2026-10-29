#!/usr/bin/env python3
"""Verify what is actually inside a built API17 APK, from its DEX, not from the source list.

Runs the SDK's `dexdump` on the APK (or reads saved dexdump text with --dexdump-output), parses the
class descriptors and method names, and checks required and forbidden classes and required methods.
It also records the APK and classes.dex SHA-256 so the result is tied to one build. Nothing is
executed from the APK and the APK is never copied anywhere; only a text report is produced.

  verify_apk_dex_classes.py --apk A.apk --dexdump DEXDUMP --label lab \
      --require org.claritylink.renderer.PaneLease --forbid org.claritylink.renderer.PaneEvent \
      --require-method org.claritylink.android.SyntheticFrameFill#fill

Exit 0 only if every requirement holds; 1 on a failed requirement; 2 on a tool or input error.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import zipfile

CLASS_RE = re.compile(r"Class descriptor\s*:\s*'(L[^;']+;)'")
METHOD_RE = re.compile(r"^\s*#\d+\s*:\s*\(in (L[^;']+;)\)\s*$")
NAME_RE = re.compile(r"^\s*name\s*:\s*'([^']+)'")


def descriptor(name: str) -> str:
    return "L" + name.replace(".", "/") + ";"


def parse_dexdump(text: str) -> tuple[set[str], set[tuple[str, str]]]:
    classes: set[str] = set()
    methods: set[tuple[str, str]] = set()
    owner = None
    for line in text.splitlines():
        m = CLASS_RE.search(line)
        if m:
            classes.add(m.group(1))
            continue
        m = METHOD_RE.match(line)
        if m:
            owner = m.group(1)
            continue
        m = NAME_RE.match(line)
        if m and owner:
            methods.add((owner, m.group(1)))
            owner = None
    return classes, methods


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apk", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--dexdump", help="path to the SDK dexdump executable")
    ap.add_argument("--dexdump-output", help="saved dexdump text instead of running dexdump")
    ap.add_argument("--require", action="append", default=[], help="fully qualified class that must be present")
    ap.add_argument("--forbid", action="append", default=[], help="fully qualified class that must be absent")
    ap.add_argument("--require-method", action="append", default=[], help="pkg.Class#method that must be present")
    ap.add_argument("--source-commit", default="unrecorded")
    args = ap.parse_args(argv)
    try:
        with open(args.apk, "rb") as handle:
            apk_bytes = handle.read()
        with zipfile.ZipFile(args.apk) as archive:
            dex_hashes = {n: sha256(archive.read(n)) for n in sorted(archive.namelist())
                          if re.fullmatch(r"classes\d*\.dex", n)}
        if not dex_hashes:
            raise ValueError("the APK contains no classes.dex")
        if args.dexdump_output:
            text = open(args.dexdump_output, encoding="utf-8", errors="replace").read()
        else:
            if not args.dexdump:
                raise ValueError("--dexdump or --dexdump-output is required")
            run = subprocess.run([args.dexdump, args.apk], capture_output=True, text=True, timeout=300)
            if run.returncode:
                raise RuntimeError(f"dexdump failed: {run.stderr.strip()[:200]}")
            text = run.stdout
        classes, methods = parse_dexdump(text)
        if not classes:
            raise ValueError("dexdump output contained no classes")
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print(f"DEX_VERIFICATION_ERROR label={args.label} {error}", file=sys.stderr)
        return 2

    ok = True
    print(f"DEX_VERIFICATION label={args.label} source_commit={args.source_commit} "
          f"apk_sha256={sha256(apk_bytes)} classes_in_dex={len(classes)}")
    for name, digest in dex_hashes.items():
        print(f"DEX_FILE label={args.label} {name} sha256={digest}")
    for name in args.require:
        present = descriptor(name) in classes
        ok &= present
        print(f"DEX_CLASS_{'PRESENT' if present else 'MISSING'} label={args.label} {name}")
    for name in args.forbid:
        absent = descriptor(name) not in classes
        ok &= absent
        print(f"DEX_CLASS_{'ABSENT_AS_EXPECTED' if absent else 'UNEXPECTEDLY_PRESENT'} label={args.label} {name}")
    for spec in args.require_method:
        cls, _, method = spec.partition("#")
        present = (descriptor(cls), method) in methods
        ok &= present
        print(f"DEX_METHOD_{'PRESENT' if present else 'MISSING'} label={args.label} {cls}#{method}")
    print(f"DEX_VERIFICATION_RESULT label={args.label} {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
