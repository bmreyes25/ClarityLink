import pathlib, subprocess, concurrent.futures,json
r=pathlib.Path.cwd();java=str(r/'research/tools/java/jdk-17.0.20.1+1-jre/Contents/Home/bin/java')
base=[java,'-Xmx1800m','-Duser.home='+str(r/'research/tools/home'),'-Djava.io.tmpdir='+str(r/'research/tmp')]
cp=str(r/'research/tools/smali/*');src=r/'extracted/system-vendor/system'
inputs=[p for d in ['vendor/app','vendor/framework'] for p in (src/d).glob('*.odex') if any(k in p.name for k in ['CarPlay','ExternalDisplay','Navigation','MediaCore','NativeVideo','PhoneCoordination'])]
(r/'research/deodexed').mkdir(exist_ok=True)
def run(p):
 name=p.stem;out=r/'research/smali'/name;dex=r/'research/deodexed'/(name+'.dex');res={'name':name}
 stages=[('baksmali',base+['-cp',cp,'org.jf.baksmali.Main','deodex','-a','17','-j','2','-d',str(src/'framework'),'-d',str(src/'vendor/framework'),'-o',str(out),str(p)]),('assemble',base+['-cp',cp,'org.jf.smali.Main','assemble','-a','17','-j','2','-o',str(dex),str(out)]),('jadx-clean',base+['-cp',str(r/'research/tools/jadx/lib/*'),'jadx.cli.JadxCLI','-j','2','--no-inline-methods','--no-inline-anonymous','-d',str(r/'research/decompiled-clean'/name),str(dex)])]
 for stage,cmd in stages:
  with (r/'research/logs'/(name+'-'+stage+'.log')).open('w') as log:s=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  res[stage]=s.returncode
  if s.returncode and stage!='jadx-clean':break
 print(res,flush=True);return res
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:results=list(ex.map(run,inputs))
(r/'research/logs/deodex-results.json').write_text(json.dumps(results,indent=2))
