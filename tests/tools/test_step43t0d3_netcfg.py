"""Offline D3 observer, versioned capture, and privacy regression tests."""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import analyze_43t0d_capture as analyzer
import step43t0d_offline as offline
import step43t0d3_static_review as static
import step43t0d0_collector as collector


def netcfg(name="cp0", state="UP", address="192.0.2.1", prefix=24,
           flags="00000001", mac="02:00:00:00:00:01"):
    return f"{name:<8} {state} {address}/{prefix} 0x{flags} {mac}\n".encode()


@pytest.mark.parametrize("raw,expected", [
    (netcfg(), ("cp0", "192.0.2.1", 24, True)),
    (netcfg(state="DOWN", address="0.0.0.0", prefix=0, flags="00000000"),
     ("cp0", "0.0.0.0", 0, False)),
])
def test_netcfg_rows(raw, expected):
    row = offline.parse_netcfg(raw)[0]
    assert (row["interface"], row["address"], row["prefix_length"], row["up"]) == expected
    assert "mac" not in json.dumps(row).lower()
    assert b"02:00:00:00:00:01" not in json.dumps(row).encode()
    assert collector.classify_format(("shell", "netcfg"), raw) == "SUCCESS"


def test_multiple_and_zero_address_preserved_but_not_promoted():
    rows = offline.parse_netcfg(netcfg() + netcfg("cp1", "DOWN", "0.0.0.0", 0, "00000000"))
    assert len(rows) == 2 and rows[1]["address"] == "0.0.0.0"
    assert not rows[1]["has_ipv4_address"]
    assert offline._items(rows, "cp1") == set()


@pytest.mark.parametrize("raw", [b"", b"usage: netcfg\n", b"\xff\n", netcfg() * 2,
    netcfg(prefix=33), netcfg(flags="00000000"), netcfg(address="999.0.0.1"),
    netcfg().replace(b" 0x", b" x"), netcfg().replace(b"cp0", b"a" * 16),
    netcfg().replace(b"192.0.2.1", b"192.0.2.1;up"), netcfg() * 800,
])
def test_bad_netcfg_fails_closed(raw):
    with pytest.raises(offline.FormatError):
        offline.parse_netcfg(raw)
    assert collector.classify_format(("shell", "netcfg"), raw) == "UNEXPECTED_FORMAT"


def test_netcfg_no_arguments_and_no_fallback():
    assert analyzer.expected("43T0-D0-3")[-1][1] == ("shell", "netcfg")
    assert len(analyzer.expected("43T0-D0-3")) == 23
    assert sum(row[1] == ("shell", "netcfg") for row in analyzer.expected("43T0-D0-3")) == 3
    assert all("ifconfig" not in row[1] for row in analyzer.expected("43T0-D0-3"))
    assert all(row[1] != ("shell", "netcfg") for row in analyzer.expected("43T0-D0-3")[:8])
    assert ("shell", "ifconfig") not in collector.ALLOWED_SUFFIXES
    for args in [("cp0",), ("cp0", "dhcp"), ("cp0", "up"), ("cp0", "down"),
                 ("cp0", "flhosts"), ("cp0", "deldefault"), ("cp0", "hwaddr", "x")]:
        assert not collector.allowed_argv(("adb", "-s", "synthetic-endpoint", "shell", "netcfg", *args),
                                          "synthetic-endpoint")


def test_netcfg_mac_removed_from_derived_and_scanner_rejects_leak():
    raw = netcfg()
    snap = offline.snapshot("connected", {"netcfg.raw": raw})
    assert snap.ipv4_addresses[0]["address"] == "192.0.2.1"
    assert "02:00:00:00:00:01" not in json.dumps(snap.ipv4_addresses)
    with pytest.raises(offline.FormatError):
        offline.privacy_scan(raw.decode())
    with pytest.raises(offline.FormatError):
        offline.privacy_scan("192.0.2.1:5555")


def archive_with(path, members):
    with tarfile.open(path, "w") as archive:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def test_static_archive_present_absent_unresolved(tmp_path):
    path = tmp_path / "archive.tar"
    archive_with(path, [(static.MEMBER, b"\x7fELFsynthetic")])
    found = static.inspect_archive(path)
    assert found["status"] == "HONDA_PRESERVED_NETCFG_PRESENT" and not found["known_binary"]
    archive_with(path, [("other", b"x")])
    assert static.inspect_archive(path)["status"] == "HONDA_PRESERVED_NETCFG_ABSENT"
    archive_with(path, [(static.MEMBER, b"invalid")])
    assert static.inspect_archive(path)["status"] == "HONDA_PRESERVED_NETCFG_UNRESOLVED"
    assert static.inspect_archive(tmp_path / "missing")["status"] == "HONDA_PRESERVED_NETCFG_UNRESOLVED"


def test_duplicate_ipv6_route_set_semantics():
    from test_step43t0d_prep import phase, v6route
    base = phase("baseline")
    connected = phase("connected", ("cp0",))
    connected.ipv6_routes = offline.parse_ipv6_routes(v6route(("cp0",)) * 3)
    post = phase("post-disconnect")
    first = offline.phase_deltas({"baseline": base, "connected": connected, "post-disconnect": post})
    connected.ipv6_routes = offline.parse_ipv6_routes(v6route(("cp0",)))
    second = offline.phase_deltas({"baseline": base, "connected": connected, "post-disconnect": post})
    assert first == second
