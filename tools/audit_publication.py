"""Inspect every reachable Git blob before a visibility change.

Outputs locations and categories only, never credential values. This is a
focused publication check, not a guarantee that every possible secret is found.
"""
import io,json,re,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIT=['git','-c','safe.directory='+ROOT.as_posix()]
PATTERNS={
 'credential':rb'(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',
 'download_token':rb'https?://[^\s"<>]+[?&]token=[A-Za-z0-9_\-]{16,}',
 'personal_path':rb'(?:[A-Z]:[/\\]Users[/\\][^/\\\s"<>]+|/home/[^/\s"<>]+)',
}
def main():
 listing=subprocess.check_output(GIT+['rev-list','--objects','--all'],cwd=ROOT).splitlines()
 names={};oids=[]
 for line in listing:
  oid,_,name=line.partition(b' ');oids.append(oid);names[oid.decode()]=name.decode('utf-8','replace')
 # Include newly staged content, before it becomes reachable through a commit.
 for entry in subprocess.check_output(GIT+['ls-files','--stage','-z'],cwd=ROOT).split(b'\0'):
  if not entry:continue
  info,name=entry.split(b'\t',1);oid=info.split()[1]
  if oid.decode() not in names:
   oids.append(oid);names[oid.decode()]=name.decode('utf-8','replace')
 data=subprocess.check_output(GIT+['cat-file','--batch'],input=b'\n'.join(oids)+b'\n',cwd=ROOT)
 stream=io.BytesIO(data);findings=[];blobs=0;archives=0
 def inspect(name,body,oid):
  for kind,pattern in PATTERNS.items():
   if re.search(pattern,body):findings.append(dict(kind=kind,path=name,object=oid))
  if name.lower().endswith(('.sav','.srm','.ss0','.ss1','.state')) or name.startswith('PROGETTO AMICO/'):
   findings.append(dict(kind='game_or_private_file',path=name,object=oid))
  if name.lower().endswith('.gba') and not Path(name).name.startswith('gbmirroring-'):
   findings.append(dict(kind='unclassified_rom',path=name,object=oid))
 for _ in oids:
  header=stream.readline().split();oid,kind,size=header[0].decode(),header[1],int(header[2]);body=stream.read(size);assert stream.read(1)==b'\n'
  if kind!=b'blob':continue
  blobs+=1;name=names[oid];inspect(name,body,oid)
  if name.endswith('.zip'):
   archives+=1
   with zipfile.ZipFile(io.BytesIO(body)) as z:
    for item in z.infolist():
     if not item.is_dir():inspect(name+'!'+item.filename,z.read(item),oid)
 report=dict(scope='All reachable local refs, staged blobs and archive entries; heuristic scan, values redacted',reachable_commits=int(subprocess.check_output(GIT+['rev-list','--all','--count'])),blobs=blobs,archives=archives,findings=findings)
 out=ROOT/'build/publication';out.mkdir(parents=True,exist_ok=True)
 (out/'history-audit.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(blobs=blobs,archives=archives,reachable_commits=report['reachable_commits'],counts={k:sum(f['kind']==k for f in findings) for k in set(f['kind'] for f in findings)}),indent=2))
 blockers=[f for f in findings if f['kind']!='personal_path']
 if blockers:print(json.dumps(blockers,indent=2));return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
