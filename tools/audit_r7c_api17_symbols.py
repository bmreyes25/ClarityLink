#!/usr/bin/env python3
"""Audit R7C Android ARM imports against API17 Bionic and libandroid stubs."""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

def run(*cmd):
    return subprocess.run(cmd, check=True, text=True, capture_output=True).stdout

def main():
    p=argparse.ArgumentParser(); p.add_argument("artifact",type=Path); p.add_argument("--ndk",type=Path,required=True); a=p.parse_args()
    pre=a.ndk/"toolchains/llvm/prebuilt/darwin-x86_64"; re=pre/"bin/llvm-readelf"; nm=pre/"bin/llvm-nm"
    stub=pre/"sysroot/usr/lib/arm-linux-androideabi/17"; dyn=run(str(re),"--dyn-syms","--wide",str(a.artifact))
    imports=set()
    for line in dyn.splitlines():
        f=line.split()
        if len(f)>=8 and f[6]=="UND": imports.add(f[7].split("@",1)[0])
    provided=set(); libs={}
    for name in ("libc.so","libm.so","libdl.so","libandroid.so"):
        path=stub/name
        if not path.exists(): continue
        syms=run(str(nm),"-D","--defined-only",str(path))
        libs[name]=sorted({x.split()[-1].split("@",1)[0] for x in syms.splitlines() if x.split()})
        provided.update(libs[name])
    unknown=sorted(imports-provided)
    result={"artifact":a.artifact.name,"sha256":hashlib.sha256(a.artifact.read_bytes()).hexdigest(),"api":17,
            "checked_stubs":sorted(libs),"unknown":unknown,
            "classifications":{s:("API17_AVAILABLE" if s in provided else "UNKNOWN") for s in sorted(imports)}}
    print(json.dumps(result,indent=2)); return 1 if unknown else 0
if __name__=="__main__": sys.exit(main())
