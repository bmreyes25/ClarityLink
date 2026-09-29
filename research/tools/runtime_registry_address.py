#!/usr/bin/env python3
"""Derive current PIE load bias and mc_devs cell from saved proc maps + exact ELF."""
import argparse, os, re, subprocess, sys

def main():
    p=argparse.ArgumentParser();p.add_argument("maps");p.add_argument("elf");p.add_argument("--static-va",default="0x35acbc");a=p.parse_args()
    text=subprocess.check_output(["readelf","-lW",a.elf],text=True)
    loads=[]
    for line in text.splitlines():
        m=re.match(r"\s*LOAD\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)",line)
        if m: loads.append((int(m.group(1),16),int(m.group(2),16)))
    maps=[]
    for line in open(a.maps,errors="replace"):
        m=re.match(r"([0-9a-fA-F]+)-([0-9a-fA-F]+)\s+(\S+)\s+([0-9a-fA-F]+)\s+\S+\s+\S+\s*(.*)",line)
        if m and os.path.basename(m.group(5).strip())==os.path.basename(a.elf):
            maps.append((int(m.group(1),16),int(m.group(4),16)))
    # ARMv7 Android uses 4 KiB ELF mapping alignment; do not use the Mac host page size.
    page=4096; biases=set()
    for start,off in maps:
        for fileoff,vaddr in loads:
            if fileoff//page*page==off: biases.add(start-(vaddr//page*page))
    if len(biases)!=1: sys.exit("cannot determine unique load bias; verify ELF identity and mappings")
    bias=biases.pop();cell=bias+int(a.static_va,0)
    print("LOAD_BIAS=0x%x"%bias);print("MC_DEVS_CELL=0x%x"%cell)
    if cell>0xffffffff: sys.exit("cell is outside 32-bit address range")
if __name__=="__main__":main()
