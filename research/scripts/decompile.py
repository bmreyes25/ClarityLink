import subprocess, pathlib, concurrent.futures, json, os
root=pathlib.Path.cwd()
java=root/'research/tools/java/jdk-17.0.20.1+1-jre/Contents/Home/bin/java'
base=[str(java),'-Xmx1400m','-Duser.home='+str(root/'research/tools/home'),'-Djava.io.tmpdir='+str(root/'research/tmp'),'-cp',str(root/'research/tools/jadx/lib/*'),'jadx.cli.JadxCLI','-j','2','--no-inline-methods','--no-inline-anonymous']
files=list((root/'research/extracted').glob('*.dex'))+list((root/'research/extracted').glob('*.apk'))
def run(p):
 out=root/'research/decompiled'/p.stem
 with (root/'research/logs'/(p.stem+'-jadx.log')).open('w') as log:
  r=subprocess.run(base+['-d',str(out),str(p)],stdout=log,stderr=subprocess.STDOUT)
 print(p.name,r.returncode,flush=True)
 return {'input':str(p.relative_to(root)),'exit_code':r.returncode,'output':str(out.relative_to(root))}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,files))
(root/'research/logs/jadx-results.json').write_text(json.dumps(results,indent=2))
