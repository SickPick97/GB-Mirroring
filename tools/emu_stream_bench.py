"""Scene loads with the resident really running inside the emulated game (mGBA).

Unlike cosim_stream.py, which runs the resident beside the game on a timing model, here the game and the resident share
the emulated console: the game's interrupts, its busy frames, the wireless-adapter probe after a door and the time the
resident takes are all those of the emulator. The 0.13.0 resident takes 99 frames here for the Pokemon Center door,
against 98-111 measured on the console (log of 2026-10-11).

Nothing is connected to the emulated Link port, so the packets themselves are not seen: what is read, from the
resident's memory after every frame, is how many packets it sent and how many known-changed blocks are outstanding
(the palette blocks of a fade the PC computes are not: it shows them at once).
The PC's answer (the verdict) cannot come through the port either: the bench build of the resident
(GBM_BUILD_SUFFIX=-banco GBM_DEFINES=BENCH) runs its control slot with the timing of the console and then takes the
28 words from memory this tool fills after every frame, as the PC would: a block announced by hash counts as held
when its content was in VRAM at an earlier moment with nothing outstanding, or is in the PC's cartridge image
(--rom-index). Everything else in the resident is the release code.
Software only: cable, Pico and USB are absent.
"""
import argparse,json,os,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
ROM=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
def run(args):
    from mgba_headless import Core
    from verify_firmware import elf_symbols
    from graphics_stream import graphics_from_state
    from stream_parser import block_fold,stream_hash
    import cosim_stream
    keys=cosim_stream.KEYS[args.scenario];folder=ROOT/args.resident
    sy=elf_symbols((folder/'resident.elf').read_bytes());blob=bytearray((folder/'resident.bin').read_bytes())
    rom=ROM.read_bytes();known=set();raw=None
    if args.rom_index:
        import rom_blocks;known|=set(a^(b*0x9e3779b1&0xffffffff) for a,b in rom_blocks.build(rom));raw=rom_blocks.build_raw(rom)
    if args.known and Path(args.known).is_file():known|=set(json.loads(Path(args.known).read_text()))
    off=lambda n:(0x21000+sy[n][0]-0x02000000) if sy[n][0]<0x03000000 else (0x19000+sy[n][0]-0x03000000)
    rd=lambda st,n,fmt='<I':struct.unpack_from(fmt,st,off(n))
    # the bench build takes the verdict from memory (see poll_control)
    bench=b'\x40\xcf\x03\x02' in blob and 'announced' in sy
    announces='announced' in sy
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom);rows=[];last=0;hits=misses=0;missed=[];judged={};palette={};fade_hits=fade_misses=0
    import rom_blocks as _rb;solve=_rb.fade_solver()
    try:
        core.run();core.restore(bytearray(Path(args.state).read_bytes()));core.run(60);st=bytearray(core.state())
        struct.pack_into('<I',blob,4,struct.unpack_from('<I',st,0x20ffc)[0]);st[0x5df80:0x5df80+len(blob)]=blob
        struct.pack_into('<I',st,0x20ffc,0x0203cf80);struct.pack_into('<I',st,off('enabled'),1)
        core.restore(st)
        for f in range(args.frames):
            core.run(1,keys(f));st=bytearray(core.state())
            sequence=rd(st,'sequence')[0];dirty=rd(st,'dirty_mask','<13I');strong=rd(st,'strong_mask','<13I')
            pending=sum(bin(a&b).count('1') for a,b in zip(dirty,strong))
            callback=struct.unpack_from('<I',st,0x19000+0x22cc)[0]
            row=dict(f=f,packets=sequence-last,pending=pending,callback=callback);rows.append(row);last=sequence
            if args.rows:
                bits=lambda m:[k for k in range(393) if m[k>>5]>>(k&31)&1]
                row['detail']='ann %d recent %d words %d %s'%(len(bits(rd(st,'announced','<13I'))) if announces else 0,len(bits(rd(st,'recent','<13I'))) if announces else 0,rd(st,'idle_words')[0],
                    bits([a&b for a,b in zip(dirty,strong)]) if pending<=12 else '')
            if pending==0 and f%8==0:
                # the PC has the whole picture: every block content in it is known from now on
                gfx=graphics_from_state(st)
                for b in range(9,393):known.add(block_fold(gfx[b*256:(b+1)*256]))
            if bench and args.verdict:
                # what the PC would answer now: one bit for every announced block whose content it holds
                masks=[0]*13;announced=rd(st,'announced','<13I');gfx=None
                for k in range(9,393):
                    if announced[k>>5]>>(k&31)&1 and k not in judged:
                        h=struct.unpack_from('<I',st,off('hashes')+4*k)[0]^1;held=h in known
                        if not held and raw is not None:
                            # copied unchanged from the cartridge: the PC finds it in its own image
                            gfx=gfx or graphics_from_state(st);key=stream_hash(bytes(gfx[k*256:(k+1)*256]))
                            held=key[0]^(key[1]*0x9e3779b1&0xffffffff)==h and raw.find(key) is not None
                        judged[k]=held;hits+=held;misses+=not held
                        if not held and args.misses:missed.append((f,k))
                if 'unf' in sy and announced[0]&0x1e:
                    # palette blocks announced during a fade: held when the PC has the unfaded palette the resident
                    # believes it has and its blend gives the announced block
                    gfx=gfx or graphics_from_state(st);unf=rd(st,'unf','<4I');color=struct.unpack_from('<H',st,0x21000+0x37fda)[0]&0x7fff;hint=struct.unpack_from('<H',st,0x21000+0x37fd8)[0]>>6&31
                    for k in range(1,5):
                        if announced[0]>>k&1:
                            # judged once for each announcement, when it is made (as the PC does on reading it)
                            h=struct.unpack_from('<I',st,off('hashes')+4*k)[0]
                            if palette.get(k,(None,))[0]!=h:
                                base=bytes(st[0x21000+0x37714+(k-1)*256:0x21000+0x37714+k*256]);now=bytes(gfx[k*256:(k+1)*256])
                                held=block_fold(now)==h^1 and block_fold(base)==unf[k-1] and solve is not None and solve(base,color,stream_hash(now),hint) is not None
                                palette[k]=(h,held);fade_hits+=held;fade_misses+=not held
                                if not held and args.misses:missed.append((f,'%d palette: %s, fade %04x %04x %04x'%(k,'changed since announced' if block_fold(now)!=h^1 else 'unfaded not the one sent' if block_fold(base)!=unf[k-1] else 'no blend gives it',*struct.unpack_from('<3H',st,0x21000+0x37fd8))))
                            if palette[k][1]:masks[0]|=1<<k
                for k in list(judged):
                    if not announced[k>>5]>>(k&31)&1:del judged[k]
                    elif judged[k]:masks[k>>5]|=1<<(k&31)
                # as the PC counts: a palette block of a fade it computed is shown at once; a tile block it holds still
                # waits for the resident to confirm it after the verdict
                row['pending']=pending-bin(dirty[0]&strong[0]&masks[0]&0x1e).count('1')
                words=[sequence&0xffff]
                for m in masks:words+=[m&0xffff,m>>16]
                check=0x5aa5
                for w in words:check^=w
                struct.pack_into('<28H',st,0x21000+0x3cf40,*words,check)
                core.restore(st)
    finally:core.close()
    loads=[];i=0
    while i<len(rows):
        if rows[i]['pending']>300 and (i==0 or rows[i-1]['pending']<100):
            j=next((k for k in range(i,len(rows)) if rows[k]['pending']==0),len(rows)-1)
            loads.append(dict(start_frame=rows[i]['f'],frames=rows[j]['f']-rows[i]['f'],packets=sum(r['packets'] for r in rows[i:j+1]),finished=rows[j]['pending']==0));i=j
        i+=1
    # longest run of frames with blocks outstanding outside the scene loads (a battle move, a menu)
    longest=run_=0
    for r in rows:
        run_=run_+1 if r['pending'] else 0;longest=max(longest,run_)
    scenes=[];previous=None
    for r in rows:
        if r['callback']!=previous and r['callback']>>24==8 or r['callback']==0 and previous!=0:scenes.append((r['f'],r['callback']))
        previous=r['callback']
    result=dict(resident=str(args.resident),scenario=args.scenario,frames=len(rows),loads=loads,longest_outstanding=longest,
        frames_outstanding=sum(1 for r in rows if r['pending']),packets=sum(r['packets'] for r in rows),store_hits=hits,store_misses=misses,fade_hits=fade_hits,fade_misses=fade_misses,scenes=scenes[:40],
        scope='mGBA game with the resident running inside it; verdict written between frames; no cable, Pico or PC')
    if args.known:Path(args.known).write_text(json.dumps(sorted(known)))
    for m in missed:print('miss frame %d block %s'%m)
    if args.rows:
        for r in rows:print(r['f'],r['packets'],r['pending'],'%08x'%r['callback'],r['detail'])
    print(json.dumps(result))
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--resident',default='build/emerald-stream-banco');ap.add_argument('--state',type=Path,default=ROOT/'build/motion/field.state')
    ap.add_argument('--scenario',default='center');ap.add_argument('--frames',type=int,default=900)
    ap.add_argument('--rom-index',action='store_true',help='the PC knows the graphics of the cartridge image, as the viewer does')
    ap.add_argument('--known',help='file of block hashes the PC already holds: read before, written after (a later session)')
    ap.add_argument('--no-verdict',dest='verdict',action='store_false',help='the PC never answers (Pico 0.7)')
    ap.add_argument('--misses',action='store_true',help='list the announced blocks the PC did not hold and whether the cartridge has them uncompressed')
    ap.add_argument('--rows',action='store_true',help='print every frame')
    run(ap.parse_args())
