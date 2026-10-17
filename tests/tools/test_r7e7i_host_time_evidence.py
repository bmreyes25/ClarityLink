"""Protocol and uncertainty-policy tests for host-only time receipts."""
import hashlib
import json
from pathlib import Path
import struct

import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "r7e7i_host_time_evidence.py")

from tools import r7e7i_host_time_evidence as h


def packet_for(t1_ns, t2_offset=0.03, t3_offset=0.04, leap=0, mode=4,
               stratum=2, root_delay=0.01, root_dispersion=0.02):
    p = bytearray(48)
    p[0] = (leap << 6) | (4 << 3) | mode
    p[1] = stratum
    p[3] = (-20) & 0xff
    p[4:8] = struct.pack("!i", round(root_delay * 65536))
    p[8:12] = struct.pack("!I", round(root_dispersion * 65536))
    p[24:32] = h.to_ntp_timestamp(t1_ns)
    p[32:40] = h.to_ntp_timestamp(t1_ns + int(t2_offset * 1e9))
    p[40:48] = h.to_ntp_timestamp(t1_ns + int(t3_offset * 1e9))
    return bytes(p)


def parse(packet, t1_ns=1_800_000_000_000_000_000, t4_offset=0.08, rtt=0.08):
    request = h.to_ntp_timestamp(t1_ns)
    return h.parse_response(packet, request, t1_ns,
                            t1_ns + int(t4_offset * 1e9), int(rtt * 1e9),
                            {"hostname": "fixture.invalid", "resolved_address": "192.0.2.1"})


def test_valid_response_records_offset_root_metrics_and_conditional_bound():
    t1_ns = 1_800_000_000_000_000_000
    result = parse(packet_for(t1_ns), t1_ns=t1_ns)
    assert result["offset_server_minus_host_seconds"] == pytest.approx(-0.005, abs=0.0001)
    assert result["network_delay_estimate_seconds"] == pytest.approx(0.07, abs=0.0001)
    assert result["root_delay_seconds"] == pytest.approx(0.01, abs=0.0001)
    assert result["root_dispersion_seconds"] == pytest.approx(0.02, abs=0.0001)
    assert result["conditional_uncertainty_seconds"] >= 0.065
    assert result["authentication"] == "UNAUTHENTICATED_ORDINARY_NTP"


@pytest.mark.parametrize("kwargs", [
    {"leap": 3}, {"mode": 3}, {"stratum": 0}, {"stratum": 16},
])
def test_unsynchronized_or_wrong_mode_is_rejected(kwargs):
    t1 = 1_800_000_000_000_000_000
    with pytest.raises(h.EvidenceError):
        parse(packet_for(t1, **kwargs), t1_ns=t1)


def test_origin_timestamp_tamper_is_rejected():
    t1 = 1_800_000_000_000_000_000
    raw = bytearray(packet_for(t1))
    raw[24] ^= 1
    with pytest.raises(h.EvidenceError, match="origin timestamp"):
        parse(bytes(raw), t1_ns=t1)


def test_server_timestamps_outside_monotonic_round_trip_are_rejected():
    t1 = 1_800_000_000_000_000_000
    with pytest.raises(h.EvidenceError, match="monotonic round trip"):
        parse(packet_for(t1, t2_offset=1, t3_offset=2), t1_ns=t1, rtt=0.08)


def test_conflict_and_clock_step_remain_inconclusive():
    a = {"offset_server_minus_host_seconds": 0.0, "conditional_uncertainty_seconds": 0.1}
    b = {"offset_server_minus_host_seconds": 1.0, "conditional_uncertainty_seconds": 0.1}
    assert h.evaluate([a, b], [], False)["decision"] == "INCONCLUSIVE_CONFLICTING_MEASUREMENTS"
    assert h.evaluate([a], [], True)["decision"] == "INCONCLUSIVE_HOST_CLOCK_STEP"
    one = h.evaluate([a], [], False)
    assert one["decision"] == "CONDITIONAL_SINGLE_UNAUTHENTICATED_SOURCE"
    assert one["trusted_absolute_clock_bound_established"] is False


def test_collector_preserves_failures_and_cannot_claim_authenticated_bound(monkeypatch):
    calls = []
    def query(server):
        calls.append(server)
        if server == "bad.example":
            raise OSError("no route")
        return {"offset_server_minus_host_seconds": 0.01,
                "conditional_uncertainty_seconds": 0.1,
                "authentication": "UNAUTHENTICATED_ORDINARY_NTP"}
    monkeypatch.setattr(h, "collect_chrony_tracking", lambda: {"available": False, "status": "NOT_INSTALLED"})
    ticks = iter([1_000_000_000, 2_000_000_000])
    walls = iter([1_800_000_000_000_000_000, 1_800_000_001_000_000_000])
    result = h.collect(["a.example", "bad.example"], query, lambda: next(walls), lambda: next(ticks))
    assert calls == ["a.example", "bad.example"]
    assert result["source_failures"] == [{"server": "bad.example", "error_type": "OSError", "message": "no route"}]
    assert result["authenticated_time_source_available"] is False
    assert result["trusted_absolute_clock_bound_established"] is False


def test_evidence_save_is_private_and_hashes_raw_evidence(tmp_path):
    destination = tmp_path / "private" / "measurement.json"
    result = {"schema_version": "R7E7I-HOST-TIME-EVIDENCE-1", "samples": []}
    path, digest = h.save_private(result, destination)
    raw = path.read_bytes()
    saved = json.loads(raw)
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert saved["evidence_sha256"] == hashlib.sha256(
        json.dumps(result, sort_keys=True, indent=2).encode() + b"\n").hexdigest()
    assert digest == hashlib.sha256(raw).hexdigest()
