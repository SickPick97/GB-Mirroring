"""Emulator-only per-VBlank cost of the 0.12 resident, with the game's real VBlank timing.

The resident runs inside mGBA next to the game (bits leave through emulated GPIO and are not
captured). Reports ticks emitted, scanlines used by each tick and words sent. Not hardware, not audio.
"""
import argparse,json,statistics,struct
from pathlib import Path
from mgba_headless import Core
from verify_firmware import elf_symbols
ROOT=Path(__file__).resolve().parents[1]
KEYS={'h':lambda f:1<<(7 if f%96<48 else 6),'v':lambda f:1<<(5 if f%96<48 else 4),'run':lambda f:(1<<(7 if f%160<80 else 6))|1,'stay':lambda f:0,
      'menus':lambda f:(1<<3 if 120<=f<123 else 1<<8 if 240<=f<243 else 1 if 480<=f<483 or 660<=f<663 else 0)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',default='emerald-stream');ap.add_argument('--state',type=Path,default=ROOT/'build/motion/field.state')
    ap.add_argument('--scenario',choices=sorted(KEYS),default='h');ap.add_argument('--frames',type=int,default=1200);ap.add_argument('--warmup',type=int,default=480)
    args=ap.parse_args()
    folder=ROOT/'build'/args.candidate;sy=elf_symbols((folder/'resident.elf').read_bytes())
    state=bytearray(args.state.read_bytes());blob=bytearray((folder/'resident.bin').read_bytes())
    struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0])
    state[0x5df80:0x60c00]=bytes(0x2c80);state[0x5df80:0x5df80+len(blob)]=blob
    struct.pack_into('<I',state,0x20ffc,0x203cf80);struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1)
    rom=(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom)
    def read(s,name):return struct.unpack_from('<I',s,0x21000+sy[name][0]-0x2000000)[0]
    rows=[]
    try:
        core.run();core.restore(state);core.run(args.warmup);last=read(core.state(),'sequence')
        for f in range(args.frames):
            core.run(1,KEYS[args.scenario](f));s=core.state();seq=read(s,'sequence')
            rows.append(dict(emitted=seq!=last,lines=read(s,'peak_lines'),words=read(s,'last_words'),entry=read(s,'entry_line')));last=seq
    finally:core.close()
    emitted=[r for r in rows if r['emitted']]
    lines=[r['lines'] for r in emitted] or [0];words=[r['words'] for r in emitted] or [0]
    def pct(v,p):s=sorted(v);return s[min(len(s)-1,int(len(s)*p))]
    result=dict(candidate=args.candidate,scenario=args.scenario,frames=args.frames,ticks_emitted=len(emitted),emitted_per_60=round(len(emitted)*60/args.frames,2),
        lines_mean=round(statistics.mean(lines),1),lines_p95=pct(lines,.95),lines_max=max(lines),words_mean=round(statistics.mean(words),1),words_max=max(words),
        entry_line_mean=round(statistics.mean(r['entry'] for r in rows),1),
        scope='Emulated game with resident in mGBA; bits not captured; not hardware or audio')
    print(json.dumps(result))
if __name__=='__main__':main()
