"""Mac-side 43T0-D collector. Default is a non-executing dry run.

The execution branch is for a separately initiated, reviewed 43T0-D session.
Never run that branch during 43T0-D0.
"""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import selectors
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol


VERSION = "43T0-D0-3"
ADB_TOKEN = "adb"
CURRENT_TARGET = "<validated-current-target>"
MANIFEST_SHA256 = "248427ae4d5dc7ce75888425ab254d308c68e6021a3032a62877c92ef3811f77"
EXPECTED_ADB_PATH = Path("/opt/homebrew/bin/adb")
EXPECTED_ADB_SHA256 = "1811e253b21b12cbfda7201ebaf86c10e7ddcb5c606a7a81f7c82b4c429c2d3b"
APPROVED_PLAN_SHA256 = "0dc6bf88c3c51d7bed3088f811ecf0e1802a8b4ae4722ca25114ef87c0dfec01"
D3_PLAN_SHA256 = "68ec3ccd3ff69d533bdee3d3d38dc2df389015ba960e9effa10450776f68647f"
SHELL_ID_SHA256 = "590cc36f1a98082e64e0e2d836c94c125bef1c73fcb7daf981b7286c6b310992"
KERNEL_SHA256 = "8fa1c06d864d3dab9be4c53c13ddecb421516bd02ace3a27ef7811a7ee79c451"
PROPERTIES = (
    ("ro.build.version.release", "4.2.2", "release.raw"),
    ("ro.build.version.sdk", "17", "sdk.raw"),
    ("ro.product.device", "vcm30t30a", "device.raw"),
    ("ro.product.board", "Andromeda", "board.raw"),
    ("ro.hardware", "vcm30t30", "hardware.raw"),
)
PHASES = ("baseline", "connected", "post-disconnect")
TIMEOUT_SECONDS = 5
OUTPUT_CAP = 65536
IDENTITY = (
    ("id", ("shell", "id"), "id.raw"),
    ("kernel", ("shell", "cat", "/proc/version"), "proc-version.raw"),
    ("ro.build.version.release", ("shell", "getprop", "ro.build.version.release"), "release.raw"),
    ("ro.build.version.sdk", ("shell", "getprop", "ro.build.version.sdk"), "sdk.raw"),
    ("ro.product.device", ("shell", "getprop", "ro.product.device"), "device.raw"),
    ("ro.product.board", ("shell", "getprop", "ro.product.board"), "board.raw"),
    ("ro.hardware", ("shell", "getprop", "ro.hardware"), "hardware.raw"),
)
NETWORK = (
    (("shell", "cat", "/proc/net/dev"), "net-dev.raw"),
    (("shell", "cat", "/proc/net/route"), "net-route.raw"),
    (("shell", "cat", "/proc/net/ipv6_route"), "ipv6-route.raw"),
    (("shell", "cat", "/proc/net/if_inet6"), "if-inet6.raw"),
    (("shell", "netcfg"), "netcfg.raw"),
)
ALLOWED_SUFFIXES = frozenset((suffix for _key, suffix, _name in IDENTITY)) | frozenset(
    suffix for suffix, _name in NETWORK
)
RESULT_CLASSES = frozenset({
    "SUCCESS", "COMMAND_UNAVAILABLE", "PERMISSION_DENIED", "TIMEOUT",
    "OUTPUT_LIMIT_EXCEEDED", "UNEXPECTED_FORMAT", "ADB_TRANSPORT_FAILURE",
    "IDENTITY_MISMATCH", "IDENTITY_INCOMPLETE", "AMBIGUOUS_ADB_TARGET",
    "UNEXPECTED_PRIVILEGE", "USER_ABORT", "STOCK_SANITY_FAILURE",
})
ENDPOINT_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
NETCFG_LINE_RE = re.compile(
    r"(?P<iface>[A-Za-z0-9_.-]{1,15})\s+(?P<state>UP|DOWN)\s+"
    r"(?P<address>(?:[0-9]{1,3}\.){3}[0-9]{1,3})/(?P<prefix>[0-9]{1,2})\s+"
    r"0x(?P<flags>[0-9a-fA-F]{8})(?:\s+(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})?"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_approved_plan() -> None:
    source = Path(__file__).with_name("step43t0c_identity_delta_dry_run.py")
    if hashlib.sha256(source.read_bytes()).hexdigest() != APPROVED_PLAN_SHA256:
        raise ValueError("approved 43T0-C plan source changed")
    revised = Path(__file__).with_name("step43t0d3_netcfg_plan.py")
    if hashlib.sha256(revised.read_bytes()).hexdigest() != D3_PLAN_SHA256:
        raise ValueError("approved D3 netcfg plan source changed")


def read_git_commit(repo_root: Path) -> str:
    git_dir = repo_root / ".git"
    if git_dir.is_file():
        marker = git_dir.read_text().strip()
        if not marker.startswith("gitdir: "):
            raise ValueError("invalid Git directory marker")
        git_dir = (repo_root / marker[8:]).resolve()
    common_dir = git_dir
    commondir = git_dir / "commondir"
    if commondir.exists():
        common_dir = (git_dir / commondir.read_text().strip()).resolve()
    head = (git_dir / "HEAD").read_text().strip()
    if head.startswith("ref: "):
        ref = head[5:]
        if not re.fullmatch(r"refs/[A-Za-z0-9_./-]+", ref) or ".." in ref:
            raise ValueError("invalid Git ref")
        loose = next((path for path in (git_dir / ref, common_dir / ref) if path.exists()), None)
        if loose is not None:
            head = loose.read_text().strip()
        else:
            packed_refs = common_dir / "packed-refs"
            packed = packed_refs.read_text().splitlines() if packed_refs.exists() else []
            matches = [line.split()[0] for line in packed if line.endswith(" " + ref)]
            if len(matches) != 1:
                raise ValueError("Git ref unavailable")
            head = matches[0]
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("invalid Git commit")
    return head


@dataclass(frozen=True)
class CommandResult:
    status: str
    stdout: bytes = b""
    stderr: bytes = b""
    returncode: int | None = None
    started_utc: str = ""
    finished_utc: str = ""


@dataclass(frozen=True)
class IdentityDecision:
    state: str
    reason: str


def assess_identity(targets: list[tuple[str, str]], human_confirmed: bool,
                    historical_endpoint: str, results: dict[str, str]) -> IdentityDecision:
    if not human_confirmed or len(targets) != 1 or targets[0][1] != "device":
        return IdentityDecision("IDENTITY_INCOMPLETE", "human or target gate incomplete")
    if targets[0][0] != historical_endpoint:
        return IdentityDecision("IDENTITY_MISMATCH", "CURRENT_ENDPOINT_DIFFERS_FROM_40E")
    keys = ("id", "kernel", *(key for key, _expected, _name in PROPERTIES))
    if any(key not in results or not results[key].rstrip("\r\n") for key in keys):
        return IdentityDecision("IDENTITY_INCOMPLETE", "missing identity result")
    shell_id = results["id"].rstrip("\r\n")
    if not re.match(r"^uid=2000\(shell\)\s+gid=2000\(shell\)(?:\s|$)", shell_id):
        return IdentityDecision("IDENTITY_MISMATCH", "UNEXPECTED_PRIVILEGE")
    if hashlib.sha256(shell_id.encode()).hexdigest() != SHELL_ID_SHA256:
        return IdentityDecision("IDENTITY_MISMATCH", "shell group fingerprint mismatch")
    if hashlib.sha256(results["kernel"].rstrip("\r\n").encode()).hexdigest() != KERNEL_SHA256:
        return IdentityDecision("IDENTITY_MISMATCH", "kernel fingerprint mismatch")
    for key, expected, _name in PROPERTIES:
        if results[key].rstrip("\r\n") != expected:
            return IdentityDecision("IDENTITY_MISMATCH", "property mismatch: " + key)
    return IdentityDecision("IDENTITY_MATCH", "all fixed checks matched")


class Runner(Protocol):
    def run(self, argv: tuple[str, ...], timeout: int, cap: int) -> CommandResult: ...


class BoundedRunner:
    """Read pipes incrementally; kill at deadline or combined byte limit."""

    def __init__(self, executable: str | None = None):
        self.executable = executable

    def run(self, argv: tuple[str, ...], timeout: int, cap: int) -> CommandResult:
        started = utc_now()
        try:
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, shell=False, close_fds=True,
                                    executable=self.executable)
        except FileNotFoundError:
            return CommandResult("COMMAND_UNAVAILABLE", started_utc=started, finished_utc=utc_now())
        except PermissionError:
            return CommandResult("PERMISSION_DENIED", started_utc=started, finished_utc=utc_now())
        except OSError:
            return CommandResult("ADB_TRANSPORT_FAILURE", started_utc=started, finished_utc=utc_now())
        selector = selectors.DefaultSelector()
        stdout = bytearray()
        stderr = bytearray()
        deadline = time.monotonic() + timeout
        status = "SUCCESS"
        try:
            assert proc.stdout and proc.stderr
            selector.register(proc.stdout, selectors.EVENT_READ, stdout)
            selector.register(proc.stderr, selectors.EVENT_READ, stderr)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "TIMEOUT"
                    break
                for key, _mask in selector.select(min(remaining, 0.05)):
                    chunk = os.read(key.fd, min(4096, cap - len(stdout) - len(stderr) + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    available = cap - len(stdout) - len(stderr)
                    key.data.extend(chunk[:available])
                    if len(chunk) > available:
                        status = "OUTPUT_LIMIT_EXCEEDED"
                        break
                if status != "SUCCESS":
                    break
            if status != "SUCCESS":
                proc.kill()
            try:
                proc.wait(timeout=max(0.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                status = "TIMEOUT"
            if status == "SUCCESS":
                status = classify_process_result(proc.returncode, bytes(stdout), bytes(stderr))
            return CommandResult(status, bytes(stdout), bytes(stderr), proc.returncode,
                                 started, utc_now())
        finally:
            selector.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc.stdout:
                proc.stdout.close()
            if proc.stderr:
                proc.stderr.close()


def classify_process_result(code: int | None, stdout: bytes, stderr: bytes) -> str:
    combined = (stdout + b"\n" + stderr).lower()
    if b"permission denied" in combined:
        return "PERMISSION_DENIED"
    if b"not found" in combined or b"no such file" in combined:
        return "COMMAND_UNAVAILABLE"
    if b"offline" in combined or b"unauthorized" in combined or b"no devices" in combined:
        return "ADB_TRANSPORT_FAILURE"
    if code != 0 or stderr:
        return "ADB_TRANSPORT_FAILURE"
    return "SUCCESS"


def parse_devices(raw: bytes) -> list[tuple[str, str]]:
    lines = raw.decode("utf-8", "strict").splitlines()
    if not lines or lines[0].strip() != "List of devices attached":
        raise ValueError("unexpected adb devices header")
    targets = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 2 or not ENDPOINT_RE.fullmatch(parts[0]):
            raise ValueError("unexpected adb devices row")
        targets.append((parts[0], parts[1]))
    return targets


def classify_format(suffix: tuple[str, ...], raw: bytes) -> str:
    try:
        text = raw.decode("utf-8", "strict").strip()
    except UnicodeError:
        return "UNEXPECTED_FORMAT"
    if suffix == ("shell", "cat", "/proc/net/dev"):
        lines = text.splitlines()
        if len(lines) < 3 or "|" not in lines[0] or "|" not in lines[1]:
            return "UNEXPECTED_FORMAT"
        rows = [line.rsplit(":", 1) for line in lines[2:]]
        if not rows or any(len(row) != 2 or len(row[1].split()) < 16 or
                           not all(v.isdecimal() for v in row[1].split()[:16]) for row in rows):
            return "UNEXPECTED_FORMAT"
    elif suffix == ("shell", "cat", "/proc/net/route"):
        lines = text.splitlines()
        if not lines or lines[0].split() != ["Iface", "Destination", "Gateway", "Flags", "RefCnt", "Use", "Metric", "Mask", "MTU", "Window", "IRTT"]:
            return "UNEXPECTED_FORMAT"
        for line in lines[1:]:
            fields = line.split()
            if len(fields) < 11 or any(not re.fullmatch(r"[0-9a-fA-F]{8}", fields[i]) for i in (1, 2, 7)):
                return "UNEXPECTED_FORMAT"
    elif suffix == ("shell", "cat", "/proc/net/ipv6_route"):
        for line in text.splitlines():
            fields = line.split()
            if len(fields) != 10 or [len(v) for v in fields[:9]] != [32, 2, 32, 2, 32, 8, 8, 8, 8]:
                return "UNEXPECTED_FORMAT"
            if any(not re.fullmatch(r"[0-9a-fA-F]+", v) for v in fields[:9]):
                return "UNEXPECTED_FORMAT"
    elif suffix == ("shell", "cat", "/proc/net/if_inet6"):
        for line in text.splitlines():
            fields = line.split()
            if len(fields) != 6 or [len(v) for v in fields[:5]] != [32, 2, 2, 2, 2]:
                return "UNEXPECTED_FORMAT"
            if any(not re.fullmatch(r"[0-9a-fA-F]+", v) for v in fields[:5]):
                return "UNEXPECTED_FORMAT"
    elif suffix == ("shell", "netcfg"):
        lines = text.splitlines()
        if not lines or len(lines) > 4096:
            return "UNEXPECTED_FORMAT"
        seen = set()
        for line in lines:
            match = NETCFG_LINE_RE.fullmatch(line.strip())
            if not match or match["iface"] in seen or int(match["prefix"]) > 32:
                return "UNEXPECTED_FORMAT"
            seen.add(match["iface"])
            try:
                ipaddress.IPv4Address(match["address"])
            except ipaddress.AddressValueError:
                return "UNEXPECTED_FORMAT"
            if (int(match["flags"], 16) & 1 != 0) != (match["state"] == "UP"):
                return "UNEXPECTED_FORMAT"
    return "SUCCESS"


def dry_run_plan(host_output: Path) -> list[dict[str, object]]:
    """Independent executable-collector plan; tests compare it to 43T0-C."""
    rows: list[dict[str, object]] = [
        {"step": "enumerate", "argv": ["adb", "devices"],
         "require": "exactly one intended target in device state; no auto-selection",
         "timeout_seconds": 5, "max_output_bytes": 65536},
        {"step": "human_confirmation", "require": "parked intended Honda head unit"},
    ]
    expectations = (
        "uid=2000(shell), gid=2000(shell); sha256:" + SHELL_ID_SHA256,
        "sha256:" + KERNEL_SHA256,
        *(expected for _key, expected, _name in PROPERTIES),
    )
    for (key, suffix, filename), expected in zip(IDENTITY, expectations, strict=True):
        rows.append({"step": "identity", "key": key,
                     "argv": ["adb", "-s", CURRENT_TARGET, *suffix],
                     "expect": expected, "host_output": str(host_output / "identity" / filename),
                     "timeout_seconds": 5, "max_output_bytes": 65536})
    rows.append({"step": "gate", "require": "IDENTITY_MATCH before any network read; endpoint equal to 40E; stop otherwise"})
    rows.append({"step": "host_capture", "manifest": str(host_output / "manifest.json"),
                 "directory_mode": "0700", "location": "Mac only, outside Git"})
    for phase in PHASES:
        for suffix, filename in NETWORK:
            rows.append({"step": "network", "phase": phase, "only_if": "IDENTITY_MATCH",
                         "argv": ["adb", "-s", CURRENT_TARGET, *suffix],
                         "host_output": str(host_output / phase / filename),
                         "timeout_seconds": 5, "max_output_bytes": 65536})
    return rows


class CaptureStore:
    def __init__(self, root: Path, repo_root: Path):
        self.root = root.expanduser().resolve()
        self.project_commit = read_git_commit(repo_root)
        self.collector_source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if self.root.is_relative_to(repo_root.resolve()) or self.root.exists():
            raise ValueError("output must be a new directory outside Git")
        self.root.mkdir(mode=0o700, parents=False)
        os.chmod(self.root, 0o700)
        self.records: list[dict[str, object]] = []
        self.started_utc = utc_now()

    def _write(self, relative: str, data: bytes) -> None:
        path = self.root / relative
        path.parent.mkdir(mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)

    def record(self, phase: str, index: int, argv: tuple[str, ...], result: CommandResult,
               relative: str) -> None:
        self._write(relative, result.stdout)
        if result.stderr:
            self._write(relative + ".stderr.raw", result.stderr)
        self.records.append({
            "phase": phase, "command_index": index, "argv": list(argv),
            "target_reference": "redacted", "started_utc": result.started_utc,
            "finished_utc": result.finished_utc, "result_class": result.status,
            "return_status": result.returncode, "stdout_bytes": len(result.stdout),
            "stderr_bytes": len(result.stderr),
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
        })
        self.flush()

    def flush(self, final_status: str | None = None) -> None:
        data = {"collector_version": VERSION, "approved_plan_commit": "fdb3da178febc2df88947d5f73f4c630f46fdc1d",
                "revised_plan_sha256": D3_PLAN_SHA256,
                "project_commit": self.project_commit,
                "collector_source_sha256": self.collector_source_sha256,
                "started_utc": self.started_utc, "updated_utc": utc_now(),
                "finished_utc": utc_now() if final_status is not None else None,
                "final_status": final_status, "commands": self.records}
        temporary = self.root / ".manifest.tmp"
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
        os.replace(temporary, self.root / "manifest.json")


def read_historical_endpoint(manifest: Path) -> str:
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MANIFEST_SHA256:
        raise ValueError("historical 40E manifest checksum mismatch")
    endpoint = json.loads(raw)["adb_serial"]
    if not isinstance(endpoint, str) or not ENDPOINT_RE.fullmatch(endpoint):
        raise ValueError("invalid historical endpoint")
    return endpoint


def validate_adb_binary(path: Path) -> str:
    if path != EXPECTED_ADB_PATH or not path.is_file() or not os.access(path, os.X_OK):
        raise ValueError("ADB path differs from reviewed host binary")
    resolved = path.resolve(strict=True)
    if resolved.name != "adb" or hashlib.sha256(resolved.read_bytes()).hexdigest() != EXPECTED_ADB_SHA256:
        raise ValueError("ADB binary checksum differs from reviewed host binary")
    return str(resolved)


def allowed_argv(argv: tuple[str, ...], endpoint: str | None) -> bool:
    if argv == (ADB_TOKEN, "devices"):
        return True
    return bool(endpoint and ENDPOINT_RE.fullmatch(endpoint) and len(argv) >= 5 and
                argv[:3] == (ADB_TOKEN, "-s", endpoint) and argv[3:] in ALLOWED_SUFFIXES)


class StopCollection(Exception):
    def __init__(self, status: str):
        self.status = status
        super().__init__(status)


def collect(runner: Runner, confirm: Callable[[str], bool], store: CaptureStore,
            historical_endpoint: str) -> str:
    """Execute only the approved procedure; runner/confirm are injectable for offline tests."""
    index = 0
    endpoint: str | None = None

    def issue(phase: str, suffix: tuple[str, ...], relative: str) -> bytes:
        nonlocal index
        argv = (ADB_TOKEN, "devices") if suffix == ("devices",) else (ADB_TOKEN, "-s", endpoint or "", *suffix)
        if not allowed_argv(argv, endpoint):
            raise StopCollection("UNEXPECTED_FORMAT")
        result = runner.run(argv, TIMEOUT_SECONDS, OUTPUT_CAP)
        index += 1
        store.record(phase, index, argv, result, relative)
        if result.status != "SUCCESS":
            raise StopCollection(result.status)
        return result.stdout

    try:
        verify_approved_plan()
    except ValueError:
        store.flush("UNEXPECTED_FORMAT")
        return "UNEXPECTED_FORMAT"
    try:
        raw = issue("preflight", ("devices",), "preflight/devices.raw")
        try:
            targets = parse_devices(raw)
        except (ValueError, UnicodeError):
            raise StopCollection("AMBIGUOUS_ADB_TARGET") from None
        if len(targets) != 1 or targets[0][1] != "device":
            raise StopCollection("AMBIGUOUS_ADB_TARGET")
        endpoint = targets[0][0]
        if not confirm("parked_honda"):
            raise StopCollection("USER_ABORT")
        if endpoint != historical_endpoint:
            raise StopCollection("IDENTITY_MISMATCH")
        identity: dict[str, str] = {}
        for key, suffix, filename in IDENTITY:
            raw = issue("identity", suffix, "identity/" + filename)
            try:
                identity[key] = raw.decode("utf-8", "strict")
            except UnicodeError:
                raise StopCollection("IDENTITY_INCOMPLETE") from None
            if key == "id" and not identity[key].startswith("uid=2000(shell) gid=2000(shell)"):
                raise StopCollection("UNEXPECTED_PRIVILEGE")
        decision = assess_identity(targets, True, historical_endpoint, identity)
        if decision.state != "IDENTITY_MATCH":
            raise StopCollection("UNEXPECTED_PRIVILEGE" if decision.reason == "UNEXPECTED_PRIVILEGE" else decision.state)
        if not confirm("baseline_disconnected"):
            raise StopCollection("USER_ABORT")
        for phase in PHASES:
            if phase == "connected" and not confirm("connected_stock_center_audio_cluster_normal"):
                raise StopCollection("STOCK_SANITY_FAILURE")
            if phase == "post-disconnect" and not confirm("disconnected_stock_center_audio_cluster_normal"):
                raise StopCollection("STOCK_SANITY_FAILURE")
            for suffix, filename in NETWORK:
                raw = issue(phase, suffix, phase + "/" + filename)
                if classify_format(suffix, raw) != "SUCCESS":
                    store.records[-1]["result_class"] = "UNEXPECTED_FORMAT"
                    store.flush()
                    raise StopCollection("UNEXPECTED_FORMAT")
        if not confirm("final_stock_center_audio_cluster_normal"):
            raise StopCollection("STOCK_SANITY_FAILURE")
        store.flush("SUCCESS")
        return "SUCCESS"
    except StopCollection as failure:
        store.flush(failure.status)
        return failure.status


def interactive_confirm(key: str) -> bool:
    prompts = {
        "parked_honda": "Confirm this is the parked Honda head unit intended for the test",
        "baseline_disconnected": "Confirm iPhone CarPlay is disconnected for baseline",
        "connected_stock_center_audio_cluster_normal": "Connect normal wired CarPlay; confirm center, audio and stock cluster are normal",
        "disconnected_stock_center_audio_cluster_normal": "Disconnect CarPlay; confirm stock center, audio and cluster have returned normally",
        "final_stock_center_audio_cluster_normal": "Confirm final center system, audio and cluster are normal",
    }
    try:
        return input(prompts[key] + ". Type CONFIRM: ").strip() == "CONFIRM"
    except (EOFError, KeyboardInterrupt):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-output", type=Path, required=True)
    parser.add_argument("--execute-approved-43t0-delta", action="store_true")
    parser.add_argument("--adb-path", type=Path)
    parser.add_argument("--historical-manifest", type=Path)
    args = parser.parse_args()
    if args.host_output.expanduser().resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("host output must be outside the repository")
    if not args.execute_approved_43t0_delta:
        verify_approved_plan()
        for row in dry_run_plan(args.host_output):
            print(json.dumps(row, sort_keys=True))
        return
    if args.adb_path is None or args.historical_manifest is None:
        parser.error("execution requires explicit --adb-path and --historical-manifest")
    try:
        adb = validate_adb_binary(args.adb_path)
    except ValueError as error:
        parser.error(str(error))
    historical = read_historical_endpoint(args.historical_manifest)
    store = CaptureStore(args.host_output, Path(__file__).resolve().parents[1])
    status = collect(BoundedRunner(adb), interactive_confirm, store, historical)
    print(status)
    if status != "SUCCESS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
