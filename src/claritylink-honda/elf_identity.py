"""Minimal read-only ELF32 identity inspector for offline jmcs verification."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import struct

class ELFError(ValueError): pass

@dataclass(frozen=True)
class LoadSegment:
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int

@dataclass(frozen=True)
class HondaBuildIdentity:
    elf_sha256: str
    text_sha256: str
    file_size: int
    elf_class: int
    endian: str
    machine: int
    elf_type: int
    build_id: bytes | None

@dataclass(frozen=True)
class ELFInspection:
    identity: HondaBuildIdentity
    load_segments: tuple[LoadSegment, ...]
    text_vaddr: int
    text_offset: int

def inspect_elf32(data: bytes) -> ELFInspection:
    if len(data) < 52 or data[:4] != b"\x7fELF": raise ELFError("not a complete ELF file")
    if data[4] != 1: raise ELFError("only ELF32 is supported by this offline inspector")
    if data[5] not in (1,2): raise ELFError("unknown ELF byte order")
    endian="little" if data[5]==1 else "big"; order="<" if endian=="little" else ">"
    e_type,machine=struct.unpack_from(order+"HH",data,16)
    phoff,shoff=struct.unpack_from(order+"II",data,28)
    ehsize,phentsize,phnum,shentsize,shnum,shstrndx=struct.unpack_from(order+"HHHHHH",data,40)
    if ehsize<52 or (phentsize<32 and phnum) or (shentsize<40 and shnum): raise ELFError("invalid ELF table sizes")
    if phoff+phentsize*phnum>len(data) or shoff+shentsize*shnum>len(data): raise ELFError("ELF table outside file")
    segments=[]
    for i in range(phnum):
        p_type,offset,vaddr,_paddr,filesz,memsz,flags,_align=struct.unpack_from(order+"IIIIIIII",data,phoff+i*phentsize)
        if p_type==1:
            if offset+filesz>len(data) or filesz>memsz: raise ELFError("invalid PT_LOAD segment")
            segments.append(LoadSegment(offset,vaddr,filesz,memsz,flags))
    if not shnum or shstrndx>=shnum: raise ELFError("missing section-name table")
    sections=[struct.unpack_from(order+"IIIIIIIIII",data,shoff+i*shentsize) for i in range(shnum)]
    names_sec=sections[shstrndx]; names=data[names_sec[4]:names_sec[4]+names_sec[5]]
    text=None; text_vaddr=None; text_offset=None; build_id=None
    for sec in sections:
        nameoff,stype,_flags,_addr,offset,size,*_=sec
        end=names.find(b"\0",nameoff)
        name=names[nameoff:end].decode("ascii","replace") if nameoff<len(names) and end>=0 else ""
        if offset+size>len(data) and stype!=8: raise ELFError(f"section {name} outside file")
        payload=data[offset:offset+size] if stype!=8 else b""
        if name==".text": text=payload; text_vaddr=_addr; text_offset=offset
        if stype==7 and build_id is None:
            cursor=0
            while cursor+12<=len(payload):
                namesz,descsz,ntype=struct.unpack_from(order+"III",payload,cursor); cursor+=12
                nend=cursor+namesz; note_name=payload[cursor:nend].rstrip(b"\0")
                cursor=(nend+3)&~3; dend=cursor+descsz
                if dend>len(payload): break
                desc=payload[cursor:dend]; cursor=(dend+3)&~3
                if note_name==b"GNU" and ntype==3: build_id=desc; break
    if text is None: raise ELFError("ELF has no .text section")
    identity=HondaBuildIdentity(hashlib.sha256(data).hexdigest(),hashlib.sha256(text).hexdigest(),len(data),32,endian,machine,e_type,build_id)
    assert text_vaddr is not None and text_offset is not None
    return ELFInspection(identity,tuple(segments),text_vaddr,text_offset)
