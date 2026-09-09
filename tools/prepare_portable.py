"""One-time local extraction from the user's material; never includes game data."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'PROGETTO AMICO'
    target=ROOT/'runtime/python'
    copied={}
    for path in (source/'python').rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':
            continue
        relative=path.relative_to(source/'python')
        destination=target/relative
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(path,destination)
        copied[str(relative).replace('\\','/')]=hashlib.sha256(path.read_bytes()).hexdigest()
    vendor=ROOT/'vendor/celio_transport'
    vendor.mkdir(parents=True,exist_ok=True)
    for name in ('mb_multi.py','usb_link.py'):
        shutil.copy2(source/name,vendor/name)
    (vendor/'logo.bin').write_bytes((source/'mbstub.gba').read_bytes()[4:0xa0])
    (ROOT/'runtime/manifest.json').write_text(json.dumps(copied,indent=2)+'\n')
    print('Runtime:',len(copied),'files; no ROMs, saves or emulator files copied.')

if __name__=='__main__':main()
