#!/usr/bin/env python3
"""Check ClarityLink documentation and repository hygiene without network access."""

from __future__ import annotations

import re
import posixpath
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
CURRENT_MILESTONE = "R5X"  # Advance with the current-state documents.
REQUIRED_PATHS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/README.md",
    "docs/glossary.md",
    "docs/safety/vehicle-testing.md",
    "docs/project/records.md",
    "docs/project/github-settings.md",
    "research/README.md",
    "step-reports/README.md",
    "step-reports/repository-organization-and-github-health.md",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
)
STRICT_PUBLIC_DOCS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "ROADMAP.md",
    "NEXT_ACTION.md",
    "docs/README.md",
    "docs/glossary.md",
    "docs/architecture/overview.md",
    "docs/development/testing.md",
    "docs/development/evidence-classification.md",
    "docs/safety/vehicle-testing.md",
    "docs/project/records.md",
    "docs/project/github-settings.md",
    "docs/project/license-decision.md",
    "research/README.md",
    "step-reports/README.md",
    "src/README.md",
    "tests/README.md",
    "tools/README.md",
)
LINK_CHECK_DOCS = set(STRICT_PUBLIC_DOCS) | {
    "docs/research/airplay-session-lifecycle-prior-art.md",
    "docs/research/carplay-altscreen-prior-art.md",
    "docs/research/honda-type111-research-plan.md",
}
REPORT_EXCLUSIONS = {"README.md", "RUN_STATUS.md"}
FORBIDDEN_SUFFIXES = {
    ".apk", ".dex", ".odex", ".so", ".img", ".bin", ".tar", ".tgz",
    ".zip", ".pcap", ".pcapng", ".raw", ".dump", ".cap", ".tar.gz",
    ".elf", ".o", ".a", ".dylib", ".dll", ".exe", ".jar", ".aab",
    ".7z", ".rar", ".gz", ".xz", ".bz2",
}
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\((<[^>]+>|[^)]+)\)")
ABSOLUTE_PERSONAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[^\s)\]>]+")


def tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def markdown_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def resolve_markdown_target(source: str, raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    target = target.split(maxsplit=1)[0] if target else ""
    parts = urlsplit(target)
    if parts.scheme or parts.netloc or not parts.path:
        return None
    path = unquote(parts.path)
    if path.startswith("/"):
        resolved = PurePosixPath(path.lstrip("/"))
    else:
        resolved = PurePosixPath(source).parent / PurePosixPath(path)
    return posixpath.normpath(str(resolved))


def main() -> int:
    paths = tracked_paths()
    directories = {
        str(parent)
        for path in paths
        for parent in PurePosixPath(path).parents
        if str(parent) != "."
    }
    failures: list[str] = []
    missing_required = [path for path in REQUIRED_PATHS if path not in paths]
    for path in missing_required:
        failures.append(f"required navigation file is missing: {path}")

    current_sections = {
        "NEXT_ACTION.md": ("## Current action", "## Historical context"),
        "PROJECT_STATE.md": ("## Current snapshot", "## Step "),
        "ROADMAP.md": ("## Current engineering stage", "## Historical receiver target"),
    }
    for source, (start, end) in current_sections.items():
        if source not in paths:
            continue
        content = (ROOT / source).read_text(encoding="utf-8")
        start_at = content.find(start)
        end_at = content.find(end, start_at + len(start)) if start_at >= 0 else -1
        section = content[start_at:end_at if end_at >= 0 else None] if start_at >= 0 else ""
        if CURRENT_MILESTONE not in section:
            failures.append(f"stale current milestone reference in {source}: expected {CURRENT_MILESTONE}")

    markdown = sorted(path for path in paths if path.lower().endswith(".md"))
    broken_links: list[tuple[str, str]] = []
    archived_untracked_references = 0
    for source in markdown:
        text = markdown_source(ROOT / source)
        for match in LINK_RE.finditer(text):
            target = resolve_markdown_target(source, match.group(1))
            if target is None:
                continue
            is_tracked_directory = target == "." or target in directories
            if (
                target not in paths
                and f"{target.rstrip('/')}/README.md" not in paths
                and not is_tracked_directory
            ):
                if source in LINK_CHECK_DOCS:
                    broken_links.append((source, target))
                else:
                    archived_untracked_references += 1
    for source, target in broken_links:
        failures.append(f"broken relative link: {source} -> {target}")

    reports = {
        path for path in paths
        if path.startswith("step-reports/")
        and path.lower().endswith(".md")
        and PurePosixPath(path).name not in REPORT_EXCLUSIONS
    }
    report_index = "step-reports/README.md"
    index_text = markdown_source(ROOT / report_index) if report_index in paths else ""
    indexed_reports: set[str] = set()
    for match in LINK_RE.finditer(index_text):
        target = resolve_markdown_target(report_index, match.group(1))
        if target in reports:
            indexed_reports.add(target)
    for report in sorted(reports - indexed_reports):
        failures.append(f"step report missing from index: {report}")

    forbidden = [
        path for path in sorted(paths)
        if any(path.lower().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)
    ]
    for path in forbidden:
        failures.append(f"forbidden binary/archive/capture extension: {path}")

    allowed_capture_notes = {
        "research/lab/captures/43p/oracle-events.redacted.jsonl",
        "research/lab/captures/43p/session-summary.json",
        "research/lab/captures/43p/session-metadata.md",
    }
    for path in sorted(paths):
        candidate = ROOT / path
        if path.startswith("research/captures/") and not path.endswith(".md"):
            failures.append(f"non-text file under protected research/captures/: {path}")
        if path.startswith("research/lab/captures/") and path not in allowed_capture_notes:
            failures.append(f"unreviewed file under research/lab/captures/: {path}")
        if candidate.is_file():
            with candidate.open("rb") as stream:
                if b"\0" in stream.read(8192):
                    failures.append(f"binary content is not allowed in tracked repository files: {path}")

    for source in STRICT_PUBLIC_DOCS:
        if source not in paths:
            continue
        text = markdown_source(ROOT / source)
        if ABSOLUTE_PERSONAL_PATH_RE.search(text):
            failures.append(f"personal absolute path in visitor-facing document: {source}")
    for source in LINK_CHECK_DOCS:
        if source not in paths:
            continue
        heading_count = len(re.findall(r"^#\s+", markdown_source(ROOT / source), re.MULTILINE))
        if heading_count != 1:
            failures.append(f"visitor-facing document must have one H1 (found {heading_count}): {source}")

    print(
        f"Repository health: {len(markdown)} Markdown files, "
        f"{len(reports)} indexed milestone/support reports, "
        f"{len(broken_links)} broken links in curated docs, "
        f"{archived_untracked_references} historical/untracked references out of CI link scope, "
        f"{len(forbidden)} forbidden tracked file extensions."
    )
    if failures:
        print("Repository health check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("All repository health checks passed (local only; no network or Honda access).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
