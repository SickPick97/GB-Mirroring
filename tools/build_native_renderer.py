"""Build the pinned, offline native display engine. Never accesses hardware."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT / 'native/renderer'
    metadata = json.loads((source / 'upstream.json').read_text())
    archive = source / 'mgba-source.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != metadata['source_sha256']:
        raise ValueError('mGBA source archive checksum mismatch')
    extracted = ROOT / 'build/native-source'
    extracted.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for entry in bundle.infolist():
            target = (extracted / entry.filename).resolve()
            target.relative_to(extracted.resolve())
        bundle.extractall(extracted)
    subprocess.run(['cmake', '-S', str(source), '-B', str(ROOT/'build/native-renderer'),
                    '-G', 'Visual Studio 17 2022', '-A', 'x64',
                    '-DMGBA_SOURCE='+str(extracted)], check=True)
    subprocess.run(['cmake', '--build', str(ROOT/'build/native-renderer'),
                    '--config', 'Release'], check=True)
    runtime = ROOT / 'runtime/native'
    runtime.mkdir(parents=True, exist_ok=True)
    dll = runtime / 'gbm_renderer.dll'
    shutil.copyfile(ROOT/'build/native-renderer/Release/gbm_renderer.dll', dll)
    shutil.copyfile(extracted/'LICENSE', runtime/'LICENSE-mgba.txt')
    metadata.update(sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                    architecture='Windows x64; static MSVC runtime',
                    source='native/renderer/mgba-source.zip')
    (runtime/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Native renderer ready:', dll)

if __name__ == '__main__':
    main()
