"""Local emulator comparison of baseline and isolated interworking candidate."""
import argparse,json,struct
from pathlib import Path
from mgba_headless import Core
from verify_firmware import elf_symbols
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rom',required=True);ap.add_argument('--state',required=True)
    args=ap.parse_args();rom=Path(args.rom).read_bytes();field=Path(args.state).read_bytes()
    if len(field)<0x61000 or field[0x1c:0x20]!=b'BPEI':raise ValueError('BPEI state required')
    report=[]
    for directory in ('build/emerald','build/emerald-next'):
        folder=ROOT/directory;symbols=elf_symbols((folder/'resident.elf').read_bytes())
        payload=bytearray((folder/'resident.bin').read_bytes());state=bytearray(field)
        struct.pack_into('<I',payload,4,struct.unpack_from('<I',state,0x20ffc)[0])
        state[0x5df80:0x60c00]=bytes(0x2c80);state[0x5df80:0x5df80+len(payload)]=payload
        struct.pack_into('<I',state,0x20ffc,0x203cf80)
        core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom)
        try:
            core.run();core.restore(state);core.run(3,(1<<2)|(1<<10)|(1<<11));core.run(480)
            def counts():
                s=core.state()
                return [struct.unpack_from('<I',s,0x21000+symbols['sequence'][0]-0x2000000)[0],
                        struct.unpack_from('<I',s,0x1b2e0)[0]]
            a=counts();core.run(600);b=counts();core.run(600,1<<7);c=counts()
            static=[b[i]-a[i] for i in range(2)];moving=[c[i]-b[i] for i in range(2)]
            if static[0]<=0 or moving[0]<=0 or static[1]!=600 or moving[1]!=600:
                raise AssertionError((directory,static,moving))
            report.append(dict(variant=directory,static=static,moving=moving,
                resident_bytes=len(payload),ram_free=0x203f800-symbols['__end__'][0]))
        finally:core.close()
    result=dict(scope='Local mGBA; counts are captures and VBlanks, not physical FPS or audio certification',variants=report)
    (ROOT/'build/emerald-next/budget-probe.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
