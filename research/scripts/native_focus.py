import sys,pathlib,json,struct,re
sys.path.insert(0,str(pathlib.Path('research/tools/python').resolve()))
from elftools.elf.elffile import ELFFile
from capstone import *
from capstone.arm import *
root=pathlib.Path('extracted/system-vendor/system')
def analyze(p,names=None,extra=[]):
 with p.open('rb') as f:
  elf=ELFFile(f);data=p.read_bytes();symbols=[];lookup={}
  for sec in elf.iter_sections():
   if sec['sh_type'] in ['SHT_DYNSYM','SHT_SYMTAB']:
    for s in sec.iter_symbols():
     if s['st_value']:lookup[s['st_value']&~1]=s.name
     if s['st_info']['type']=='STT_FUNC' and s['st_size'] and (names is None or names.search(s.name)):symbols.append((s.name,s['st_value'],s['st_size']))
  def read(addr,n):
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD' and seg['p_vaddr']<=addr and addr+n<=seg['p_vaddr']+seg['p_filesz']:
     off=seg['p_offset']+addr-seg['p_vaddr'];return data[off:off+n]
   return b''
  def word(a):
   b=read(a,4);return struct.unpack('<I',b)[0] if len(b)==4 else None
  def desc(a):
   if a in lookup:return lookup[a]
   b=read(a,160).split(b'\0')[0]
   if len(b)>3 and all(32<=c<127 for c in b):return repr(b.decode())
   return ''
  if p.name=='app_process':
   for sec in elf.iter_sections():
    if sec['sh_type']=='SHT_PROGBITS' and sec['sh_flags']&2:
     b=sec.data()
     for off in range(0,len(b)-12,4):
      a,sg,fn=struct.unpack_from('<III',b,off)
      if desc(a) in ["'decrypt'","'encrypt'"]:
       symbols.append((desc(a),fn,256));print('JNI',hex(sec['sh_addr']+off),desc(a),desc(sg),hex(fn))
  symbols+=extra;result=[]
  for name,addr,size in dict.fromkeys(symbols):
   md=Cs(CS_ARCH_ARM,CS_MODE_THUMB if addr&1 else CS_MODE_ARM);md.detail=True;regs={};result.append('\nFUNCTION '+name+' '+hex(addr))
   for ins in md.disasm(read(addr&~1,size),addr&~1):
    ops=ins.operands;notes=[];pc=ins.address+(4 if addr&1 else 8)
    if ins.mnemonic.startswith('ldr') and len(ops)>1 and ops[0].type==ARM_OP_REG and ops[1].type==ARM_OP_MEM:
     mem=ops[1].mem;base=(pc&~3) if mem.base==ARM_REG_PC else regs.get(mem.base)
     if base is not None and not mem.index:
      val=word((base+mem.disp)&0xffffffff)
      if val is not None:regs[ops[0].reg]=val;notes.append(hex(val)+' '+desc(val))
    elif ins.mnemonic in ['add','adds','add.w'] and len(ops)>=2 and ops[0].type==ARM_OP_REG:
     sources=[ops[0],ops[1]] if len(ops)==2 else ops[1:]
     vals=[o.imm if o.type==ARM_OP_IMM else (pc if o.reg==ARM_REG_PC else regs.get(o.reg)) if o.type==ARM_OP_REG else None for o in sources]
     if all(v is not None for v in vals):
      val=sum(vals)&0xffffffff;regs[ops[0].reg]=val;notes.append(hex(val)+' '+desc(val))
    elif ins.mnemonic.startswith('mov') and len(ops)>1 and ops[0].type==ARM_OP_REG:
     o=ops[1];v=o.imm if o.type==ARM_OP_IMM else regs.get(o.reg)
     if v is not None:regs[ops[0].reg]=v
    if ins.mnemonic.startswith('bl') and ops and ops[0].type==ARM_OP_IMM:
     notes.append(lookup.get(ops[0].imm,''))
     for reg in [ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3]:
      if reg in regs and desc(regs[reg]):notes.append(ins.reg_name(reg)+'='+desc(regs[reg]))
     for reg in [ARM_REG_R0,ARM_REG_R1,ARM_REG_R2,ARM_REG_R3]:regs.pop(reg,None)
    result.append(f'{ins.address:08x}: {ins.mnemonic:9} {ins.op_str}'+(' ; '+' | '.join(n for n in notes if n) if notes else ''))
  dest=pathlib.Path('research/native')/p.name;dest.mkdir(exist_ok=True);(dest/'focused-annotated.txt').write_text('\n'.join(result))
analyze(root/'bin/jmcs',re.compile(r'iface_to_airplay_resource_change|screen_add_props|mc_carplay_app_init|mc_carplay_screen_init|mc_carplay_screen_stream_init_instance|mc_ScreenStreamInitialize|AirPlayReceiverSessionScreen_CopyDisplaysInfo|ScreenCopyMain|init_identification_global_params|ipod_attach_identification_params|ios_iap2_set_identified|ScreenRegister'))
analyze(root/'bin/app_process',re.compile('nevermatch'))
