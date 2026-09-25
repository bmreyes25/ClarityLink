from pathlib import Path
import re,json
root=Path('research')
terms=['carplay','iap','iap2','apple','navigation','route','guidance','maneuver','turn','secondary','second display','external display','cluster','meter','map','video','h264','framebuffer','display stream','audio','siri']
pat=re.compile('|'.join(re.escape(t).replace(r'\ ',r'[ _-]?') for t in terms),re.I)
sets={'factory-java':root/'decompiled-clean','hondahack-java':root/'decompiled/cn.autohack.hondahack-2/sources','resource-xml':root/'resources'}
summary={}
for name,base in sets.items():
 rows=[];counts={t:0 for t in terms}
 for p in base.rglob('*'):
  if not p.is_file() or p.suffix not in ['.java','.xml','.smali']:continue
  try:lines=p.read_text(errors='replace').splitlines()
  except OSError:continue
  for n,line in enumerate(lines,1):
   found=pat.findall(line)
   if found:
    for t in terms:
     if re.search(re.escape(t).replace(r'\ ',r'[ _-]?'),line,re.I):counts[t]+=1
    if len(line)>1000:line=line[:1000]+'…'
    rows.append(f'{p.relative_to(root)}:{n}: {line.strip()}')
 dest=root/'search'/f'{name}-hits.txt';dest.write_text('\n'.join(rows)+'\n')
 summary[name]={'files':len(list(base.rglob('*'))),'lines':len(rows),'term_line_counts':counts}
(root/'search'/'search-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v['lines'] for k,v in summary.items()}))
