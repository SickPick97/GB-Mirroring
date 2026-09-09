"""Prepare pinned build dependencies inside this workspace (Python stdlib only)."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
DEPS = [
    dict(name='pico-sdk 2.2.0', archive='pico-sdk-2.2.0.zip', destination='third_party',
         url='https://codeload.github.com/raspberrypi/pico-sdk/zip/refs/tags/2.2.0',
         sha256='848afc05f3af55e475a083f2d0533ac3c845341eb4ea6a35acf77a0897be3f3c'),
    dict(name='TinyUSB 86ad6e56c1700e85f1c5678607a762cfe3aa2f47', archive='tinyusb-86ad6e56.zip', destination='third_party',
         url='https://codeload.github.com/hathach/tinyusb/zip/86ad6e56c1700e85f1c5678607a762cfe3aa2f47',
         sha256='3011c90c128988012b553e5d2f0a90bc0b64046591c964bc1f9f6659edcd7e4b'),
    dict(name='Ninja 1.12.1 Windows x64', archive='ninja-win-1.12.1.zip', destination='tools/ninja',
         url='https://github.com/ninja-build/ninja/releases/download/v1.12.1/ninja-win.zip',
         sha256='f550fec705b6d6ff58f2db3c374c2277a37691678d6aba463adcbb129108467a')
]

def main():
    (ROOT/'downloads').mkdir(exist_ok=True)
    for dep in DEPS:
        archive = ROOT/'downloads'/dep['archive']
        if not archive.exists():
            print('Download:',dep['name'],flush=True)
            request = urllib.request.Request(dep['url'],headers={'User-Agent':'GBMirroring-build/0.1'})
            with urllib.request.urlopen(request,timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != dep['sha256']:
                raise ValueError('Download hash mismatch: '+dep['name'])
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != dep['sha256']:
            raise ValueError('Archive hash mismatch: '+str(archive))
        destination = (ROOT/dep['destination']).resolve()
        destination.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                target = (destination/member.filename).resolve()
                if destination not in target.parents and target != destination:
                    raise ValueError('Archive path outside destination')
                # Managed dependency files only; no deletion, and skip unchanged files.
                if member.is_dir():
                    target.mkdir(parents=True,exist_ok=True)
                else:
                    contents = z.read(member)
                    if not target.exists() or target.read_bytes() != contents:
                        target.parent.mkdir(parents=True,exist_ok=True)
                        target.write_bytes(contents)
        print('Verified:',dep['name'])
    (ROOT/'downloads/dependency-lock.json').write_text(json.dumps(DEPS,indent=2)+'\n',encoding='utf-8')

if __name__ == '__main__': main()

