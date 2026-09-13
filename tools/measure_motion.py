"""Local emulation only. Read-only ROM/save; real input and capture counters.

Does not access USB. VBlank counts are not a gameplay/audio certification.
"""
import argparse,json,struct
from pathlib import Path
from mgba_headless import Core
from verify_firmware import elf_symbols
from link_protocol import bmp
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',default='emerald-cache');ap.add_argument('--state',type=Path,default=ROOT/'build/motion/field.state')
    ap.add_argument('--frames',type=int,default=1200);ap.add_argument('--leg',type=int,default=48);ap.add_argument('--vertical',action='store_true');ap.add_argument('--menus',action='store_true');ap.add_argument('--team',action='store_true');ap.add_argument('--stay',action='store_true');args=ap.parse_args()
    folder=ROOT/'build'/args.candidate;scenario=('team' if args.team else 'pokedex' if args.menus else 'vertical' if args.vertical else 'walking')+('-stay' if args.stay else '');out=args.state.parent/args.candidate/scenario;out.mkdir(parents=True,exist_ok=True)
    sym=elf_symbols((folder/'resident.elf').read_bytes())
    state=bytearray(args.state.read_bytes())
    blob=bytearray((folder/'resident.bin').read_bytes())
    struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0])
    state[0x5df80:0x60c00]=bytes(0x2c80);state[0x5df80:0x5df80+len(blob)]=blob
    struct.pack_into('<I',state,0x20ffc,0x203cf80)
    struct.pack_into('<I',state,0x21000+sym['enabled'][0]-0x2000000,1)
    rom=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom.read_bytes())
    def read(s,name):return struct.unpack_from('<I',s,0x21000+sym[name][0]-0x2000000)[0]
    records=[]
    try:
        core.run();core.restore(state);core.run(480);initial=read(core.state(),'sequence')
        for frame in range(args.frames):
            keys=1<<((5 if frame%(args.leg*2)<args.leg else 4) if args.vertical else (7 if frame%(args.leg*2)<args.leg else 6))
            if args.menus or args.team:
                keys=(1<<3 if 120<=frame<123 else 1<<8 if 240<=frame<243 else 1 if 480<=frame<483 or 660<=frame<663 else 0)
            if args.stay and frame>=480:keys=0
            if args.team and 180<=frame<183:keys=1<<5
            core.run(1,keys);s=core.state()
            row={k:read(s,k) for k in ('sequence','capture_ticks','capture_words','changed','cursor','entry_line','peak_lines','visits')}

            if 'cost' in sym:row['cost']=list(struct.unpack_from('<4I',s,0x21000+sym['cost'][0]-0x2000000))
            row['frame']=frame;row['vblank_callback']=struct.unpack_from('<I',s,0x1b2cc)[0]
            records.append(row)
            if frame in (0,119,239,359,479,599,779,args.frames-1):bmp(out/('%s.bmp'%frame),core.rgb555())
    finally:core.close()
    captures=records[-1]['sequence']-initial
    result=dict(scope='Emulated directional input, no physical Link or browser measurement',frames=args.frames,leg_frames=args.leg,scenario=scenario,captures=captures,capture_fps=captures*16777216/280896/args.frames,records=records)
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='records'}))

if __name__=='__main__':main()
