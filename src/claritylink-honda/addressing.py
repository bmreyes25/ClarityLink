"""Synthetic /proc/maps address resolution; never reads live process maps."""
from dataclasses import dataclass

U32_MAX=(1<<32)-1
class AddressResolutionError(ValueError): pass
@dataclass(frozen=True)
class ProcMap:
    start:int; end:int; permissions:str; offset:int; path:str
@dataclass(frozen=True)
class LoadSegment:
    offset:int; vaddr:int; filesz:int; memsz:int; flags:int

def parse_maps(text:str)->tuple[ProcMap,...]:
    result=[]
    for line in text.splitlines():
        parts=line.split(None,5)
        if len(parts)<5: raise AddressResolutionError("malformed maps line")
        try:
            bounds,perms,off=parts[:3]; lo,hi=(int(v,16) for v in bounds.split("-")); offset=int(off,16)
        except Exception as exc: raise AddressResolutionError("malformed maps address") from exc
        path=parts[5] if len(parts)>5 else ""
        if lo>=hi: raise AddressResolutionError("empty or reversed mapping")
        result.append(ProcMap(lo,hi,perms,offset,path))
    return tuple(result)

def resolve_runtime_address(static_va:int,mappings:tuple[ProcMap,...],segments:tuple[LoadSegment,...],expected_path:str,*,page_size=4096)->int:
    if isinstance(static_va,bool) or not isinstance(static_va,int) or not 0<=static_va<=U32_MAX: raise AddressResolutionError("static address outside uint32")
    thumb=static_va&1; va=static_va&~1
    candidates=[s for s in segments if s.flags&1 and s.vaddr<=va<s.vaddr+s.memsz]
    if len(candidates)!=1: raise AddressResolutionError("no unique executable PT_LOAD contains target")
    seg=candidates[0]; file_page=seg.offset//page_size*page_size; vaddr_page=seg.vaddr//page_size*page_size
    maps=[m for m in mappings if m.path==expected_path and "x" in m.permissions and m.offset==file_page]
    if len(maps)!=1: raise AddressResolutionError("missing or ambiguous executable mapping")
    mapping=maps[0]; bias=mapping.start-vaddr_page
    if bias<0: raise AddressResolutionError("invalid negative load bias")
    runtime=bias+va
    if runtime>U32_MAX or not mapping.start<=runtime<mapping.end: raise AddressResolutionError("resolved address outside mapped executable range")
    return runtime|thumb
