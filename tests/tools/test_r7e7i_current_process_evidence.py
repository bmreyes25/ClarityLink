import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[2] / "tools" / "r7e7i_current_process_evidence.py"
spec = importlib.util.spec_from_file_location("r7e7i_current_process_evidence", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)


def evidence():
    proc = {"pid": 42, "starttime_ticks": 100, "state": "S",
            "exe": {"identity": {"device": "08:01", "inode": 77}, "path": mod.TARGET},
            "maps": [], "fds": []}
    return {"schema_version": "R7E7I-CURRENT-PROCESS-EVIDENCE-1",
            "source_kind": "SYNTHETIC_FIXTURE", "evidence_id": "fixture",
            "receipts": [{"name": "fixture", "sha256": "a" * 64}],
            "target_path": mod.TARGET,
            "target_identity_before": {"device": "08:01", "inode": 77},
            "target_identity_after": {"device": "08:01", "inode": 77},
            "target_file_type": "REGULAR", "boot_id_before": "boot", "boot_id_after": "boot",
            "processes_before": [{"pid": 42, "starttime_ticks": 100}],
            "processes_after": [proc], "proc_visibility": "COMPLETE", "enumerated_count": 1,
            "unreadable_processes": [], "readlink_available": True, "maps_available": True,
            "fd_directory_covered": True, "relaunch_audit": "NONE_REVIEWED"}


def decision(data):
    out = mod.classify(data)
    assert out["cleanup_authorized"] is False
    assert out["test_a_authorized"] is False
    assert out["future_launch_exclusion"] == "NOT_PROVEN_BY_SNAPSHOT"
    return out["decision"]


def test_exact_device_inode_reference_detected():
    assert decision(evidence()) == "MODEL_ONLY_CURRENT_REFERENCES_PRESENT"


def test_no_current_reference_is_still_not_future_launch_proof():
    data = evidence()
    data["processes_after"][0]["exe"] = {"identity": {"device": "08:01", "inode": 88}, "path": "/different"}
    assert decision(data) == "MODEL_ONLY_CURRENT_REFERENCES_ABSENT_WITH_COMPLETE_VISIBILITY"


@pytest.mark.parametrize("mutator,expected", [
    (lambda d: d["processes_after"][0]["maps"].append({"identity": {"device": "08:01", "inode": 77}, "path": mod.TARGET + " (deleted)"}), "MODEL_ONLY_CURRENT_REFERENCES_PRESENT"),
    (lambda d: d["processes_after"][0]["fds"].append({"identity": {"device": "08:01", "inode": 77}, "path": mod.TARGET}), "MODEL_ONLY_CURRENT_REFERENCES_PRESENT"),
    (lambda d: d["processes_after"][0].update(starttime_ticks=101), "MODEL_ONLY_PID_REUSE_OR_PROCESS_REPLACED"),
    (lambda d: d.update(proc_visibility="PARTIAL"), "MODEL_ONLY_VISIBILITY_INCOMPLETE"),
    (lambda d: d.update(readlink_available=False), "MODEL_ONLY_REQUIRED_PROC_FIELD_UNAVAILABLE"),
    (lambda d: (d["processes_after"][0].update(exe={"identity": {"device": "08:01", "inode": 88}, "path": "/other"}), d.update(relaunch_audit="UNKNOWN")), "MODEL_ONLY_RELAUNCH_RISK_UNKNOWN"),
    (lambda d: (d["processes_after"][0].update(exe={"identity": {"device": "08:01", "inode": 88}, "path": "/other"}), d.update(relaunch_audit="PRESENT")), "MODEL_ONLY_RELAUNCH_SOURCE_PRESENT"),
    (lambda d: d.update(boot_id_after="newboot"), "MODEL_ONLY_BOOT_OR_SNAPSHOT_CONFLICT"),
])
def test_fail_closed_cases(mutator, expected):
    data = evidence()
    mutator(data)
    assert decision(data) == expected


def test_zombie_has_no_address_space_reference_but_is_not_silently_ignored():
    data = evidence()
    data["processes_after"][0].update(state="Z", exe=None)
    assert decision(data) == "MODEL_ONLY_ZOMBIE_PROCESS_PRESENT"


def test_live_process_with_unreadable_exe_is_inconclusive():
    data = evidence()
    data["processes_after"][0]["exe"] = None
    assert decision(data) == "MODEL_ONLY_REQUIRED_PROC_FIELD_UNAVAILABLE"


def test_same_path_but_different_inode_is_reported_not_matched():
    data = evidence()
    data["processes_after"][0]["exe"]["identity"]["inode"] = 999
    out = mod.classify(data)
    assert out["decision"] == "MODEL_ONLY_CURRENT_REFERENCES_ABSENT_WITH_COMPLETE_VISIBILITY"
    assert out["same_basename_different_inode"] == [42]


def test_malformed_map_row_is_not_silently_ignored():
    data = evidence()
    data["processes_after"][0]["maps"] = ["garbage"]
    assert decision(data) == "MODEL_ONLY_MALFORMED_PROCESS_RECORD"


def test_proc_stat_handles_parentheses_in_comm():
    # fields 3..22: state then 18 intervening numeric values then starttime.
    raw = "42 (test ) process) S " + " ".join(["0"] * 18 + ["987"])
    assert mod.parse_proc_stat(raw) == {"pid": 42, "state": "S", "starttime_ticks": 987}


def test_map_parser_preserves_device_inode_and_deleted_path():
    row = mod.parse_maps("1000-2000 r-xp 00000000 08:01 77 " + mod.TARGET + " (deleted)")[0]
    assert (row["device"], row["inode"]) == ("08:01", 77)
    assert row["path"] == mod.TARGET + " (deleted)"
