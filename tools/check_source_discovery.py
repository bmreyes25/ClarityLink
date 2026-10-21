#!/usr/bin/env python3
"""Report ignored source-like files so the repository allowlist cannot hide them silently."""
import argparse
import subprocess
from pathlib import Path

SOURCE_SUFFIXES = {".py", ".sh", ".c", ".h", ".cc", ".cpp", ".java", ".kt", ".swift", ".md", ".json", ".yaml", ".yml", ".toml"}
SAFE_IGNORED_DIRS = {"build", ".venv", "__pycache__", ".pytest_cache", "research/captures", "research/decompiled", "research/decompiled-clean", "research/deodexed", "research/extracted", "research/logs", "research/resources", "research/search", "research/smali", "research/tools", "research/tmp"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = Path(subprocess.check_output(["git", "-C", str(args.repo), "rev-parse", "--show-toplevel"], text=True).strip())
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "--others", "--ignored", "--exclude-standard", "-z"], text=True).split("\0")
    found = []
    for name in filter(None, paths):
        path = Path(name)
        if path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(name == item or name.startswith(item + "/") for item in SAFE_IGNORED_DIRS):
            continue
        found.append(name)
    for name in found:
        print(f"IGNORED_SOURCE {name}")
    print(f"IGNORED_SOURCE_COUNT {len(found)}")
    return 1 if found else 0

if __name__ == "__main__":
    raise SystemExit(main())
