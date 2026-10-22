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
  PS008 the gate itself (this scanner or its protected workflow) is modified by the candidate
  PS009 the candidate's allowlist grants more than the trusted allowlist (new or broader entry,
        higher count, new sample)
  PS010 a Git object the gate cannot safely inspect (gitlink, escaping symlink, unsupported mode)

PS001-PS007 are evaluated per (path, rule) against an allowance in
docs/security/public-safety-allowlist.json. The default allowance is zero, so a new
violation fails while existing, reviewed content is recorded explicitly with a reason.
An allowance is a ceiling: more matches than allowed fail even in an allowlisted file.

Trust model: the allowance that applies is read from a TRUSTED ref (the protected base branch),
never from the candidate being judged. The candidate's own allowlist is only compared with the
trusted one, and any expansion fails closed (PS009). Widening an exemption therefore needs a
separate, reviewed update to the trusted baseline. PS008-PS010 cannot be allowlisted. Anything
the gate cannot read or parse is an error (exit 2), never a pass.

When the trusted ref has no allowlist at all (the one-time bootstrap that introduces this gate)
the gate refuses unless --allow-bootstrap is given, and then reports PUBLIC_SAFETY_BOOTSTRAP_UNTRUSTED:
the candidate's allowlist was not independently trusted and a reviewer must read all of it.

This gate is a mechanical backstop, not a review. It does not replace reading the diff.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import posixpath
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
    "PS008": "gate control file modified by the candidate",
    "PS009": "allowlist expanded beyond the trusted baseline",
    "PS010": "Git object the gate cannot safely inspect",
}
ALLOWABLE = {f"PS00{n}" for n in range(1, 8)}
CONTROL_PATHS = (
    "tools/check_public_safety.py",
    ".github/workflows/public-safety.yml",
)


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
    try:
        return _load_allowlist(text)
    except ValueError as error:
        raise ValueError(f"invalid allowlist: {error}") from error


def _load_allowlist(text: str | None) -> dict:
    if text is None:
        return {"vin_samples": [], "allow": []}
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get("schema") != 1:
            raise ValueError("allowlist schema must be 1")
        samples, allow = data.get("vin_samples", []), data.get("allow", [])
        if not isinstance(samples, list) or not all(isinstance(x, str) for x in samples):
            raise ValueError("vin_samples must be a list of strings")
        if not isinstance(allow, list):
            raise ValueError("allow must be a list")
        for entry in allow:
            if not isinstance(entry, dict):
                raise ValueError(f"allowlist entry must be an object: {entry!r}")
            for field in ("path", "rule", "max", "reason"):
                if field not in entry:
                    raise ValueError(f"allowlist entry missing {field!r}: {entry}")
            if not isinstance(entry["path"], str) or not entry["path"]:
                raise ValueError(f"allowlist path must be a non-empty string: {entry}")
            if entry["rule"] not in ALLOWABLE or not str(entry["reason"]).strip():
                raise ValueError(f"allowlist entry has an unknown or non-allowable rule or empty reason: {entry}")
            if not isinstance(entry["max"], int) or isinstance(entry["max"], bool) or entry["max"] < 0:
                raise ValueError(f"allowlist max must be a non-negative integer: {entry}")
        return data
    except json.JSONDecodeError as error:
        raise ValueError(str(error)) from error


def allowance(allow: dict, path: str, rule: str) -> int:
    best = 0
    for entry in allow.get("allow", []):
        if entry["rule"] == rule and fnmatch.fnmatchcase(path, entry["path"]):
            best = max(best, entry["max"])
    return best


def expansions(trusted: dict, candidate: dict) -> list[str]:
    """Everything the candidate's allowlist grants that the trusted one does not. Removing or
    lowering an entry is not an expansion. Messages name the rule and path only."""
    base = {(e["rule"], e["path"]): e["max"] for e in trusted.get("allow", [])}
    out: list[str] = []
    for entry in candidate.get("allow", []):
        key = (entry["rule"], entry["path"])
        if key not in base:
            out.append(f"new {entry['rule']} exception for {entry['path']}")
        elif entry["max"] > base[key]:
            out.append(f"{entry['rule']} count for {entry['path']} raised from {base[key]} to {entry['max']}")
    extra = set(candidate.get("vin_samples", [])) - set(trusted.get("vin_samples", []))
    if extra:
        out.append(f"{len(extra)} new sample exclusion(s) (values withheld)")
    return out


def inspect_object(path: str, mode: str, data_loader) -> Violation | None:
    """Only regular files, and symlinks that stay inside the repository, can be inspected."""
    if mode in ("100644", "100755"):
        return None
    if mode == "120000":
        target = data_loader().decode(errors="replace")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
        if target.startswith("/") or "\\" in target or resolved.startswith("..") or "\x00" in target:
            return Violation("PS010", path, 0, "symlink target outside the repository")
        return None
    kind = {"160000": "gitlink (submodule)"}.get(mode, f"unsupported mode {mode}")
    return Violation("PS010", path, 0, kind)


def scan_blob(path: str, data: bytes, allow: dict) -> list[Violation]:
    found: list[Violation] = []
    suffix = Path(path).suffix.lower()
    parts = path.split("/")

    # Rules that count occurrences are collected first and compared to the ceiling.
    counts: dict[str, list[Violation]] = {r: [] for r in ALLOWABLE}

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


def resolve_commit(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", "--quiet", ref + "^{commit}").strip()


def entries_for(root: Path, args) -> tuple[list[tuple[str, str, str]], object]:
    """(path, mode, status) for everything the candidate adds or changes, and a reader for it.
    Status D (deleted) is reported only so that deleting a control file is visible."""
    if args.staged:
        raw = git(root, "diff", "--cached", "--raw", "-z", "--no-renames", "--diff-filter=ACMRTD")
        reader = lambda p: read_blob(root, ":" + p)
    else:
        reader = lambda p: read_blob(root, f"{args.head}:{p}")
        if args.base:
            merge_base = git(root, "merge-base", args.base, args.head).strip()
            raw = git(root, "diff", "--raw", "-z", "--no-renames", "--diff-filter=ACMRTD", merge_base, args.head)
        else:
            raw = None
    out: list[tuple[str, str, str]] = []
    if raw is not None:
        fields = raw.split("\0")
        i = 0
        while i + 1 < len(fields) and fields[i].startswith(":"):
            meta, path = fields[i].split(), fields[i + 1]
            out.append((path, meta[1], meta[4][0]))
            i += 2
        if any(f for f in fields[i:]):
            raise RuntimeError("unparseable git diff output")
    else:
        listing = git(root, "ls-tree", "-r", "-z", args.head)
        for record in [r for r in listing.split("\0") if r]:
            meta, path = record.split("\t", 1)
            out.append((path, meta.split()[0], "A"))
    return out, reader


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
    ap.add_argument("--trusted-ref", "--allowlist-ref", dest="trusted_ref", default=None,
                    help="ref whose allowlist and gate files are trusted (default: the --base ref; "
                         "origin/main for --staged; the checked head for --all, which is an audit)")
    ap.add_argument("--allow-bootstrap", action="store_true",
                    help="permit the one-time introduction of the gate when the trusted ref has no allowlist")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        return run_gate(root, args)
    except (RuntimeError, ValueError, OSError, UnicodeError) as error:
        print(f"PUBLIC_SAFETY_ERROR {error}", file=sys.stderr)
        return 2


def run_gate(root: Path, args) -> int:
    audit = args.all and not args.trusted_ref
    if args.trusted_ref:
        trusted_ref = args.trusted_ref
    elif args.base:
        trusted_ref = args.base
    elif args.staged:
        trusted_ref = "origin/main"
    else:
        trusted_ref = args.head
    local_fallback = False
    try:
        resolve_commit(root, trusted_ref)
    except RuntimeError:
        if not (args.staged and not args.trusted_ref):
            raise RuntimeError(f"trusted ref {trusted_ref} does not resolve") from None
        trusted_ref, local_fallback = "HEAD", True

    cand_spec = (":" + ALLOWLIST_PATH) if args.staged else f"{args.head}:{ALLOWLIST_PATH}"
    try:
        trusted_text = read_blob(root, f"{trusted_ref}:{ALLOWLIST_PATH}").decode()
    except RuntimeError:
        trusted_text = None
    bootstrap = trusted_text is None
    try:
        candidate_text = read_blob(root, cand_spec).decode()
    except RuntimeError:
        candidate_text = None
    if candidate_text is None and (bootstrap or audit):
        raise RuntimeError(f"allowlist not found at {cand_spec}")
    if candidate_text is None:
        # A branch cut before the trusted allowlist existed has none of its own. It grants nothing, so the
        # trusted allowlist alone applies; only an unparseable allowlist is an error.
        print("PUBLIC_SAFETY_NOTICE the candidate has no allowlist file; the trusted allowlist alone applies")
        candidate_allow = {"vin_samples": [], "allow": []}
    else:
        candidate_allow = load_allowlist(candidate_text)    # invalid: error
    local_publish = args.staged and not args.trusted_ref   # the publisher's pre-commit check, not the authoritative gate
    if bootstrap and not (args.allow_bootstrap or local_fallback or audit or local_publish):
        raise RuntimeError(f"trusted ref {trusted_ref} has no allowlist; the gate cannot establish a trusted "
                           "baseline (use --allow-bootstrap only for the reviewed introduction of this gate)")
    trusted_allow = candidate_allow if (bootstrap or audit) else load_allowlist(trusted_text)

    entries, reader = entries_for(root, args)
    violations: list[Violation] = []
    if not (bootstrap or audit):
        for message in expansions(trusted_allow, candidate_allow):
            violations.append(Violation("PS009", ALLOWLIST_PATH, 0, message))
        control_in_trusted = [c for c in CONTROL_PATHS
                              if subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{trusted_ref}:{c}"],
                                                capture_output=True).returncode == 0]
        for path, _mode, status in entries:
            if path in control_in_trusted:
                violations.append(Violation("PS008", path, 0, f"status {status}; needs owner approval of the gate change"))
    if bootstrap or audit:
        notice = ("PUBLIC_SAFETY_BOOTSTRAP_UNTRUSTED the allowlist and gate come from the candidate itself, "
                  "not from a trusted baseline; a reviewer must read the whole allowlist and scanner"
                  if bootstrap else "PUBLIC_SAFETY_AUDIT the checked tree's own allowlist is used; this is an audit, not a gate")
        print(notice)

    for path, file_mode, status in entries:
        if status == "D":
            continue
        problem = inspect_object(path, file_mode, lambda p=path: reader(p))
        if problem:
            violations.append(problem)
            continue
        violations.extend(scan_blob(path, reader(path), trusted_allow))

    for v in sorted(violations, key=lambda v: (v.rule, v.path, v.line)):
        print(v.render())
    scope = "staged" if args.staged else ("changed since " + args.base if args.base else "all tracked")
    live = [e for e in entries if e[2] != "D"]
    if violations:
        print(f"PUBLIC_SAFETY_FAIL violations={len(violations)} files_checked={len(live)} scope={scope}")
        return 1
    print(f"PUBLIC_SAFETY_PASS files_checked={len(live)} scope={scope}"
          + (" trust=bootstrap-untrusted" if bootstrap else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
