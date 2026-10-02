"""43T0-D host-only offline analysis. Reads a D0 capture; never executes device commands."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from step43t0d_offline import (COLLECTOR_HASH, FILES, IDENTITY, KERNEL_HASH, NETWORK, PHASES,
    PLAN_COMMIT, PROPERTIES, RESULTS, SHELL_HASH, FormatError, decide, privacy_scan, public_summary, snapshot)

ROOT = Path(__file__).resolve().parents[1]
MAX_MANIFEST = 131072
MAX_FILE = 65536


def expected() -> list[tuple[str, tuple[str,...], str]]:
    rows=[("preflight", ("devices",), "preflight/devices.raw")]
    rows.extend(("identity", suffix, "identity/"+name) for name,suffix in IDENTITY)
    rows.extend((phase, suffix, phase+"/"+name) for phase in PHASES for suffix,name in zip(NETWORK,FILES,strict=True))
    return rows


def safe_file(root: Path, relative: str, max_bytes: int = MAX_FILE) -> bytes:
    path=Path(relative)
    if path.is_absolute() or any(part in (".","..") for part in path.parts) or not path.parts:
        raise FormatError("unsafe path")
    current=root
    for part in path.parts:
        current=current/part
        if current.is_symlink(): raise FormatError("symlink input")
    if not current.is_file() or current.stat().st_size>max_bytes:
        raise FormatError("missing/oversized input")
    with current.open("rb") as stream: data=stream.read(max_bytes+1)
    if len(data)>max_bytes: raise FormatError("oversized input")
    return data


def validate_capture(root: Path) -> tuple[str,str,dict,dict]:
    if not root.is_dir() or root.is_symlink(): raise FormatError("capture root")
    def unique_object(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise FormatError("duplicate manifest key")
            result[key]=value
        return result
    manifest=json.loads(safe_file(root,"manifest.json",MAX_MANIFEST),object_pairs_hook=unique_object,
                        parse_constant=lambda _value: (_ for _ in ()).throw(FormatError("invalid JSON constant")))
    if not isinstance(manifest,dict) or manifest.get("collector_version")!="43T0-D0-1" or manifest.get("collector_source_sha256")!=COLLECTOR_HASH or manifest.get("approved_plan_commit")!=PLAN_COMMIT:
        raise FormatError("collector provenance")
    if not re.fullmatch(r"[0-9a-f]{40}",manifest.get("project_commit","")):
        raise FormatError("project commit")
    commands=manifest.get("commands")
    if not isinstance(commands,list) or len(commands)>23: raise FormatError("command count")
    planned=expected(); raw={}; successful={}; endpoint=None
    for i,row in enumerate(commands):
        if not isinstance(row,dict) or row.get("command_index")!=i+1 or row.get("phase")!=planned[i][0] or row.get("target_reference")!="redacted":
            raise FormatError("sequence/index/target reference")
        phase,suffix,relative=planned[i]
        argv=row.get("argv")
        if i==0:
            if argv!=["adb","devices"]: raise FormatError("unapproved enumeration")
        else:
            if not isinstance(argv,list) or len(argv)!=3+len(suffix) or argv[:2]!=["adb","-s"] or argv[3:]!=list(suffix) or argv[2]!=endpoint:
                raise FormatError("unapproved command")
        if row.get("result_class") not in RESULTS or row.get("stdout_bytes") not in range(MAX_FILE+1) or row.get("stderr_bytes") not in range(MAX_FILE+1) or row["stdout_bytes"]+row["stderr_bytes"]>MAX_FILE:
            raise FormatError("result/size")
        data=safe_file(root,relative)
        if len(data)!=row["stdout_bytes"] or hashlib.sha256(data).hexdigest()!=row.get("stdout_sha256"):
            raise FormatError("stdout integrity")
        err_rel=relative+".stderr.raw"
        err=safe_file(root,err_rel) if row["stderr_bytes"] else b""
        if len(err)!=row["stderr_bytes"] or hashlib.sha256(err).hexdigest()!=row.get("stderr_sha256"):
            raise FormatError("stderr integrity")
        raw[relative]=data
        if row["result_class"]=="SUCCESS": successful[relative]=data
        if i==0 and row["result_class"]=="SUCCESS":
            try:
                lines=data.decode("utf-8","strict").splitlines()
                if len(lines)!=2 or lines[0].strip()!="List of devices attached": raise ValueError
                token,state=lines[1].split()
                if state!="device" or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}",token): raise ValueError
                endpoint=token
            except (ValueError,UnicodeError):
                if len(commands)>1: raise FormatError("preflight target format") from None
        if row["result_class"]!="SUCCESS" and i!=len(commands)-1:
            raise FormatError("commands after failed result")
    # Reject unrecorded files and symlinks, including hidden extras.
    allowed={"manifest.json"}|set(raw)
    allowed|={planned[i][2]+".stderr.raw" for i,row in enumerate(commands) if row["stderr_bytes"]}
    permitted_dirs={"preflight","identity",*PHASES}
    count=0
    for path in root.rglob("*"):
        count+=1
        if count>64: raise FormatError("too many entries")
        if path.is_symlink(): raise FormatError("symlink in capture")
        relative=path.relative_to(root).as_posix()
        if path.is_dir() and relative not in permitted_dirs: raise FormatError("unexpected directory")
        if path.is_file() and relative not in allowed: raise FormatError("unexpected file")
    final=manifest.get("final_status")
    if final not in RESULTS and final is not None: raise FormatError("final status")
    if len(commands)==23 and all(r["result_class"]=="SUCCESS" for r in commands):
        if final!="SUCCESS": raise FormatError("final status inconsistent")
        status="CAPTURE_VALID"
    else:
        if final=="SUCCESS" or (commands and commands[-1]["result_class"]!="SUCCESS" and final!=commands[-1]["result_class"]):
            raise FormatError("partial status inconsistent")
        status="CAPTURE_VALID_PARTIAL"
    identity=validate_identity(successful)
    if any(p in raw for p in ("baseline/net-dev.raw","connected/net-dev.raw","post-disconnect/net-dev.raw")) and identity!="IDENTITY_MATCH":
        raise FormatError("network preceded identity gate")
    return status,identity,manifest,successful


def validate_identity(raw: dict) -> str:
    keys=["identity/"+name for name,_ in IDENTITY]
    if any(k not in raw for k in keys): return "IDENTITY_INCOMPLETE"
    try:
        values=[raw[k].decode("utf-8","strict").rstrip("\r\n") for k in keys]
    except UnicodeError: return "IDENTITY_INCOMPLETE"
    if not values[0].startswith("uid=2000(shell) gid=2000(shell)"):
        return "IDENTITY_MISMATCH"
    if hashlib.sha256(values[0].encode()).hexdigest()!=SHELL_HASH or hashlib.sha256(values[1].encode()).hexdigest()!=KERNEL_HASH:
        return "IDENTITY_MISMATCH"
    return "IDENTITY_MATCH" if tuple(values[2:])==PROPERTIES else "IDENTITY_MISMATCH"


def render_report(summary: dict, manifest: dict) -> str:
    gates="\n".join(f"| {key} | {summary[key]} |" for key in ("G11_A","G11_B","G11_C","G11_D","G11_E","G11_F"))
    text=f"""# Step 43T0-D — read-only Honda network delta analysis

Capture status: **{summary['capture_status']}**. Identity: **{summary['identity_status']}**.
Starting HEAD recorded by collector: `{manifest['project_commit']}`. Honda contacted by target command: {'YES' if len(manifest['commands'])>1 else 'NO'}; ADB used: {'YES' if manifest['commands'] else 'NO'}. Target writes: **0** under the reviewed command contract. Root/su: **NO**.

Phases completed: {', '.join(summary['completed_phases']) or 'none'}. Command count: {len(manifest['commands'])}. Final stock sanity: {'collector SUCCESS' if manifest['final_status']=='SUCCESS' else 'not established by analyzer'}. CAR-OFF boundary: operator must issue the exact runbook message after collector exit.

## Interface, address, route, and 40E findings

Candidate state: {summary['candidate_state']}; interface: {summary['candidate_interface'] or 'none'}; family: {summary['candidate_address_family']}. IPv4 and IPv6 exact addresses are withheld. Route policy: {summary['G11_D']}. 40E correlation: stock CarPlay IPv6 link-local global socket rows; process ownership remains blocked.

## G11

| Gate | Result |
|---|---|
{gates}

Candidate binding policy: {json.dumps(summary['candidate_route_policy'],sort_keys=True) if summary['candidate_route_policy'] else 'none'}.

## Boundaries

Reversibility: {'phase reversal observed' if any(d['phase_reversal_correlation'] for d in summary['phase_deltas']) else 'not established'}. Privacy: {summary['privacy_status']}. Limitations: {', '.join(summary['limitations'])}. Type111 and listener reachability untested.

Next recommendation: **{summary['next_recommendation']}**. No vehicle action follows automatically.
"""
    privacy_scan(text)
    return text


def analyze(capture: Path, output: Path, *, private_binding_detail: bool = False) -> dict:
    if output.resolve()==capture.resolve() or output.resolve().is_relative_to(capture.resolve()) or capture.resolve().is_relative_to(output.resolve()):
        raise FormatError("output must be separate")
    status,identity,manifest,raw=validate_capture(capture)
    snapshots={}
    if identity=="IDENTITY_MATCH":
        for phase in PHASES:
            subset={name:raw[phase+"/"+name] for name in FILES if phase+"/"+name in raw}
            if subset: snapshots[phase]=snapshot(phase,subset)
    decision=decide(snapshots)
    private_policy=decide(snapshots,private=True)["candidate_route_policy"] if private_binding_detail else None
    summary=public_summary(decision,status,identity,snapshots)
    # No output until all validation and privacy gates pass.
    if private_binding_detail and output.resolve().is_relative_to(ROOT):
        raise FormatError("private detail must stay outside Git")
    report=render_report(summary,manifest)
    if output.exists(): raise FormatError("output exists")
    output.mkdir(mode=0o700,parents=False)
    os.chmod(output,0o700)
    (output/"43t0d-network-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    (output/"43t0d-read-only-honda-network-delta.md").write_text(report)
    if private_binding_detail:
        (output/"PRIVATE_BINDING_DETAIL.json").write_text(json.dumps(private_policy,indent=2,sort_keys=True)+"\n")
    for path in output.iterdir(): path.chmod(0o600)
    return summary


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture",type=Path,required=True)
    parser.add_argument("--40e-capture",type=Path,help="optional immutable 40E bundle; correlation uses the verified sanitized 43T0-A facts")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--private-binding-detail",action="store_true")
    args=parser.parse_args()
    try:
        prior=args.__dict__["40e_capture"]
        if prior is not None:
            if not prior.is_dir() or prior.is_symlink(): raise FormatError("40E reference directory")
            if hashlib.sha256(safe_file(prior,"manifest.json",1048576)).hexdigest()!="248427ae4d5dc7ce75888425ab254d308c68e6021a3032a62877c92ef3811f77":
                raise FormatError("40E manifest checksum mismatch")
        result=analyze(args.capture,args.output,private_binding_detail=args.private_binding_detail)
    except (FormatError,ValueError,UnicodeError,OSError,TypeError,KeyError) as exc:
        print("CAPTURE_INVALID: " + str(exc)); raise SystemExit(2) from None
    print(result["capture_status"]+": "+str(args.output))

if __name__=="__main__": main()
