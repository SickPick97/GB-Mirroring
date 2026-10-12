"""Build the small native index of cartridge graphics (runtime/native/gbm_blocks.dll). Never accesses hardware."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    zig=sorted((ROOT/'build/tools').glob('zig-*/zig.exe'))
    if os.environ.get('GBM_ZIG'):zig=[Path(os.environ['GBM_ZIG'])]
    if not zig:raise SystemExit('zig not found: build/tools/zig-*/zig.exe or GBM_ZIG')
    out=ROOT/'build/native-blocks/gbm_blocks.dll';out.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(zig[-1]),'cc','-target','x86_64-windows-gnu','-shared','-O2','-std=c11','-DNDEBUG','-o',str(out),str(ROOT/'native/blocks/blocks.c')],check=True)
    runtime=ROOT/'runtime/native';dll=runtime/'gbm_blocks.dll';shutil.copyfile(out,dll)
    (runtime/'manifest-blocks.json').write_text(json.dumps(dict(source='native/blocks/blocks.c',sha256=hashlib.sha256(dll.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256((ROOT/'native/blocks/blocks.c').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
        architecture='Windows x64; zig cc (clang), static',scope='Hashes and offsets of the user\'s own cartridge image, in memory; no game content.'),indent=2)+'\n')
    print('Native block index ready:',dll)
if __name__=='__main__':main()
