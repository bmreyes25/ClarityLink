import importlib.util
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("r7e_a0r", ROOT / "tools/r7e_a0r_collector.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class FakeAdb:
    def __init__(self, inventory="List of devices attached\nHONDA_SERIAL_123\tdevice\n",
                 uid="uid=2000(shell) gid=2000(shell) groups=1003(graphics)\n",
                 release="4.2.2\n", sdk="17\n", abi="armeabi-v7a\n",
                 mounts="rootfs / rootfs rw 0 0\n/dev/block/data /data ext4 rw,nosuid,nodev 0 0\n",
                 selinux="1\n", fail_id=False, fail_ls=False, timeout_at=None,
                 unavailable_tools=()):
        self.inventory, self.uid, self.release = inventory, uid, release
        self.sdk, self.abi, self.mounts, self.selinux = sdk, abi, mounts, selinux
        self.fail_id, self.fail_ls, self.timeout_at = fail_id, fail_ls, timeout_at
        self.unavailable_tools = set(unavailable_tools)
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs["timeout"] == collector.TIMEOUT_SECONDS
        if argv == ["adb", "devices"]:
            return subprocess.CompletedProcess(argv, 0, self.inventory, "")
        assert argv[:3] == ["adb", "-s", "HONDA_SERIAL_123"]
        operation = argv[3:]
        if self.timeout_at and operation == self.timeout_at:
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if self.fail_id and operation == ["shell", "id"]:
            return subprocess.CompletedProcess(argv, 1, "", "failed")
        if self.fail_ls and operation[:3] == ["shell", "ls", "-ld"]:
            return subprocess.CompletedProcess(argv, 127, "", "unknown option")
        if operation[:3] == ["shell", "ls", "-l"]:
            tool = operation[3].rsplit("/", 1)[-1]
            if tool in self.unavailable_tools:
                return subprocess.CompletedProcess(argv, 1, "", "No such file")
            return subprocess.CompletedProcess(argv, 0, f"-rwxr-xr-x root shell {tool}\n", "")
        outputs = {
            ("shell", "id"): self.uid,
            ("shell", "getprop", "ro.build.version.release"): self.release,
            ("shell", "getprop", "ro.build.version.sdk"): self.sdk,
            ("shell", "getprop", "ro.product.cpu.abi"): self.abi,
            ("shell", "pwd"): "/\n",
            ("shell", "ls", "-ld", "/data"): "drwxrwx--x root system /data\n",
            ("shell", "ls", "-ld", "/data/local"): "drwxrwx--x shell shell /data/local\n",
            ("shell", "ls", "-ld", "/data/local/tmp"): "drwxrwx--x shell shell /data/local/tmp\n",
            ("shell", "cat", "/proc/mounts"): self.mounts,
            ("shell", "cat", "/proc/self/status"): "Uid:\t2000\t2000\t2000\t2000\n",
            ("shell", "cat", "/sys/fs/selinux/enforce"): self.selinux,
        }
        if operation == ("shell", "cat", "/sys/fs/selinux/enforce") and self.selinux is None:
            return subprocess.CompletedProcess(argv, 1, "", "No such file")
        return subprocess.CompletedProcess(argv, 0, outputs[tuple(operation)], "")


def authorized_args(tmp_path, *extra):
    return ["--execute-authorized-a0-readonly", "--authorization-ref", "LOCAL-REF-1",
            "--observed-power-state", "Operator typed unknown state", "--audio-state-before",
            "NOT_RELEVANT", "--stationary",
            "--parked", "--center-display-booted", "--cluster-normal",
            "--no-unexpected-warnings", "--confirm-intended-honda-target",
            "--evidence-root", str(tmp_path), *extra]


def test_default_refusal_and_dry_run_make_zero_adb_calls(capsys, tmp_path):
    calls = []
    assert collector.main([], runner=lambda *a, **k: calls.append(a)) == 2
    assert "NOT_AUTHORIZED" in capsys.readouterr().err
    assert calls == []
    assert collector.main(["--dry-run"], runner=lambda *a, **k: calls.append(a)) == 0
    assert calls == []
    assert "TARGET_REDACTED" in capsys.readouterr().out


def test_one_target_pins_every_command_and_redacts_identity(tmp_path):
    fake = FakeAdb()
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
    assert len(fake.calls) == 18
    assert fake.calls[0] == ["adb", "devices"]
    assert all(call[1:3] == ["-s", "HONDA_SERIAL_123"] for call in fake.calls[1:])
    run_dir = next(tmp_path.iterdir())
    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["target_identity"] == "REDACTED"
    assert metadata["decision"] == "A0R_PASS_FOR_REVIEW"
    assert "HONDA_SERIAL_123" not in json.dumps(metadata)
    assert (run_dir / "target-identity.local.txt").read_text().strip() == "HONDA_SERIAL_123"
    assert metadata["data_mount"]["exec_observation"] == "NO_NOEXEC_FLAG_OBSERVED"


def test_zero_multi_offline_and_unauthorized_targets_run_no_shell(tmp_path):
    inventories = [
        "List of devices attached\n",
        "List of devices attached\na\tdevice\nb\tdevice\n",
        "List of devices attached\na\toffline\n",
        "List of devices attached\na\tunauthorized\n",
        "List of devices attached\na\tsideload\n",
    ]
    for index, inventory in enumerate(inventories):
        fake = FakeAdb(inventory=inventory)
        assert collector.main(authorized_args(tmp_path / str(index)), runner=fake,
                              input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
        assert len(fake.calls) == 1


def test_unexpected_uid_stops_before_platform_or_destination_queries(tmp_path):
    fake = FakeAdb(uid="uid=0(root) gid=0(root)\n")
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert len(fake.calls) == 2
    assert fake.calls[-1][3:] == ["shell", "id"]


def test_platform_mismatch_stops_before_pwd_and_destination_queries(tmp_path):
    fake = FakeAdb(sdk="19\n")
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert [call[3:] for call in fake.calls[1:]] == [
        ["shell", "id"], ["shell", "getprop", "ro.build.version.release"],
        ["shell", "getprop", "ro.build.version.sdk"],
        ["shell", "getprop", "ro.product.cpu.abi"],
    ]
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["decision"] == "A0R_BLOCKED_PLATFORM_MISMATCH"


def test_wrong_abi_stops_before_destination_queries(tmp_path):
    fake = FakeAdb(abi="x86\n")
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert len(fake.calls) == 5
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["decision"] == "A0R_BLOCKED_PLATFORM_MISMATCH"


def test_noexec_classification_and_no_promotion(tmp_path):
    mounts = "dev /data ext4 rw,noexec,nosuid,nodev 0 0\n"
    fake = FakeAdb(mounts=mounts)
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert fake.calls[-1][3:] == ["shell", "cat", "/proc/mounts"]
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["decision"] == "A0R_BLOCKED_NOEXEC"


def test_rw_and_ro_mount_flags_are_reported_and_noexec_absence_is_bounded(tmp_path):
    fake = FakeAdb(mounts="dev /data ext4 ro,nosuid,nodev 0 0\n", selinux="0\n")
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["data_mount"]["ro"] is True
    assert meta["data_mount"]["rw"] is False
    assert meta["data_mount"]["noexec"] is False
    assert meta["data_mount"]["exec_observation"] == "NO_NOEXEC_FLAG_OBSERVED"
    assert meta["selinux_state"] == "0"


def test_selinux_unavailable_is_not_disabled_and_has_no_fallback(tmp_path):
    fake = FakeAdb(selinux=None)
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
    calls = [call[3:] for call in fake.calls[1:]]
    assert ["shell", "cat", "/sys/fs/selinux/enforce"] in calls
    assert not any("getenforce" in call for call in calls)
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["decision"] == "A0R_PASS_FOR_REVIEW"
    assert meta["selinux_state"] == "SELINUX_STATE_UNAVAILABLE"


def test_ls_ld_failure_stops_without_stat_or_toolbox_fallback(tmp_path):
    fake = FakeAdb(fail_ls=True)
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    calls = [call[3:] for call in fake.calls[1:]]
    assert calls[-1] == ["shell", "ls", "-ld", "/data"]
    assert not any(call[1:2] in (["stat"], ["busybox"], ["toybox"]) for call in calls)
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["command_records"][-1]["classification"] == "LS_LD_UNAVAILABLE"


def test_command_failure_and_timeout_stop_without_retry(tmp_path):
    fake = FakeAdb(timeout_at=["shell", "id"])
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert len(fake.calls) == 2
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["command_records"][-1]["exit_status"] == "TIMEOUT"


def test_failed_identity_command_stops_without_retry_or_fallback(tmp_path):
    fake = FakeAdb(fail_id=True)
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert len(fake.calls) == 2
    assert fake.calls[-1][3:] == ["shell", "id"]


def test_manifest_templates_contain_no_mutating_operations():
    manifest = json.loads((ROOT / "research/runtime/r7e3-a0r-plan-manifest.json").read_text())
    import hashlib
    assert manifest["collector_source_sha256"] == hashlib.sha256(
        (ROOT / manifest["collector_source"]).read_bytes()).hexdigest()
    prohibited = {"push", "install", "touch", "mkdir", "dd", "mount",
                  "remount", "setprop", "su", "reboot", "stat", "getenforce"}
    for item in manifest["commands"]:
        argv = item["argv"]
        assert not prohibited.intersection(argv)
        # rm/ps/kill/md5/chmod may appear only as literal metadata operands to ls -l.
        if any(argv[-1].endswith("/system/bin/" + x)
               for x in {"rm", "ps", "kill", "md5", "chmod", "toolbox"}):
            assert argv[:3] == ["shell", "ls", "-l"]
    assert not any("shell" in item["argv"] and "-c" in item["argv"] for item in manifest["commands"])


def test_a0w_and_test_a_never_auto_chain(tmp_path):
    fake = FakeAdb()
    collector.main(authorized_args(tmp_path), runner=fake, input_fn=lambda _: "STOCK_STATE_UNCHANGED")
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["a0w"].startswith("WRITE_DELETE_EVIDENCE_STILL_REQUIRED")
    assert meta["test_a"] == "NOT_AUTHORIZED"
    assert not any("push" in call or "chmod" in call for call in fake.calls)


def test_each_future_tool_absence_is_informational_and_never_executed(tmp_path):
    tools = {"toolbox", "rm", "ps", "kill", "md5", "chmod"}
    for tool in tools:
        fake = FakeAdb(unavailable_tools={tool})
        out = tmp_path / tool
        assert collector.main(authorized_args(out), runner=fake,
                              input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
        meta = json.loads(next(out.iterdir()).joinpath("metadata.json").read_text())
        assert meta["decision"] == "A0R_PASS_FOR_REVIEW"
        assert meta["future_tool_availability"][tool] == f"{tool.upper()}_UNAVAILABLE"
        blockers = meta.get("future_plan_review_blockers", [])
        assert bool(blockers) is (tool in {"rm", "ps", "kill"})
        assert all(call[3:5] == ["shell", "ls"] for call in fake.calls[12:])


def test_future_tool_metadata_checks_use_only_fixed_ls_l(tmp_path):
    fake = FakeAdb()
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
    tail = [call[3:] for call in fake.calls[12:]]
    assert tail == [["shell", "ls", "-l", f"/system/bin/{name}"]
                    for name in ("toolbox", "rm", "ps", "kill", "md5", "chmod")]
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["future_tool_availability"] == {
        "toolbox": "TOOLBOX_PRESENT", "rm": "RM_PRESENT", "ps": "PS_PRESENT",
        "kill": "KILL_PRESENT", "md5": "MD5_PRESENT", "chmod": "CHMOD_PRESENT",
    }


def test_stock_state_change_is_recorded_as_stop_condition(tmp_path):
    fake = FakeAdb()
    assert collector.main(authorized_args(tmp_path), runner=fake,
                          input_fn=lambda _: "Unexpected warning appeared") == 1
    meta = json.loads(next(tmp_path.iterdir()).joinpath("metadata.json").read_text())
    assert meta["decision"] == "A0R_STOP_CONDITION"
    assert meta["operator_confirmations_after"]["stock_state_observation_exact"] == "Unexpected warning appeared"
