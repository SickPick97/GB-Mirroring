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
    runtime = ROOT / 'runtime/native'
    runtime.mkdir(parents=True, exist_ok=True)
    dll = runtime / 'gbm_renderer.dll'
    zig = sorted((ROOT/'build/tools').glob('zig-*/zig.exe'))
    if zig:
        # Portable path without Visual Studio: zig's bundled clang, static, same sources and definitions as CMakeLists.
        src = extracted
        units = [str(source/'renderer.c')] + [str(src/'src/gba/renderers'/n) for n in
                 ('common.c', 'video-software.c', 'software-bg.c', 'software-mode0.c', 'software-obj.c')]
        out = ROOT/'build/native-renderer/gbm_renderer.dll'
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(zig[-1]), 'cc', '-target', 'x86_64-windows-gnu', '-shared', '-O2', '-std=c11',
                        '-I'+str(src/'include'), '-I'+str(src/'src'),
                        '-DBUILD_STATIC', '-DCOLOR_16_BIT', '-DCOLOR_5_6_5', '-DNDEBUG', '-DDISABLE_THREADING',
                        '-D_CRT_SECURE_NO_WARNINGS', '-o', str(out)] + units, check=True)
        architecture = 'Windows x64; zig cc (clang), static'
    else:
        subprocess.run(['cmake', '-S', str(source), '-B', str(ROOT/'build/native-renderer'),
                        '-G', 'Visual Studio 17 2022', '-A', 'x64',
                        '-DMGBA_SOURCE='+str(extracted)], check=True)
        subprocess.run(['cmake', '--build', str(ROOT/'build/native-renderer'),
                        '--config', 'Release'], check=True)
        out = ROOT/'build/native-renderer/Release/gbm_renderer.dll'
        architecture = 'Windows x64; static MSVC runtime'
    shutil.copyfile(out, dll)
    shutil.copyfile(extracted/'LICENSE', runtime/'LICENSE-mgba.txt')
    metadata.update(sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
                    architecture=architecture,
                    source='native/renderer/mgba-source.zip')
    (runtime/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print('Native renderer ready:', dll)

if __name__ == '__main__':
    main()
