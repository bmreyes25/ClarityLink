import sys,pathlib,json,re,hashlib
sys.path.insert(0,str(pathlib.Path('research/tools/python').resolve()))
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM,CS_MODE_THUMB,CS_MODE_LITTLE_ENDIAN
root=pathlib.Path('extracted/system-vendor/system');out=pathlib.Path('research/native')
terms=re.compile(r'carplay|iap2?|apple|navig|route|guidance|maneuver|turn|secondary|second.?display|external.?display|cluster|meter|map|video|h264|framebuffer|display.?stream|audio|siri|lvds|screen|fb[01]|disp_com',re.I)
paths=[root/'lib/libcarplay_proxy.so',root/'vendor/bin/disp_com_meter',root/'bin/jmcs',root/'vendor/bin/nativevideo']
paths += [p for p in (root/'lib').glob('*') if p.is_file() and not p.is_symlink() and any(k in p.name.lower() for k in ['nativevideo','dispcom','xposed'])]
manifest=[]
for p in paths:
 data=p.read_bytes();dest=out/p.name;dest.mkdir(exist_ok=True)
 strings=[{'offset':hex(m.start()),'text':m.group().decode('ascii')} for m in re.finditer(rb'[\x20-\x7e]{4,}',data)]
 (dest/'strings.txt').write_text('\n'.join(f"{s['offset']}\t{s['text']}" for s in strings))
 (dest/'keyword-strings.txt').write_text('\n'.join(f"{s['offset']}\t{s['text']}" for s in strings if terms.search(s['text'])))
 with p.open('rb') as f:
  elf=ELFFile(f);symbols=[];seen=set();assembly=[];dwarf=[]
  for sec in elf.iter_sections():
   if sec['sh_type'] in ['SHT_DYNSYM','SHT_SYMTAB']:
    for s in sec.iter_symbols():
     key=(s.name,s['st_value'])
     if key in seen:continue
     seen.add(key);row={'name':s.name,'value':hex(s['st_value']),'size':s['st_size'],'type':s['st_info']['type'],'section':s['st_shndx']};symbols.append(row)
     if s['st_info']['type']=='STT_FUNC' and isinstance(s['st_shndx'],int) and (p.name!='jmcs' or terms.search(s.name)):
      code=elf.get_section(s['st_shndx']);v=s['st_value']&~1;off=v-code['sh_addr'];size=s['st_size']
      if size and off>=0:
       md=Cs(CS_ARCH_ARM,(CS_MODE_THUMB if s['st_value']&1 else CS_MODE_ARM)|CS_MODE_LITTLE_ENDIAN)
       assembly.append('\nFUNCTION '+s.name+' '+hex(s['st_value'])+' file '+hex(code['sh_offset']+off))
       assembly.extend(f'{i.address:08x}: {i.mnemonic:9} {i.op_str}' for i in md.disasm(code.data()[off:off+size],v))
  (dest/'symbols.json').write_text(json.dumps(symbols,indent=2));(dest/'disassembly.txt').write_text('\n'.join(assembly))
  if elf.has_dwarf_info():
   for cu in elf.get_dwarf_info().iter_CUs():
    top=cu.get_top_DIE();attrs=top.attributes
    dwarf.append({k:str(attrs[k].value) for k in ['DW_AT_name','DW_AT_comp_dir','DW_AT_producer'] if k in attrs})
  (dest/'compile-units.json').write_text(json.dumps(dwarf,indent=2))
  deps=[]
  dyn=elf.get_section_by_name('.dynamic')
  if dyn:
   deps=[t.needed for t in dyn.iter_tags() if t.entry.d_tag=='DT_NEEDED']
  manifest.append({'path':str(p),'sha256':hashlib.sha256(data).hexdigest(),'needed':deps,'symbols':len(symbols),'compile_units':len(dwarf)})
 print(p.name,len(symbols),'symbols',flush=True)
(out/'manifest.json').write_text(json.dumps(manifest,indent=2))
