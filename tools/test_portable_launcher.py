"""Exercise the real embedded interpreter entry point; never access USB."""
import subprocess,shutil,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 target=ROOT/'build'/'Launcher test with spaces'
 target.mkdir(parents=True,exist_ok=True)
 names=subprocess.check_output(['git','-c','safe.directory='+ROOT.as_posix(),'ls-files','-z'],cwd=ROOT).decode().split('\0')
 for name in filter(None,names):
  p=target/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,p)
 # Invalid choice exits after imports and offline checks, before opening a device.
 result=subprocess.run([str(target/'runtime/python/python.exe'),str(target/'tools/start_unified.py')],cwd=target.parent,input='x\n',text=True,capture_output=True,timeout=30)
 assert 'ModuleNotFoundError' not in result.stderr,result.stderr
 assert 'INVIO per multiboot' in result.stdout,result.stdout+result.stderr
 assert 'Scelta non riconosciuta' in result.stderr,result.stderr
 assert result.returncode!=0
 print(json.dumps(dict(passed=True,scope='Direct script launch with bundled isolated Python from relocated path containing spaces; invalid choice exits before USB'),indent=2))
if __name__=='__main__':main()
