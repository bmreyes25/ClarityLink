"""Pure offline 43T0-D parsing and evidence decisions. No device or network APIs."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PHASES = ("baseline", "connected", "post-disconnect")
FILES = ("net-dev.raw", "net-route.raw", "ipv6-route.raw", "if-inet6.raw", "ifconfig.raw")
IDENTITY = (("id.raw", ("shell", "id")), ("proc-version.raw", ("shell", "cat", "/proc/version")),
            ("release.raw", ("shell", "getprop", "ro.build.version.release")),
            ("sdk.raw", ("shell", "getprop", "ro.build.version.sdk")),
            ("device.raw", ("shell", "getprop", "ro.product.device")),
            ("board.raw", ("shell", "getprop", "ro.product.board")),
            ("hardware.raw", ("shell", "getprop", "ro.hardware")))
NETWORK = (("shell", "cat", "/proc/net/dev"), ("shell", "cat", "/proc/net/route"),
           ("shell", "cat", "/proc/net/ipv6_route"), ("shell", "cat", "/proc/net/if_inet6"),
           ("shell", "ifconfig"))
RESULTS = {"SUCCESS", "COMMAND_UNAVAILABLE", "PERMISSION_DENIED", "TIMEOUT", "OUTPUT_LIMIT_EXCEEDED",
           "UNEXPECTED_FORMAT", "ADB_TRANSPORT_FAILURE", "IDENTITY_MISMATCH", "IDENTITY_INCOMPLETE",
           "AMBIGUOUS_ADB_TARGET", "UNEXPECTED_PRIVILEGE", "USER_ABORT", "STOCK_SANITY_FAILURE"}
COLLECTOR_HASH = "2162e795568307cfe34dbf7bc8a6de1f70d358119e4aca22e9c6e29789809afc"
PLAN_COMMIT = "fdb3da178febc2df88947d5f73f4c630f46fdc1d"
SHELL_HASH = "590cc36f1a98082e64e0e2d836c94c125bef1c73fcb7daf981b7286c6b310992"
KERNEL_HASH = "8fa1c06d864d3dab9be4c53c13ddecb421516bd02ace3a27ef7811a7ee79c451"
PROPERTIES = ("4.2.2", "17", "vcm30t30a", "Andromeda", "vcm30t30")
HEX = re.compile(r"[0-9a-fA-F]+\Z")
IFACE = re.compile(r"[A-Za-z0-9_.-]{1,32}\Z")
MAX_LINES = 4096

class FormatError(ValueError):
    pass

def lines(raw: bytes) -> list[str]:
    if len(raw) > 65536:
        raise FormatError("oversized input")
    try:
        result = raw.decode("utf-8", "strict").splitlines()
    except UnicodeError as exc:
        raise FormatError("invalid UTF-8") from exc
    if len(result) > MAX_LINES or any(len(row) > 4096 for row in result):
        raise FormatError("input bounds")
    return result

def decimal(value: str) -> int:
    if not re.fullmatch(r"[0-9]{1,20}", value):
        raise FormatError("invalid decimal")
    number = int(value)
    if number > 2**64-1:
        raise FormatError("decimal overflow")
    return number

def hexfield(value: str, width: int) -> int:
    if len(value) != width or not HEX.fullmatch(value):
        raise FormatError("invalid hex")
    return int(value, 16)

def interface(value: str) -> str:
    if not IFACE.fullmatch(value):
        raise FormatError("invalid interface")
    return value

def parse_dev(raw: bytes) -> dict:
    rows = lines(raw)
    if len(rows) < 2 or not re.fullmatch(r"\s*Inter-\|\s*Receive\s*\|\s*Transmit\s*", rows[0]) or not re.fullmatch(r"\s*face\s*\|\s*bytes packets errs drop fifo frame compressed multicast\s*\|\s*bytes packets errs drop fifo colls carrier compressed\s*", rows[1]):
        raise FormatError("net-dev header")
    out = {}
    for row in rows[2:]:
        if not row.strip(): continue
        if row.count(":") != 1: raise FormatError("net-dev row")
        name, values = row.split(":")
        name = interface(name.strip())
        fields = values.split()
        if len(fields) != 16 or name in out: raise FormatError("net-dev width/duplicate")
        n = [decimal(v) for v in fields]
        out[name] = dict(zip(("rx_bytes", "rx_packets", "rx_errors", "rx_dropped", "tx_bytes", "tx_packets", "tx_errors", "tx_dropped"),
                             (n[0], n[1], n[2], n[3], n[8], n[9], n[10], n[11])))
    return out

def ipv4hex(value: str) -> str:
    hexfield(value, 8)
    return str(ipaddress.IPv4Address(bytes.fromhex(value)[::-1]))

def parse_ipv4_routes(raw: bytes) -> list[dict]:
    rows = lines(raw)
    if not rows or rows[0].split() != ["Iface", "Destination", "Gateway", "Flags", "RefCnt", "Use", "Metric", "Mask", "MTU", "Window", "IRTT"]:
        raise FormatError("route header")
    out, seen = [], set()
    for row in rows[1:]:
        if not row.strip(): continue
        f = row.split()
        if len(f) != 11: raise FormatError("route width")
        name = interface(f[0]); dest, gateway, mask = (ipv4hex(f[i]) for i in (1, 2, 7))
        flags = hexfield(f[3], 4)
        refcnt, use, metric, mtu, window, irtt = (decimal(f[i]) for i in (4,5,6,8,9,10))
        key = (name,dest,gateway,mask,flags,metric)
        if key in seen: raise FormatError("duplicate route")
        seen.add(key)
        out.append(dict(interface=name,destination=dest,gateway=gateway,mask=mask,flags=flags,
                        refcnt=refcnt,use=use,metric=metric,mtu=mtu,window=window,irtt=irtt))
    return out

def ipv6hex(value: str) -> str:
    hexfield(value, 32)
    return str(ipaddress.IPv6Address(int(value,16)))

def parse_if_inet6(raw: bytes) -> list[dict]:
    out, seen = [], set()
    for row in lines(raw):
        if not row.strip(): continue
        f = row.split()
        if len(f) != 6: raise FormatError("if_inet6 width")
        address = ipv6hex(f[0]); index,prefix,scope,flags = (hexfield(v,2) for v in f[1:5])
        if prefix > 128: raise FormatError("IPv6 prefix")
        name = interface(f[5]); key=(name,address)
        if key in seen: raise FormatError("duplicate IPv6 address")
        seen.add(key)
        ip = ipaddress.IPv6Address(address)
        scope_class = "LINK_LOCAL" if ip.is_link_local else "LOOPBACK" if ip.is_loopback else "GLOBAL" if ip.is_global else "OTHER"
        out.append(dict(interface=name,address=address,index=index,prefix_length=prefix,scope=scope,flags=flags,scope_class=scope_class))
    return out

def parse_ipv6_routes(raw: bytes) -> list[dict]:
    """Linux v3.1 net/ipv6/route.c rt6_info_route proc serializer."""
    out, seen = [], set()
    for row in lines(raw):
        if not row.strip(): continue
        f=row.split()
        if len(f)!=10: raise FormatError("ipv6_route width")
        dest,src,hop=(ipv6hex(f[i]) for i in (0,2,4))
        dp,sp=(hexfield(f[i],2) for i in (1,3))
        if dp>128 or sp>128: raise FormatError("IPv6 route prefix")
        metric,refcnt,use,flags=(hexfield(f[i],8) for i in (5,6,7,8))
        name=interface(f[9]); key=(name,dest,dp,src,sp,hop,metric,flags)
        if key in seen: raise FormatError("duplicate IPv6 route")
        seen.add(key)
        out.append(dict(interface=name,destination=dest,destination_prefix_length=dp,source=src,
                        source_prefix_length=sp,next_hop=hop,metric=metric,refcnt=refcnt,use=use,flags=flags))
    return out

IFCONFIG_RE = re.compile(r"([A-Za-z0-9_.-]{1,32}): ip ((?:[0-9]{1,3}\.){3}[0-9]{1,3}) mask ((?:[0-9]{1,3}\.){3}[0-9]{1,3}) flags \[([a-z, ]+)\]\Z")
def parse_ifconfig(raw: bytes) -> list[dict]:
    rows=lines(raw)
    if not rows: raise FormatError("empty ifconfig")
    out=[]; seen=set()
    for row in rows:
        match=IFCONFIG_RE.fullmatch(row.strip())
        if not match: raise FormatError("UNEXPECTED_FORMAT")
        name,address,mask,flags=match.groups()
        if name in seen: raise FormatError("duplicate ifconfig")
        seen.add(name)
        try:
            address=str(ipaddress.IPv4Address(address)); mask=str(ipaddress.IPv4Address(mask))
        except ipaddress.AddressValueError as exc: raise FormatError("invalid IPv4") from exc
        out.append(dict(interface=name,address=None if address=="0.0.0.0" else address,netmask=mask,flags=flags.split(","),up="up" in flags.split(",")))
    return out

@dataclass
class NetworkPhaseSnapshot:
    phase: str
    interfaces: dict = field(default_factory=dict)
    ipv4_addresses: list = field(default_factory=list)
    ipv6_addresses: list = field(default_factory=list)
    ipv4_routes: list = field(default_factory=list)
    ipv6_routes: list = field(default_factory=list)
    complete: bool = False
    source_hashes: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

def snapshot(phase: str, raw: dict[str,bytes]) -> NetworkPhaseSnapshot:
    if phase not in PHASES: raise FormatError("phase")
    s=NetworkPhaseSnapshot(phase)
    parsers={FILES[0]:("interfaces",parse_dev),FILES[1]:("ipv4_routes",parse_ipv4_routes),FILES[2]:("ipv6_routes",parse_ipv6_routes),
             FILES[3]:("ipv6_addresses",parse_if_inet6),FILES[4]:("ipv4_addresses",parse_ifconfig)}
    for name,(attr,parser) in parsers.items():
        if name in raw:
            setattr(s,attr,parser(raw[name])); s.source_hashes[name]=hashlib.sha256(raw[name]).hexdigest()
        else: s.warnings.append("missing " + name)
    s.complete=len(s.source_hashes)==5
    return s

def _items(rows: list, name: str) -> set:
    return {r["address"] if "address" in r else (r["destination"],r.get("destination_prefix_length"),r.get("gateway"),r.get("next_hop")) for r in rows if r["interface"]==name and r.get("address","NON_ADDRESS") is not None}

def phase_deltas(snapshots: dict[str,NetworkPhaseSnapshot]) -> list[dict]:
    b=snapshots.get("baseline"); c=snapshots.get("connected"); p=snapshots.get("post-disconnect")
    if not b or not c or not b.complete or not c.complete: return []
    names=set(b.interfaces)|set(c.interfaces)
    if p and p.complete: names|=set(p.interfaces)
    out=[]
    for name in sorted(names):
        present=[name in s.interfaces if s and s.complete else None for s in (b,c,p)]
        sets=lambda attr:[_items(getattr(s,attr),name) if s and s.complete else None for s in (b,c,p)]
        a4,a6,r4,r6=(sets(attr) for attr in ("ipv4_addresses","ipv6_addresses","ipv4_routes","ipv6_routes"))
        added=[x[1]-x[0] for x in (a4,a6,r4,r6)]
        reversed_values=[bool(x[1]-x[0]) and x[2]==x[0] for x in (a4,a6,r4,r6)] if p and p.complete else []
        structural=present[:2]==[False,True] or any(added)
        reversal=(present==[False,True,False] or any(reversed_values)) if p and p.complete else False
        traffic=None
        if present[0] and present[1]:
            traffic={k:c.interfaces[name][k]-b.interfaces[name][k] for k in ("rx_bytes","tx_bytes")}
        category=("APPEARS_WITH_CARPLAY" if present[:2]==[False,True] else
                  "PERSISTENT_INTERFACE_WITH_NEW_ADDRESS" if added[0] or added[1] else
                  "PERSISTENT_INTERFACE_WITH_ROUTE_CHANGE" if added[2] or added[3] else
                  "PERSISTENT_INTERFACE_TRAFFIC_ONLY" if traffic and any(traffic.values()) else "UNCHANGED")
        out.append(dict(interface=name,present=present,category=category,phase_reversal_correlation=reversal,
                        structural=bool(structural),ipv4_added=sorted(added[0]),ipv6_added=sorted(added[1]),
                        ipv4_routes_added=len(added[2]),ipv6_routes_added=len(added[3]),traffic_delta=traffic,
                        ipv4_reversed=bool(reversed_values and reversed_values[0]),
                        ipv6_reversed=bool(reversed_values and reversed_values[1]),
                        routes_reversed=bool(reversed_values and any(reversed_values[2:]))))
    return out

def correlate_40e() -> dict:
    # Sanitized verified 43T0-A report: phase-correlated link-local global socket rows.
    return dict(address_class="IPv6_LINK_LOCAL", stock_carplay_correlation=True,
                process_ownership="READ_BLOCKED_WITHOUT_PRIVILEGE", provenance="step-reports/43t0a-40e-network-evidence-reanalysis.md")

def decide(snapshots: dict[str,NetworkPhaseSnapshot], *, private=False) -> dict:
    deltas=phase_deltas(snapshots); full=all(x in snapshots and snapshots[x].complete for x in PHASES)
    candidates=[]; conflicts=[]; candidate_details=[]
    for d in deltas:
        if not d["structural"]: continue
        name=d["interface"]; c=snapshots["connected"]
        addresses=[r for r in c.ipv6_addresses if r["interface"]==name and r["address"] in d["ipv6_added"]]
        routes=[r for r in c.ipv6_routes if r["interface"]==name and r["destination"]!="::"
                and any(ipaddress.IPv6Address(a["address"]) in ipaddress.IPv6Network((r["destination"],r["destination_prefix_length"]),strict=False) for a in addresses)]
        scoped=all(a["index"]>0 and (a["scope"]==0x20 if a["scope_class"]=="LINK_LOCAL" else True) for a in addresses)
        ipv6=bool(addresses and routes and d["ipv6_routes_added"] and scoped)
        ipv4=bool(d["ipv4_added"] and d["ipv4_routes_added"])
        if addresses and (not routes or not scoped): conflicts.append(name)
        if ipv6 or ipv4:
            reasons=[d["category"]]
            if ipv6: reasons += ["IPV6_LINK_LOCAL_ADDRESS_AND_SCOPE" if any(a["scope_class"]=="LINK_LOCAL" for a in addresses) else "IPV6_ADDRESS", "IPV6_ROUTE_ON_INTERFACE"]
            if ipv4: reasons += ["IPV4_ADDRESS", "IPV4_ROUTE_ON_INTERFACE"]
            if d["phase_reversal_correlation"]: reasons.append("PHASE_REVERSAL_CORRELATION")
            if ipv6 and any(a["scope_class"]=="LINK_LOCAL" for a in addresses): reasons.append("MATCHES_40E_SOCKET_ADDRESS_CLASS")
            candidate_details.append(dict(interface=name,reasons=reasons,evidence_class="HONDA_OBSERVED_NETWORK_POLICY_INPUT" if d["phase_reversal_correlation"] else "INFERRED"))
            candidates.append((d,ipv4,ipv6,addresses))
    state=("CONFLICTING_EVIDENCE" if conflicts else "MULTIPLE_CANDIDATES" if len(candidates)>1 else
           "PARTIAL_CAPTURE" if not full else "SINGLE_STRONG_CANDIDATE" if len(candidates)==1 and candidates[0][0]["phase_reversal_correlation"] else
           "NO_CANDIDATE")
    chosen=candidates[0] if len(candidates)==1 else None
    strong=bool(chosen and chosen[0]["phase_reversal_correlation"] and full and state=="SINGLE_STRONG_CANDIDATE")
    family=("DUAL" if chosen and chosen[1] and chosen[2] else "IPv4" if chosen and chosen[1] else "IPv6" if chosen and chosen[2] else "UNKNOWN")
    policy=None
    if strong:
        d,v4,v6,addresses=chosen
        policy=dict(interface_name=d["interface"],address_family=family,local_address=(addresses[0]["address"] if private and v6 else d["ipv4_added"][0] if private and v4 else "WITHHELD"),
                    scope_id_required=v6 and any(r["scope_class"]=="LINK_LOCAL" for r in addresses),route_present=True,
                    wildcard_binding_recommended=False,evidence_class="HONDA_OBSERVED_NETWORK_POLICY_INPUT")
    correlation=correlate_40e()
    correlation.update(candidate_address_class_match=bool(chosen and chosen[2] and any(a["scope_class"]=="LINK_LOCAL" for a in chosen[3])),
                       route_supports_candidate=bool(chosen and (chosen[1] or chosen[2])),
                       topology_reversal=bool(chosen and chosen[0]["phase_reversal_correlation"]))
    return dict(candidate_state=state,candidates=candidate_details,conflicting_interfaces=conflicts,candidate_interface=chosen[0]["interface"] if chosen else None,
                candidate_address_family=family,candidate_route_policy=policy,
                G11_A="YES_OBSERVED" if strong else "LIKELY_INFERRED" if chosen else "NO",
                G11_B="YES_OBSERVED" if strong else "LIKELY_INFERRED" if chosen else "NO",
                G11_C=family if strong else "UNKNOWN",G11_D="YES" if strong else "PARTIAL" if chosen else "NO",
                G11_E="NO / READ_BLOCKED_WITHOUT_PRIVILEGE",G11_F="NO",
                evidence_classes=["OBSERVED_ON_HONDA_READ_ONLY","HONDA_RUNTIME_CORRELATION","HONDA_OBSERVED_NETWORK_POLICY_INPUT"] if strong else ["INFERRED","UNRESOLVED","READ_BLOCKED_WITHOUT_PRIVILEGE"],
                correlation_40e=correlation,phase_deltas=deltas,
                fact_provenance={"G11_A":"OBSERVED_ON_HONDA_READ_ONLY" if strong else "INFERRED",
                                 "G11_B":"OBSERVED_ON_HONDA_READ_ONLY" if strong else "INFERRED",
                                 "G11_C":"HONDA_OBSERVED_NETWORK_POLICY_INPUT" if strong else "UNRESOLVED",
                                 "G11_D":"HONDA_OBSERVED_NETWORK_POLICY_INPUT" if strong else "UNRESOLVED",
                                 "G11_E":"READ_BLOCKED_WITHOUT_PRIVILEGE","G11_F":"UNRESOLVED",
                                 "40E":"HONDA_RUNTIME_CORRELATION"},
                next_recommendation="43T1-PREP — offline reversible RAM-only listener/attachment readiness design" if strong else
                "NO_GO_FOR_RUNTIME_ATTACHMENT" if conflicts or len(candidates)>1 else "RETURN_TO_ECC_WITH_EXACT_REMAINING_GAP")

SENSITIVE = [re.compile(x,re.I) for x in (r"\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b",r"\b(?:\d{1,3}\.){3}\d{1,3}(?::5555)?\b",
              r"\b(?:[0-9a-f]{1,4}:){2,}[0-9a-f:]*[0-9a-f]\b|\b[0-9a-f]{1,4}::[0-9a-f]{1,4}\b",r"(?:ssid|password|private.key|token)\s*[:=]")]
def privacy_scan(text: str) -> None:
    if any(p.search(text) for p in SENSITIVE): raise FormatError("PRIVACY_GATE_FAILED")

def public_summary(decision: dict, status: str, identity: str, snapshots: dict) -> dict:
    clean=json.loads(json.dumps(decision))
    for delta in clean["phase_deltas"]:
        delta["ipv4_added"]=["IPv4_ADDRESS_WITHHELD"]*len(delta["ipv4_added"])
        delta["ipv6_added"]=["IPv6_LINK_LOCAL_WITHHELD" if ipaddress.IPv6Address(v).is_link_local else "IPv6_ADDRESS_WITHHELD" for v in delta["ipv6_added"]]
    if clean["candidate_route_policy"]: clean["candidate_route_policy"]["local_address"]="WITHHELD"
    clean.update(capture_status=status,identity_status=identity,completed_phases=[p for p in PHASES if p in snapshots and snapshots[p].complete],
                 interfaces=sorted({name for s in snapshots.values() for name in s.interfaces}),limitations=["G11-E and G11-F unresolved by observational capture"],privacy_status="SANITIZED")
    privacy_scan(json.dumps(clean))
    return clean
