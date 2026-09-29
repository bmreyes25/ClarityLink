#!/usr/bin/env python3
"""Resolve callback pointers from a reader JSON file and saved proc maps."""
import argparse, json, os, re, subprocess, sys

MAP = re.compile(r"^([0-9a-f]+)-([0-9a-f]+)\s+(\S+)\s+([0-9a-f]+)\s+\S+\s+\S+\s*(.*)$")
LOAD = re.compile(r"LOAD\s+0x([0-9a-f]+)\s+0x([0-9a-f]+)")

def run(*args):
    try: return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError): return ""

def load_bias(path, maps_for_file):
    ph = run("readelf", "-lW", path)
    segs = [(int(a,16),int(b,16)) for a,b in LOAD.findall(ph)]
    page = 4096
    biases=[]
    for m in maps_for_file:
        for off,vaddr in segs:
            if (off & ~(page-1)) == m[3]: biases.append(m[0]-(vaddr & ~(page-1)))
    return biases[0] if biases else None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("reader_json"); ap.add_argument("maps"); ap.add_argument("--module-dir", action="append", default=[]); a=ap.parse_args()
    data=json.load(open(a.reader_json)); maps=[]
    for line in open(a.maps, errors="replace"):
        m=MAP.match(line.rstrip())
        if m and m.group(3)[0]=='r':
            path=m.group(6).strip()
            if path.endswith(" (deleted)"): path=path[:-10]
            maps.append((int(m.group(1),16),int(m.group(2),16),m.group(3),int(m.group(4),16),path))
    files={}
    for m in maps:
        if m[4].startswith("/"): files.setdefault(m[4],[]).append(m)
    search=a.module_dir+["."]
    resolved={}
    for p,ms in files.items():
        candidates=[p]+[os.path.join(d,os.path.basename(p)) for d in search]
        elf=next((x for x in candidates if os.path.isfile(x)),None)
        if elf: resolved[p]=(elf,load_bias(elf,ms))
    symcache={}
    for e in data.get("entries",[]):
        for field in ("matcher","attach"):
            ptr=int(e[field],16); normalized=ptr & ~1
            mp=next((m for m in maps if m[0]<=normalized<m[1]),None)
            record={"RUNTIME_ADDRESS":e[field],"MODULE":mp[4] if mp else None,"MODULE_LOAD_BIAS":None,"STATIC_VA/OFFSET":None,"SYMBOL":None,"DWARF_FUNCTION":None}
            if mp and mp[4] in resolved:
                elf,bias=resolved[mp[4]]; record["MODULE_LOAD_BIAS"]=hex(bias) if bias is not None else None
                if bias is not None:
                    va=normalized-bias; record["STATIC_VA/OFFSET"]=hex(va)
                    if elf not in symcache: symcache[elf]=run("nm","-nC",elf)
                    preceding=[]
                    for ln in symcache[elf].splitlines():
                        cols=ln.split(None,2)
                        if len(cols)>=3:
                            try:
                                addr=int(cols[0],16)
                                if addr<=va: preceding.append((addr,cols[2]))
                            except ValueError: pass
                    if preceding: record["SYMBOL"]=max(preceding)[1]
                    dwarf=run("addr2line","-f","-C","-e",elf,hex(va)).splitlines()
                    if dwarf: record["DWARF_FUNCTION"]=dwarf[0]
            e[field+"_resolution"]=record
    json.dump(data,sys.stdout,indent=2);print()
if __name__=="__main__": main()
