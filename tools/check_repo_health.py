#!/usr/bin/env python3
"""Check ClarityLink documentation and repository hygiene without network access."""

from __future__ import annotations

import hashlib
import json
import re
import posixpath
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from check_r5y_sandbox_boundary import check_source as check_r5y_source

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "docs/README.md",
    "docs/status/current.md",
    "docs/status/capabilities.md",
    "docs/status/blockers.md",
    "docs/status/milestones.json",
    "docs/status/cl-r0-review-scope.json",
    "docs/status/cl-r0-validation.md",
    "docs/roadmap/final-development-plan.md",
    "docs/roadmap/milestone-specifications.md",
    "docs/roadmap/dependency-map.md",
    "docs/development/blocker-resolution.md",
    "docs/getting-started/quickstart.md",
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
    "docs/status/current.md",
    "docs/status/cl-r0-validation.md",
    "docs/status/capabilities.md",
    "docs/status/blockers.md",
    "docs/roadmap/final-development-plan.md",
    "docs/roadmap/milestone-specifications.md",
    "docs/roadmap/dependency-map.md",
    "docs/development/blocker-resolution.md",
    "docs/getting-started/overview.md",
    "docs/getting-started/quickstart.md",
    "docs/getting-started/development-setup.md",
    "docs/decisions/README.md",
    "docs/glossary.md",
    "docs/architecture/overview.md",
    "docs/development/testing.md",
    "docs/development/evidence-classification.md",
    "docs/safety/vehicle-testing.md",
    "docs/project/records.md",
    "docs/project/github-settings.md",
    "docs/project/license-decision.md",
    "docs/project/public-repository-practices.md",
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
PUBLIC_IMAGE_MANIFEST = ROOT / "tools/repo_health_public_images.json"
FORBIDDEN_SUFFIXES = {
    ".apk", ".dex", ".odex", ".so", ".img", ".bin", ".tar", ".tgz",
    ".zip", ".pcap", ".pcapng", ".raw", ".dump", ".cap", ".tar.gz",
    ".elf", ".o", ".a", ".dylib", ".dll", ".exe", ".jar", ".aab",
    ".7z", ".rar", ".gz", ".xz", ".bz2",
}
LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\((<[^>]+>|[^)]+)\)")
ABSOLUTE_PERSONAL_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:Users|home)/[^\s)\]>]+")
VIN_RE = re.compile(r"\b(?![A-HJ-NPR-Z0-9]{16}\b)[A-HJ-NPR-Z0-9]{17}\b")
TOKEN_RE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16})\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def tracked_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def indexed_paths() -> set[str]:
    """Return staged or committed paths, distinct from local untracked output."""
    result = subprocess.run(
        ["git", "ls-files", "--cached"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


@lru_cache(maxsize=2)
def _read_index_blobs(root_string: str) -> dict[str, bytes]:
    """Read staged candidate bytes in two Git calls, not one process per file."""
    root = Path(root_string)
    listing = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=root,
                             check=True, capture_output=True).stdout
    records: list[tuple[str, str]] = []
    for entry in listing.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        fields = metadata.split()
        if len(fields) != 3 or fields[2] != b"0":
            continue
        records.append((raw_path.decode("utf-8", errors="surrogateescape"),
                        fields[1].decode("ascii")))
    if not records:
        return {}
    output = subprocess.run(["git", "cat-file", "--batch"], cwd=root,
                            input="".join(oid + "\n" for _, oid in records).encode("ascii"),
                            check=True, capture_output=True).stdout
    blobs: dict[str, bytes] = {}
    cursor = 0
    for path, expected_oid in records:
        header_end = output.index(b"\n", cursor)
        header = output[cursor:header_end].split()
        if len(header) != 3 or header[0].decode("ascii") != expected_oid or header[1] != b"blob":
            raise RuntimeError(f"unexpected staged Git object while reading {path}")
        size = int(header[2])
        start = header_end + 1
        end = start + size
        blobs[path] = output[start:end]
        if output[end:end + 1] != b"\n":
            raise RuntimeError(f"truncated staged Git object while reading {path}")
        cursor = end + 1
    return blobs


def indexed_blob(path: str) -> bytes:
    """Read the staged candidate bytes, never an unstaged working-tree version."""
    try:
        return _read_index_blobs(str(ROOT.resolve()))[path]
    except KeyError as exc:
        raise subprocess.CalledProcessError(1, ["git", "show", f":{path}"]) from exc


def indexed_json(path: str, indexed: set[str]):
    """Load required JSON from the index and fail if it is absent there."""
    if path not in indexed:
        raise FileNotFoundError(f"required indexed JSON file is missing: {path}")
    return json.loads(indexed_blob(path))


def markdown_source(path: str) -> str:
    text = indexed_blob(path).decode("utf-8", errors="replace")
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.DOTALL)
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def is_health_exempt_image(path: str, candidate: bytes, *, is_indexed: bool = True,
                           manifest: dict | None = None) -> bool:
    try:
        if manifest is None:
            manifest = json.loads(indexed_blob("tools/repo_health_public_images.json"))
        approved = (manifest.get("schema") == "claritylink-health-only-image-hashes-v1"
                    and manifest.get("files", {}).get(path) == hashlib.sha256(candidate).hexdigest())
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError, TypeError):
        approved = False
    return approved and is_indexed


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
    indexed = indexed_paths()
    local_paths = tracked_paths()
    paths = indexed
    unindexed_count = len(local_paths - indexed)
    unstaged_count = len(subprocess.run(
        ["git", "diff", "--name-only", "-z"], cwd=ROOT, check=True,
        capture_output=True,
    ).stdout.split(b"\0")) - 1
    directories = {
        str(parent)
        for path in paths
        for parent in PurePosixPath(path).parents
        if str(parent) != "."
    }
    failures: list[str] = []
    # Publication checks use the index snapshot. The sandbox source guard also
    # reads staged Python blobs so unstaged edits cannot change the candidate.
    sandbox_prefix = "src/claritylink-sandbox/"
    sandbox_failures = []
    for path in sorted(p for p in indexed if p.startswith(sandbox_prefix) and p.endswith(".py")):
        sandbox_failures.extend(check_r5y_source(
            indexed_blob(path).decode("utf-8", errors="replace"), path
        ))
    failures.extend(f"R5Y sandbox boundary: {item}" for item in sandbox_failures)
    missing_required = [path for path in REQUIRED_PATHS if path not in paths]
    for path in missing_required:
        failures.append(f"required navigation file is missing: {path}")

    manifest_file = "docs/status/milestones.json"
    if manifest_file in indexed:
        try:
            manifest = indexed_json(manifest_file, indexed)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failures.append(f"status manifest is invalid JSON: {error}")
        else:
            required_manifest_keys = {
                "schema_version", "updated", "current_campaign", "current_milestone",
                "current_milestone_state", "next_technical_milestone", "safeForHonda", "milestones",
            }
            missing_manifest_keys = sorted(required_manifest_keys - manifest.keys())
            if missing_manifest_keys:
                failures.append(f"status manifest is missing required keys: {missing_manifest_keys}")
            expected_ids = [f"CL-R{number}" for number in range(9)]
            milestones = manifest.get("milestones", [])
            ids = [item.get("id") for item in milestones if isinstance(item, dict)]
            if ids != expected_ids:
                failures.append(f"status manifest milestone sequence must be {expected_ids}")
            current_id = manifest.get("current_milestone")
            current_state = manifest.get("current_milestone_state")
            milestone_by_id = {item.get("id"): item for item in milestones if isinstance(item, dict)}
            if current_id not in milestone_by_id:
                failures.append("status manifest current_milestone must identify a listed milestone")
            if current_state not in {"IN_PROGRESS", "REVIEW_PENDING", "COMPLETE", "BLOCKED"}:
                failures.append("status manifest has an unsupported current_milestone_state")
            if manifest.get("safeForHonda") is not False:
                failures.append("status manifest must keep safeForHonda false")
            if current_id in milestone_by_id and milestone_by_id[current_id].get("state") != current_state:
                failures.append("current milestone state disagrees with its manifest entry")
            ordered_after_r0 = [f"CL-R{number}" for number in range(1, 9)]
            expected_next = next((mid for mid in ordered_after_r0
                                  if milestone_by_id.get(mid, {}).get("state") != "COMPLETE"), None)
            if manifest.get("next_technical_milestone") != expected_next:
                failures.append(f"next technical milestone must be {expected_next}")
            for item in milestones:
                if item.get("state") not in {"PLANNED", "IN_PROGRESS", "REVIEW_PENDING", "COMPLETE", "BLOCKED"}:
                    failures.append(f"unsupported state for milestone {item.get('id')}")
                for evidence in item.get("evidence", []):
                    if evidence not in paths:
                        failures.append(f"status manifest evidence path is missing: {evidence}")

    review_scope_file = "docs/status/cl-r0-review-scope.json"
    if review_scope_file in indexed:
        try:
            review_scope = indexed_json(review_scope_file, indexed)
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            failures.append(f"CL-R0 review scope is invalid JSON: {error}")
        else:
            if review_scope.get("approval_claimed") is not False:
                failures.append("CL-R0 review scope must not claim independent approval")
            if review_scope.get("review_status") != "PENDING_INDEPENDENT_ECC_REVIEW":
                failures.append("CL-R0 review scope status must remain pending until an independent review is recorded")
            for entry in review_scope.get("files", []):
                path = entry.get("path")
                if not isinstance(path, str) or path not in indexed:
                    failures.append(f"CL-R0 review scope file is missing: {path}")
                elif hashlib.sha256(indexed_blob(path)).hexdigest() != entry.get("sha256"):
                    failures.append(f"CL-R0 review scope hash mismatch: {path}")

    markdown = sorted(path for path in paths if path.lower().endswith(".md"))
    broken_links: list[tuple[str, str]] = []
    archived_untracked_references = 0
    for source in markdown:
        text = markdown_source(source)
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
    index_text = markdown_source(report_index) if report_index in paths else ""
    indexed_reports: set[str] = set()
    for match in LINK_RE.finditer(index_text):
        target = resolve_markdown_target(report_index, match.group(1))
        if target in reports:
            indexed_reports.add(target)
    for report in sorted(reports - indexed_reports):
        failures.append(f"step report missing from index: {report}")

    # Only indexed paths are part of the source publication candidate. Local
    # untracked artifacts remain visible in Git status and the final inventory,
    # but are not silently treated as reviewed public source inputs.
    forbidden = [
        path for path in sorted(paths)
        if path in indexed
        if any(path.lower().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)
    ]
    for path in forbidden:
        failures.append(f"forbidden binary/archive/capture extension: {path}")

    allowed_capture_notes = {
        "research/lab/captures/43p/oracle-events.redacted.jsonl",
        "research/lab/captures/43p/session-summary.json",
        "research/lab/captures/43p/session-metadata.md",
    }
    try:
        image_manifest = json.loads(indexed_blob("tools/repo_health_public_images.json"))
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError):
        image_manifest = {}
    for path in sorted(indexed):
        candidate = indexed_blob(path)
        if path.startswith("research/captures/") and not path.endswith(".md"):
            failures.append(f"non-text file under protected research/captures/: {path}")
        if path.startswith("research/lab/captures/") and path not in allowed_capture_notes:
            failures.append(f"unreviewed file under research/lab/captures/: {path}")
        if not is_health_exempt_image(path, candidate, manifest=image_manifest):
            if b"\0" in candidate[:8192]:
                failures.append(f"binary content is not allowed in tracked repository files: {path}")

    for source in STRICT_PUBLIC_DOCS:
        if source not in paths:
            continue
        text = markdown_source(source)
        if ABSOLUTE_PERSONAL_PATH_RE.search(text):
            failures.append(f"personal absolute path in visitor-facing document: {source}")
        if TOKEN_RE.search(text) or PRIVATE_KEY_RE.search(text) or VIN_RE.search(text):
            failures.append(f"credential, private-key marker, or VIN-like value in visitor-facing document: {source}")
    for source in LINK_CHECK_DOCS:
        if source not in paths:
            continue
        heading_count = len(re.findall(r"^#\s+", markdown_source(source), re.MULTILINE))
        if heading_count != 1:
            failures.append(f"visitor-facing document must have one H1 (found {heading_count}): {source}")

    print(
        f"Index-snapshot repository health: {len(markdown)} Markdown files, "
        f"{len(reports)} indexed milestone/support reports, "
        f"{len(broken_links)} broken links in curated docs, "
        f"{archived_untracked_references} historical/untracked references out of CI link scope, "
        f"{unindexed_count} unindexed local paths inventoried but excluded from the index-snapshot checks, "
        f"{unstaged_count} tracked unstaged paths excluded from the index-snapshot checks, "
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
