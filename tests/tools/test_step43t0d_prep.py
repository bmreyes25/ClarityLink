"""Synthetic-only offline DPREP contract and decision tests."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/"tools"))
import analyze_43t0d_capture as analyzer
import step43t0d_offline as m

DEV_HEADER=b"Inter-|   Receive |  Transmit\n face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\n"
ROUTE_HEADER=b"Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\n"
ZERO="0"*32
FE="fe800000000000000000000000000001"

def dev(names=(), traffic=1):
    return DEV_HEADER+b"".join(f"{n}: {traffic} 2 0 0 0 0 0 0 {traffic} 2 0 0 0 0 0 0\n".encode() for n in names)
def route(names=()):
    return ROUTE_HEADER+b"".join(f"{n}\t00000000\t00000000\t0001\t0\t0\t0\t00000000\t0\t0\t0\n".encode() for n in names)
def v6route(names=()):
    return b"".join(f"{FE} 40 {ZERO} 00 {ZERO} 00000001 00000000 00000000 00000001 {n}\n".encode() for n in names)
def inet6(names=()):
    return b"".join(f"{FE} 01 40 20 80 {n}\n".encode() for n in names)
def config(names=(), ipv4=False):
    return b"".join(f"{n}: ip {'192.0.2.1' if ipv4 else '0.0.0.0'} mask 255.255.255.0 flags [up]\n".encode() for n in names) or b"lo: ip 127.0.0.1 mask 255.0.0.0 flags [up]\n"
def phase(phase,names=(),ipv4=False,traffic=1,route_names=None,addr_names=None):
    rn=names if route_names is None else route_names
    an=names if addr_names is None else addr_names
    return m.snapshot(phase,dict(zip(m.FILES,(dev(names,traffic),route(rn if ipv4 else ()),v6route(rn),inet6(an),config(names,ipv4)))))

def test_parsers_normal_and_empty():
    assert m.parse_dev(dev(("cp0","eth0")))["cp0"]["tx_bytes"]==1
    assert m.parse_ipv4_routes(route(("cp0",)))[0]["destination"]=="0.0.0.0"
    assert m.parse_ipv6_routes(v6route(("cp0",)))[0]["destination"].startswith("fe80:")
    assert m.parse_if_inet6(inet6(("cp0",)))[0]["scope_class"]=="LINK_LOCAL"
    assert m.parse_ifconfig(config(("cp0",)))[0]["up"]
    assert m.parse_if_inet6(b"")==[] and m.parse_ipv6_routes(b"")==[]

@pytest.mark.parametrize("parser,raw",[
    (m.parse_dev,b""),(m.parse_dev,DEV_HEADER+b"cp0: 1 2\n"),(m.parse_dev,dev(("cp0",))+dev(("cp0",))[len(DEV_HEADER):]),
    (m.parse_dev,DEV_HEADER+b"cp0: -1 2 0 0 0 0 0 0 1 2 0 0 0 0 0 0\n"),
    (m.parse_dev,DEV_HEADER+b"cp0: 99999999999999999999999 2 0 0 0 0 0 0 1 2 0 0 0 0 0 0\n"),
    (m.parse_ipv4_routes,ROUTE_HEADER+b"cp0 0000000X 00000000 0001 0 0 0 00000000 0 0 0\n"),
    (m.parse_ipv4_routes,ROUTE_HEADER+b"cp0 00000000 00000000 0001 0 0 -1 00000000 0 0 0\n"),
    (m.parse_ipv4_routes,route(("cp0",))+route(("cp0",))[len(ROUTE_HEADER):]),
    (m.parse_if_inet6,b"bad 01 40 20 80 cp0\n"),(m.parse_if_inet6,f"{FE} 01 ff 20 80 cp0\n".encode()),
    (m.parse_ipv6_routes,f"{FE} ff {ZERO} 00 {ZERO} 00000001 00000000 00000000 00000001 cp0\n".encode()),
    (m.parse_ipv6_routes,v6route(("cp0",)).replace(b"fe80",b"xx80")),
    (m.parse_ifconfig,b"cp0 Link encap:Ethernet HWaddr 00:11:22:33:44:55\n"),
    (m.parse_ifconfig,b"usage: ifconfig interface up\n"),
    (m.parse_ifconfig,b"\xff\n"),
])
def test_malformed_parsers(parser,raw):
    with pytest.raises(m.FormatError): parser(raw)

@pytest.mark.parametrize("parser,raw",[(m.parse_ipv6_routes,v6route(("cp0",))),(m.parse_if_inet6,inet6(("cp0",))),(m.parse_ipv4_routes,route(("cp0",)))])
def test_truncation_at_every_byte(parser,raw):
    for size in range(1,len(raw)):
        try: parser(raw[:size])
        except m.FormatError: pass

def test_scenarios():
    b=phase("baseline"); c=phase("connected",("cp0",)); p=phase("post-disconnect")
    ideal=m.decide(dict(baseline=b,connected=c,**{"post-disconnect":p}))
    assert (ideal["candidate_state"],ideal["G11_A"],ideal["G11_B"],ideal["G11_C"],ideal["G11_D"],ideal["G11_F"]) == ("SINGLE_STRONG_CANDIDATE","YES_OBSERVED","YES_OBSERVED","IPv6","YES","NO")
    assert ideal["candidate_route_policy"]["scope_id_required"]
    persistent=m.decide(dict(baseline=phase("baseline",("cp0",),route_names=(),addr_names=()),connected=c,**{"post-disconnect":phase("post-disconnect",("cp0",),route_names=(),addr_names=())}))
    assert persistent["candidate_state"]=="SINGLE_STRONG_CANDIDATE"
    dual=m.decide(dict(baseline=b,connected=phase("connected",("cp0",),ipv4=True),**{"post-disconnect":p}))
    assert dual["G11_C"]=="DUAL"
    traffic=m.decide(dict(baseline=phase("baseline",("cp0",),traffic=1),connected=phase("connected",("cp0",),traffic=100),**{"post-disconnect":phase("post-disconnect",("cp0",),traffic=101)}))
    assert traffic["G11_A"]=="NO" and traffic["G11_F"]=="NO"
    multiple=m.decide(dict(baseline=b,connected=phase("connected",("cp0","cp1")),**{"post-disconnect":p}))
    assert multiple["candidate_state"]=="MULTIPLE_CANDIDATES"
    partial=m.decide(dict(baseline=b,connected=c))
    assert partial["candidate_state"]=="PARTIAL_CAPTURE" and partial["G11_A"]!="YES_OBSERVED"
    conflict=m.decide(dict(baseline=b,connected=phase("connected",("cp0",),route_names=("cp1",)),**{"post-disconnect":p}))
    assert conflict["candidate_state"]=="CONFLICTING_EVIDENCE"
    ipv4=m.decide(dict(baseline=b,connected=phase("connected",("cp0",),ipv4=True,addr_names=(),route_names=("cp0",)),**{"post-disconnect":p}))
    assert ipv4["G11_C"]=="IPv4"
    no_scope=m.decide(dict(baseline=b,connected=phase("connected",("cp0",),route_names=()),**{"post-disconnect":p}))
    assert no_scope["candidate_route_policy"] is None
    assert all(x["G11_F"]=="NO" for x in (ideal,persistent,dual,traffic,multiple,partial,conflict,ipv4,no_scope))
    public=m.public_summary(ideal,"CAPTURE_VALID","IDENTITY_MATCH",dict(baseline=b,connected=c,**{"post-disconnect":p}))
    assert "fe80:" not in json.dumps(public)
    assert m.correlate_40e()["process_ownership"]=="READ_BLOCKED_WITHOUT_PRIVILEGE"

def fixture(tmp, monkeypatch, count=23, version="43T0-D0-1"):
    root=tmp/"capture"; root.mkdir()
    monkeypatch.setattr(analyzer,"SHELL_HASH",hashlib.sha256(b"uid=2000(shell) gid=2000(shell) groups=2000(shell)").hexdigest())
    monkeypatch.setattr(analyzer,"KERNEL_HASH",hashlib.sha256(b"synthetic kernel").hexdigest())
    values=[b"List of devices attached\nsynthetic-endpoint\tdevice\n",b"uid=2000(shell) gid=2000(shell) groups=2000(shell)\n",b"synthetic kernel\n",*(v.encode()+b"\n" for v in m.PROPERTIES)]
    data=[]
    for phase in m.PHASES:
        names=("cp0",) if phase=="connected" else ()
        observer = (b"".join(f"{n:<8} UP  0.0.0.0/0  0x00000001 02:00:00:00:00:01\n".encode() for n in names)
                    or b"lo       UP  127.0.0.1/8  0x00000001 00:00:00:00:00:00\n") if version=="43T0-D0-3" else config(names)
        data.extend((dev(names),route(),v6route(names),inet6(names),observer))
    values+=data; commands=[]
    for i,(phase,suffix,rel) in enumerate(analyzer.expected(version)[:count]):
        raw=values[i]; path=root/rel; path.parent.mkdir(exist_ok=True); path.write_bytes(raw)
        commands.append(dict(phase=phase,command_index=i+1,argv=["adb","devices"] if i==0 else ["adb","-s","synthetic-endpoint",*suffix],
                             target_reference="redacted",result_class="SUCCESS",stdout_bytes=len(raw),stderr_bytes=0,
                             stdout_sha256=hashlib.sha256(raw).hexdigest(),stderr_sha256=hashlib.sha256(b"").hexdigest()))
    manifest=dict(collector_version=version,collector_source_sha256=m.COLLECTOR_HASHES[version],approved_plan_commit=m.PLAN_COMMIT,
                  project_commit="a"*40,commands=commands,final_status="SUCCESS" if count==23 else "USER_ABORT")
    if version=="43T0-D0-3": manifest["revised_plan_sha256"]=m.D3_PLAN_SHA256
    (root/"manifest.json").write_text(json.dumps(manifest))
    return root,manifest

def test_capture_validation_immutability_and_report(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch)
    before={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    assert analyzer.validate_capture(root)[0:2]==("CAPTURE_VALID","IDENTITY_MATCH")
    out=tmp_path/"derived"; summary=analyzer.analyze(root,out)
    assert summary["G11_F"]=="NO" and summary["privacy_status"]=="SANITIZED"
    assert "Step 43T0-D" in (out/"43t0d-read-only-honda-network-delta.md").read_text()
    after={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
    assert before==after

def test_prefix_and_invalid_manifest(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,18)
    assert analyzer.validate_capture(root)[0]=="CAPTURE_VALID_PARTIAL"
    manifest["commands"][10]["argv"][-1]="/proc/secret"
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_path_and_integrity(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch)
    (root/"baseline/net-dev.raw").unlink(); (root/"baseline/net-dev.raw").symlink_to(tmp_path/"outside")
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)
    (root/"baseline/net-dev.raw").unlink(); (root/"baseline/net-dev.raw").write_bytes(b"tampered")
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_privacy_gate():
    for secret in ("aa:bb:cc:dd:ee:ff","192.0.2.1:5555","fe80::1","SSID: cabin","password=secret"):
        with pytest.raises(m.FormatError): m.privacy_scan(secret)

def test_failed_final_command_is_bounded_partial(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,9)
    row=manifest["commands"][-1]
    row["result_class"]="UNEXPECTED_FORMAT"
    rel=analyzer.expected()[8][2]
    (root/rel).write_bytes(b"malformed raw output")
    row["stdout_bytes"]=len(b"malformed raw output")
    row["stdout_sha256"]=hashlib.sha256(b"malformed raw output").hexdigest()
    manifest["final_status"]="UNEXPECTED_FORMAT"
    (root/"manifest.json").write_text(json.dumps(manifest))
    assert analyzer.validate_capture(root)[0]=="CAPTURE_VALID_PARTIAL"
    summary=analyzer.analyze(root,tmp_path/"derived")
    assert summary["G11_A"]=="NO" and summary["G11_B"]=="LIKELY_INFERRED" and summary["G11_F"]=="NO"

@pytest.mark.parametrize("change",["duplicate_index","extra_command","reorder","result_class","source_hash","byte_count","target_reference"])
def test_manifest_fail_closed(tmp_path,monkeypatch,change):
    root,manifest=fixture(tmp_path,monkeypatch)
    if change=="duplicate_index": manifest["commands"][4]["command_index"]=4
    if change=="extra_command": manifest["commands"].append(manifest["commands"][-1].copy())
    if change=="reorder": manifest["commands"][8]["argv"][-1]="/proc/net/route"
    if change=="result_class": manifest["commands"][4]["result_class"]="MYSTERY"
    if change=="source_hash": manifest["collector_source_sha256"]="0"*64
    if change=="byte_count": manifest["commands"][9]["stdout_bytes"]+=1
    if change=="target_reference": manifest["commands"][0]["target_reference"]="synthetic-endpoint"
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)
    assert not (tmp_path/"derived").exists()

def test_extra_file_and_large_input_rejected(tmp_path,monkeypatch):
    root,_=fixture(tmp_path,monkeypatch)
    (root/"unexpected.raw").write_bytes(b"x")
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)
    (root/"unexpected.raw").unlink()
    (root/"baseline/net-dev.raw").write_bytes(b"x"*65537)
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_private_detail_separated_and_public_clean(tmp_path,monkeypatch):
    root,_=fixture(tmp_path,monkeypatch)
    out=tmp_path/"private-output"
    analyzer.analyze(root,out,private_binding_detail=True)
    assert "fe80:" in (out/"PRIVATE_BINDING_DETAIL.json").read_text()
    assert "fe80:" not in (out/"43t0d-network-summary.json").read_text()
    assert "fe80:" not in (out/"43t0d-read-only-honda-network-delta.md").read_text()
    assert (out/"PRIVATE_BINDING_DETAIL.json").stat().st_mode & 0o777 == 0o600

def test_offline_source_has_no_execution_or_network_import():
    import ast
    for name in ("analyze_43t0d_capture.py","step43t0d_offline.py"):
        tree=ast.parse((Path(__file__).resolve().parents[2]/"tools"/name).read_text())
        imported={alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for alias in (node.names if isinstance(node,ast.Import) else [ast.alias(name=node.module or "")])}
        assert not ({"subprocess","socket","requests","urllib"}&imported)

def test_no_ipv4_and_bad_dev_header():
    assert m.parse_ifconfig(config(("cp0",)))[0]["address"] is None
    with pytest.raises(m.FormatError): m.parse_dev(DEV_HEADER.replace(b"compressed multicast",b"secret multicast")+dev(("cp0",))[len(DEV_HEADER):])

def test_zero_target_fail_closed_capture_is_valid_partial(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,1)
    raw=b"List of devices attached\n"
    (root/"preflight/devices.raw").write_bytes(raw)
    manifest["commands"][0]["stdout_bytes"]=len(raw)
    manifest["commands"][0]["stdout_sha256"]=hashlib.sha256(raw).hexdigest()
    manifest["final_status"]="AMBIGUOUS_ADB_TARGET"
    (root/"manifest.json").write_text(json.dumps(manifest))
    assert analyzer.validate_capture(root)[0:2]==("CAPTURE_VALID_PARTIAL","IDENTITY_INCOMPLETE")
    summary=analyzer.analyze(root,tmp_path/"derived")
    assert summary["completed_phases"]==[] and summary["G11_A"]=="NO"

def test_ambiguous_target_cannot_precede_identity(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,2)
    raw=b"List of devices attached\n"
    (root/"preflight/devices.raw").write_bytes(raw)
    manifest["commands"][0]["stdout_bytes"]=len(raw)
    manifest["commands"][0]["stdout_sha256"]=hashlib.sha256(raw).hexdigest()
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_link_local_missing_scope_mapping_never_bind_ready():
    b=phase("baseline"); c=phase("connected",("cp0",)); p=phase("post-disconnect")
    c.ipv6_addresses[0]["index"]=0
    result=m.decide(dict(baseline=b,connected=c,**{"post-disconnect":p}))
    assert result["candidate_route_policy"] is None
    assert result["G11_B"]!="YES_OBSERVED"

def test_synthetic_summary_and_report_golden():
    root=Path(__file__).resolve().parents[2]
    b=phase("baseline"); c=phase("connected",("cp0",)); p=phase("post-disconnect")
    snap=dict(baseline=b,connected=c,**{"post-disconnect":p})
    actual=m.public_summary(m.decide(snap),"CAPTURE_VALID","IDENTITY_MATCH",snap)
    actual.update(synthetic_example=True,provenance="SANITIZED_SYNTHETIC_FIXTURE_ONLY_NO_HONDA_CAPTURE")
    expected=json.loads((root/"research/runtime/43t0d-synthetic-example.json").read_text())
    assert actual==expected
    manifest=dict(project_commit="a"*40,commands=[None]*23,final_status="SUCCESS")
    report="# SYNTHETIC GOLDEN FIXTURE — NO HONDA CAPTURE\n"+analyzer.render_report(actual,manifest)
    assert report==(root/"tests/fixtures/43t0d-prep-synthetic-report.golden.md").read_text()

def test_honda_route_header_whitespace_regression():
    from step43t0d0_collector import VERSION, classify_format
    assert VERSION=="43T0-D0-3"
    header=b"Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT   \n"
    body=b"cp0\t00000000\t00000000\t0001\t0\t0\t0\t00000000\t0\t0\t0\n"
    assert classify_format(("shell","cat","/proc/net/route"),header+body)=="SUCCESS"
    assert m.parse_ipv4_routes(header+body)[0]["interface"]=="cp0"
    assert classify_format(("shell","cat","/proc/net/route"),header.replace(b"Gateway",b"Unknown")+body)=="UNEXPECTED_FORMAT"

def test_d0_2_capture_accepted_and_old_hash_still_pinned(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch)
    manifest["collector_version"]="43T0-D0-2"
    manifest["collector_source_sha256"]=m.COLLECTOR_HASHES["43T0-D0-2"]
    (root/"manifest.json").write_text(json.dumps(manifest))
    assert analyzer.validate_capture(root)[0]=="CAPTURE_VALID"
    manifest["collector_source_sha256"]=m.COLLECTOR_HASH
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_d0_3_capture_accepted_and_uses_netcfg(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,version="43T0-D0-3")
    assert analyzer.validate_capture(root)[0:2]==("CAPTURE_VALID","IDENTITY_MATCH")
    before=hashlib.sha256((root/"connected/netcfg.raw").read_bytes()).hexdigest()
    summary=analyzer.analyze(root,tmp_path/"derived")
    assert summary["G11_F"]=="NO"
    assert "02:00:00:00:00:01" not in (tmp_path/"derived/43t0d-network-summary.json").read_text()
    assert "02:00:00:00:00:01" not in (tmp_path/"derived/43t0d-read-only-honda-network-delta.md").read_text()
    assert before==hashlib.sha256((root/"connected/netcfg.raw").read_bytes()).hexdigest()
    manifest["revised_plan_sha256"]="0"*64
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_d0_3_partial_prefix_and_no_fallback(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch,count=13,version="43T0-D0-3")
    assert analyzer.validate_capture(root)[0]=="CAPTURE_VALID_PARTIAL"
    assert (root/"baseline/netcfg.raw").exists()
    manifest["commands"][-1]["argv"][-1]="ifconfig"
    (root/"manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(m.FormatError): analyzer.validate_capture(root)

def test_preflight_trailing_blank_line_accepted(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path,monkeypatch)
    raw=b"List of devices attached\nsynthetic-endpoint\tdevice\n\n"
    (root/"preflight/devices.raw").write_bytes(raw)
    manifest["commands"][0]["stdout_bytes"]=len(raw)
    manifest["commands"][0]["stdout_sha256"]=hashlib.sha256(raw).hexdigest()
    (root/"manifest.json").write_text(json.dumps(manifest))
    assert analyzer.validate_capture(root)[0]=="CAPTURE_VALID"

def test_linux_ipv6_route_can_repeat_identical_visible_rows():
    raw=v6route(("cp0",))*3
    rows=m.parse_ipv6_routes(raw)
    assert len(rows)==3
    assert rows[0]==rows[1]==rows[2]
