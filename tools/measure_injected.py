"""Development: inject the built resident into the emulated game (mGBA) and measure what it does to the game.

Unlike cosim_stream.py (Unicorn + cycle model), the resident runs here on mGBA's timing with the game's real
interrupts, so interrupt interplay, idle-time use and the game's own pace are observed directly. The link output
itself is not captured. Counts the game's main-loop iterations through a callback1 hook appended past the ROM.
"""
import argparse,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from mgba_headless import Core
from verify_firmware import elf_symbols
ROM=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
COUNTER=0x0203fff0
def keys_for(name,f):
    if name=='h':return 1<<(7 if f%240<120 else 6)
    if name=='run':return (1<<(7 if f%240<120 else 6))|1
    if name=='v':return 1<<(5 if f%240<120 else 4)
    return 0
def run(resident,state_path,frames,scenario,enabled=True,key_file=None):
    rom=ROM.read_bytes()
    state=bytearray(Path(state_path).read_bytes())
    cb1=struct.unpack_from('<I',state,0x19000+0x22c0)[0]
    # callback1 hook: count one main-loop iteration, then tail-call the game's callback1
    rom+=bytes((-len(rom))%16)
    hook=len(rom)|0x08000000
    rom+=struct.pack('<10I',0xe92d400f,0xe59f0014,0xe5901000,0xe2811001,0xe5801000,0xe8bd400f,0xe59fc004,0xe12fff1c,COUNTER,cb1)
    struct.pack_into('<I',state,0x19000+0x22c0,hook)
    sy=None
    if resident:
        folder=ROOT/resident;sy=elf_symbols((folder/'resident.elf').read_bytes());blob=bytearray((folder/'resident.bin').read_bytes())
        struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0]);state[0x5df80:0x5df80+len(blob)]=blob
        struct.pack_into('<I',state,0x20ffc,0x203cf80);struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1 if enabled else 0)
    keys=[int(x) for x in Path(key_file).read_text().split(',')] if key_file else None
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom)
    rd=lambda s,a:struct.unpack_from('<I',s,0x21000+a-0x2000000)[0]
    try:
        core.run();core.restore(state);s=core.state()
        m0=rd(s,COUNTER);v0=struct.unpack_from('<I',s,0x19000+0x22e0)[0]
        start={n:rd(s,sy[n][0]) for n in ('visits','sequence')} if sy else {}
        idle=[];callbacks=set()
        for f in range(frames):
            k=keys[f//16] if keys and f<len(keys)*16 else keys_for(scenario,f)
            core.run(1,k);s=core.state()
            callbacks.add(struct.unpack_from('<I',s,0x19000+0x22cc)[0])
            if sy and 'idle_words' in sy:idle.append(rd(s,sy['idle_words'][0]))
        m1=rd(s,COUNTER);v1=struct.unpack_from('<I',s,0x19000+0x22e0)[0]
        out=dict(frames=frames,main_iterations=m1-m0,vblanks=v1-v0)
        if sy:
            out.update(ticks=rd(s,sy['visits'][0])-start['visits'],packets=rd(s,sy['sequence'][0])-start['sequence'])
            if idle:out.update(idle_words_mean=round(sum(idle)/len(idle),1),idle_words_max=max(idle))
        out['callbacks']=sorted(hex(c) for c in callbacks)
        return out
    finally:core.close()
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--resident',default='build/emerald-stream');ap.add_argument('--state',default=str(ROOT/'build/motion/field.state'))
    ap.add_argument('--frames',type=int,default=600);ap.add_argument('--scenario',default='h');ap.add_argument('--keys')
    ap.add_argument('--baseline',action='store_true',help='also run the game without the resident')
    a=ap.parse_args()
    r=dict(resident=run(a.resident,a.state,a.frames,a.scenario,key_file=a.keys))
    if a.baseline:r['game_alone']=run(None,a.state,a.frames,a.scenario,key_file=a.keys)
    print(json.dumps(r))
