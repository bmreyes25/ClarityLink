#!/usr/bin/env python3
"""Public-safety gate for publication candidates in the public ClarityLink repository.

Reads file contents from Git objects (a ref range, or the index with --staged), so it
checks exactly what would be published and never touches ignored local files. It never
prints matched content, only the rule, path and line number.

Rules
  PS001 forbidden file extension (binaries, archives, keys, firmware, media)
  PS002 opaque binary content (NUL bytes or a known executable/archive magic number)
  PS003 oversize file
  PS004 high-confidence credential or private key
  PS005 VIN-like identifier
  PS006 absolute path that names a local user account
  PS007 file under a restricted research directory that is not explicitly allowlisted

Every rule is evaluated per (path, rule) against an allowance in
docs/security/public-safety-allowlist.json. The default allowance is zero, so a new
violation fails while existing, reviewed content is recorded explicitly with a reason.
An allowance is a ceiling: more matches than allowed fail even in an allowlisted file.

This gate is a mechanical backstop, not a review. It does not replace reading the diff.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ALLOWLIST_PATH = "docs/security/public-safety-allowlist.json"
MAX_BYTES = 1024 * 1024
MAX_IMAGE_BYTES = 1024 * 1024

FORBIDDEN_SUFFIXES = {
    ".apk", ".aab", ".dex", ".odex", ".oat", ".vdex", ".art", ".so", ".dylib", ".dll", ".exe",
    ".elf", ".o", ".a", ".img", ".bin", ".rom", ".fw", ".tar", ".tgz", ".gz", ".bz2", ".xz", ".zip",
    ".7z", ".rar", ".jar", ".war", ".pcap", ".pcapng", ".dump", ".raw", ".core", ".keystore", ".jks",
    ".p12", ".pfx", ".pem", ".key", ".der", ".crt", ".cer", ".mp4", ".mov", ".avi", ".mkv", ".db",
    ".sqlite", ".sqlite3",
}
ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg"}
RESTRICTED_PARTS = {
    "captures", "private-captures", "acquisition", "extracted", "decompiled", "decompiled-clean",
    "deodexed", "firmware", "vendor-dumps", "raw-evidence", "evidence", "smali", "dumps",
}
MAGICS = (
    (b"\x7fELF", "ELF executable"), (b"\xca\xfe\xba\xbe", "Mach-O universal or Java class"),
    (b"\xfe\xed\xfa\xce", "Mach-O"), (b"\xfe\xed\xfa\xcf", "Mach-O"), (b"\xcf\xfa\xed\xfe", "Mach-O"),
    (b"\xce\xfa\xed\xfe", "Mach-O"), (b"MZ", "PE executable"), (b"dex\n", "Dalvik dex"),
    (b"PK\x03\x04", "zip or apk archive"), (b"\x1f\x8b", "gzip archive"), (b"BZh", "bzip2 archive"),
    (b"\xfd7zXZ", "xz archive"), (b"7z\xbc\xaf", "7z archive"), (b"SQLite format 3", "SQLite database"),
    (b"bplist00", "binary plist"), (b"\xd4\xc3\xb2\xa1", "pcap capture"), (b"\xa1\xb2\xc3\xd4", "pcap capture"),
    (b"\x0a\x0d\x0d\x0a", "pcapng capture"), (b"ANDROID!", "Android boot image"), (b"OggS", "ogg media"),
)
SECRET_PATTERNS = [re.compile(p) for p in (
    rb"gh[pousr]_[A-Za-z0-9]{30,}", rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY",
    rb"AKIA[0-9A-Z]{16}", rb"ASIA[0-9A-Z]{16}", rb"xox[abprs]-[A-Za-z0-9-]{10,}",
    rb"AIza[0-9A-Za-z_\-]{35}", rb"sk-[A-Za-z0-9]{32,}",
    rb"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
)]
VIN_CANDIDATE = re.compile(rb"(?<![A-Za-z0-9])[A-HJ-NPR-Z0-9]{17}(?![A-Za-z0-9])")
VIN_YEAR = set(b"ABCDEFGHJKLMNPRSTVWXY123456789")
PRIVATE_PATH = re.compile(
    rb"(?:/Users/|/home/|C:\\Users\\)(?!Shared\b|Public\b|runner\b|user\b|username\b|you\b|<|\{|\$|\*|\.\.)"
    rb"[A-Za-z][A-Za-z0-9._-]{2,}"
)

RULES = {
    "PS001": "forbidden file extension",
    "PS002": "opaque binary content",
    "PS003": "oversize file",
    "PS004": "credential or private key pattern",
    "PS005": "VIN-like identifier",
    "PS006": "absolute path naming a local account",
    "PS007": "restricted research directory not allowlisted",
}


@dataclass(frozen=True)
class Violation:
    rule: str
    path: str
    line: int
    detail: str

    def render(self) -> str:
        where = f"{self.path}:{self.line}" if self.line else self.path
        return f"{self.rule} {where}  {RULES[self.rule]} ({self.detail})"


def git(root: Path, *args: str, binary: bool = False):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace").strip() or f"git {args[0]} failed")
    return p.stdout if binary else p.stdout.decode(errors="replace")


def load_allowlist(text: str | None) -> dict:
    if text is None:
        return {"vin_samples": [], "allow": []}
    data = json.loads(text)
    if data.get("schema") != 1:
        raise ValueError("allowlist schema must be 1")
    for entry in data.get("allow", []):
        for field in ("path", "rule", "max", "reason"):
            if field not in entry:
                raise ValueError(f"allowlist entry missing {field!r}: {entry}")
        if entry["rule"] not in RULES or not str(entry["reason"]).strip():
            raise ValueError(f"allowlist entry has an unknown rule or empty reason: {entry}")
        if not isinstance(entry["max"], int) or entry["max"] < 0:
            raise ValueError(f"allowlist max must be a non-negative integer: {entry}")
    return data


def allowance(allow: dict, path: str, rule: str) -> int:
    best = 0
    for entry in allow.get("allow", []):
        if entry["rule"] == rule and fnmatch.fnmatchcase(path, entry["path"]):
            best = max(best, entry["max"])
    return best


def scan_blob(path: str, data: bytes, allow: dict) -> list[Violation]:
    found: list[Violation] = []
    suffix = Path(path).suffix.lower()
    parts = path.split("/")

    # Rules that count occurrences are collected first and compared to the ceiling.
    counts: dict[str, list[Violation]] = {r: [] for r in RULES}

    if suffix in FORBIDDEN_SUFFIXES:
        counts["PS001"].append(Violation("PS001", path, 0, f"suffix {suffix}"))
    head = data[:8192]
    is_image = suffix in ALLOWED_IMAGE_SUFFIXES
    if not is_image:
        if b"\x00" in head:
            counts["PS002"].append(Violation("PS002", path, 0, "NUL bytes in a non-image file"))
        else:
            for magic, label in MAGICS:
                if data.startswith(magic):
                    counts["PS002"].append(Violation("PS002", path, 0, label))
                    break
    limit = MAX_IMAGE_BYTES if is_image else MAX_BYTES
    if len(data) > limit:
        counts["PS003"].append(Violation("PS003", path, 0, f"{len(data)} bytes over {limit}"))
    if RESTRICTED_PARTS & set(parts[:-1]):
        counts["PS007"].append(Violation("PS007", path, 0, "under " + sorted(RESTRICTED_PARTS & set(parts[:-1]))[0]))

    if b"\x00" not in head:   # text-level rules
        samples = {s.encode() for s in allow.get("vin_samples", [])}
        for number, line in enumerate(data.split(b"\n"), 1):
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    counts["PS004"].append(Violation("PS004", path, number, "pattern match, value withheld"))
                    break
            for m in VIN_CANDIDATE.finditer(line):
                v = m.group(0)
                if (re.search(rb"[A-Z]", v) and re.search(rb"[0-9]", v) and v[9] in VIN_YEAR
                        and (v[8:9].isdigit() or v[8:9] == b"X") and v not in samples
                        and not re.fullmatch(rb"[0-9A-F]{17}", v)):
                    counts["PS005"].append(Violation("PS005", path, number, "value withheld"))
            if PRIVATE_PATH.search(line):
                counts["PS006"].append(Violation("PS006", path, number, "account name withheld"))

    for rule, items in counts.items():
        if len(items) > allowance(allow, path, rule):
            found.extend(items)
    return found


def changed_paths(root: Path, base: str, head: str) -> list[str]:
    merge_base = git(root, "merge-base", base, head).strip()
    out = git(root, "diff", "--name-only", "--diff-filter=ACMR", "-z", f"{merge_base}", head)
    return [p for p in out.split("\0") if p]


def read_blob(root: Path, spec: str) -> bytes:
    return git(root, "show", spec, binary=True)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--base", help="check files changed since the merge-base with this ref")
    mode.add_argument("--staged", action="store_true", help="check the index")
    mode.add_argument("--all", action="store_true", help="audit every tracked file at --head")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--allowlist-ref", default=None,
                    help="read the allowlist from this ref (default: the checked head, or the index)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.staged:
        paths = [p for p in git(root, "diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split("\0") if p]
        spec = lambda p: ":" + p
        allow_spec = ":" + ALLOWLIST_PATH
    else:
        if args.base:
            paths = changed_paths(root, args.base, args.head)
        else:
            paths = [p for p in git(root, "ls-tree", "-r", "--name-only", "-z", args.head).split("\0") if p]
        spec = lambda p: f"{args.head}:{p}"
        allow_spec = f"{args.allowlist_ref or args.head}:{ALLOWLIST_PATH}"
    try:
        allow = load_allowlist(read_blob(root, allow_spec).decode())
    except RuntimeError:
        print(f"PUBLIC_SAFETY_ERROR allowlist not found at {allow_spec}", file=sys.stderr)
        return 2
    except (ValueError, json.JSONDecodeError) as error:
        print(f"PUBLIC_SAFETY_ERROR invalid allowlist: {error}", file=sys.stderr)
        return 2

    violations: list[Violation] = []
    if ALLOWLIST_PATH in paths:
        print(f"PUBLIC_SAFETY_NOTICE {ALLOWLIST_PATH} is modified by this candidate; a reviewer must read the diff of its entries")
    for path in paths:
        if path == ALLOWLIST_PATH:
            continue   # reviewed through the diff; its entries are validated above
        try:
            data = read_blob(root, spec(path))
        except RuntimeError:
            continue   # gitlinks and other non-blob entries
        violations.extend(scan_blob(path, data, allow))

    for v in sorted(violations, key=lambda v: (v.rule, v.path, v.line)):
        print(v.render())
    scope = "staged" if args.staged else ("changed since " + args.base if args.base else "all tracked")
    if violations:
        print(f"PUBLIC_SAFETY_FAIL violations={len(violations)} files_checked={len(paths)} scope={scope}")
        return 1
    print(f"PUBLIC_SAFETY_PASS files_checked={len(paths)} scope={scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
