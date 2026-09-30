"""Development co-simulation: mGBA game frames -> real ARM resident tick() in Unicorn -> PC parser.

mGBA advances the unmodified game. Each game frame its graphics memory is copied into a
Unicorn machine that runs the real resident code once per VBlank with an approximate ARM7TDMI
cycle model (VCOUNT is derived from consumed cycles, so the resident's own scanline deadlines
apply). The bits written to the Link GPIO are decoded by the same parser used on the PC.
This estimates CPU time and stream completeness; it is not a physical or audio measurement.
"""
import argparse,json,random,statistics,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_CPSR,UC_ARM_REG_PC
from verify_firmware import elf_symbols
from mgba_headless import Core
from graphics_stream import graphics_from_state
LINE=1232
KEYS={'h':lambda f:1<<(7 if f%96<48 else 6),'v':lambda f:1<<(5 if f%96<48 else 4),
      'run':lambda f:(1<<(7 if f%160<80 else 6))|1,'stay':lambda f:0,
      # Start menu (Pokedex/Pokemon), select, back: same key pattern as measure_motion --menus / --team.
      # Enter the Pokemon Center standing below its door (field.state), walk to the counter, come back out.
      'center':lambda f:1<<4 if 60<=f<230 else 1<<5 if 500<=f<640 else 0,
      # Wild battle: start from build/motion/battle.state (transition already running), press A now and then.
      'battle':lambda f:1<<8 if f>=300 and f%40<3 else 0,
      'menus':lambda f:(1<<3 if 120<=f<123 else 1<<8 if 240<=f<243 else 1 if 480<=f<483 or 660<=f<663 else 0),
      'team':lambda f:(1<<3 if 120<=f<123 else 1<<5 if 180<=f<183 else 1<<8 if 240<=f<243 else 1 if 480<=f<483 or 660<=f<663 else 0)}

def toolchain_nm():
    import os
    base=Path(os.environ.get('GBM_ARM_TOOLCHAIN','C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi'))
    return sorted(base.glob('*/bin/arm-none-eabi-nm.exe'))[-1]

class Machine:
    """One resident image in an ARM machine with a coarse cycle counter."""
    def __init__(self,folder,rom_state_callback=0x080863a5):
        self.sy=sy=elf_symbols((folder/'resident.elf').read_bytes());blob=(folder/'resident.bin').read_bytes()
        nm=subprocess.check_output([str(toolchain_nm()),'-n','-S',str(folder/'resident.elf')],text=True)
        self.funcs=sorted((int(p[0],16),0,p[-1]) for p in (l.split() for l in nm.splitlines()) if len(p)>=3 and p[-2] in 'tTr' and not p[-1].startswith('$'))
        self.addrs=[a for a,_,_ in self.funcs]
        u=self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        for a,s in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000),(0x08000000,0x1000000)):u.mem_map(a,s)
        self.rom_loaded=False
        u.mem_write(0x0203cf80,blob);off=sy['__hot_load__'][0]-0x0203cf80
        u.mem_write(sy['__hot_start__'][0],blob[off:off+sy['__hot_end__'][0]-sy['__hot_start__'][0]])
        self.word(sy['enabled'][0],1);u.mem_write(0x04000130,struct.pack('<H',1023))
        self.word(0x030022cc,rom_state_callback);u.mem_write(0x04000134,struct.pack('<H',0x8030))
        self.cycles=0;self.entry=200;self.bus=dict(clock=0,bits=0,word=0,words=[]);self.by_function={}
        u.hook_add(UC_HOOK_MEM_WRITE,self._link,begin=0x04000134,end=0x04000135)
        u.hook_add(UC_HOOK_MEM_READ,self._vcount,begin=0x04000006,end=0x04000007)
        u.hook_add(UC_HOOK_CODE,self._code)
        u.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,self._data,begin=0x02000000,end=0x02ffffff)
        u.hook_add(UC_HOOK_MEM_READ,self._rom,begin=0x08000000,end=0x08ffffff)
        self.profile=False;self.pc_cycles={}
    def load_rom(self,rom):
        self.u.mem_write(0x08000000,bytes(rom));self.rom_loaded=True
    def word(self,a,v):self.u.mem_write(a,struct.pack('<I',v))
    def read32(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
    def symbol(self,name):return self.sy[name][0]
    def _link(self,uc,access,address,size,value,user):
        b=self.bus
        if value&32 and value&1 and not b['clock']:
            b['word']=((b['word']<<1)|((value>>1)&1))&65535;b['bits']+=1
            if b['bits']==16:b['words'].append(b['word']);b['bits']=0
        b['clock']=value&1
    def _vcount(self,uc,access,address,size,value,user):
        uc.mem_write(0x04000006,struct.pack('<H',(self.entry+self.cycles//LINE)%228))
    def _code(self,uc,address,size,user):
        thumb=(uc.reg_read(UC_ARM_REG_CPSR)>>5)&1
        fetch=1 if address>=0x03000000 else (3 if thumb else 6)
        extra=0
        try:
            if thumb:
                op=struct.unpack('<H',uc.mem_read(address,2))[0]
                if (op&0xf600)==0xb400:extra=bin(op&0xff).count('1')+((op>>8)&1)
                elif (op&0xf000)==0xc000:extra=bin(op&0xff).count('1')
                elif (op&0xffc0)==0x4340:extra=3
            else:
                op=struct.unpack('<I',uc.mem_read(address,4))[0]
                if (op&0x0e000000)==0x08000000:extra=bin(op&0xffff).count('1')
                elif (op&0x0fc000f0)==0x00000090:extra=3
        except Exception:pass
        c=fetch+extra;self.cycles+=c
        if self.profile:
            import bisect
            i=bisect.bisect_right(self.addrs,address)-1
            n=self.funcs[i][2] if i>=0 else 'unknown'
            self.by_function[n]=self.by_function.get(n,0)+c
            if n=='tick':self.pc_cycles[address&~15]=self.pc_cycles.get(address&~15,0)+c
    def _data(self,uc,access,address,size,value,user):
        c=2 if size<=2 else 5;self.cycles+=c
        if self.profile:
            import bisect
            pc=uc.reg_read(UC_ARM_REG_PC);i=bisect.bisect_right(self.addrs,pc)-1
            n='data:'+(self.funcs[i][2] if i>=0 else 'unknown');self.by_function[n]=self.by_function.get(n,0)+c
            if n=='data:tick':self.pc_cycles[pc&~15]=self.pc_cycles.get(pc&~15,0)+c
    def _rom(self,uc,access,address,size,value,user):
        c=5 if size>2 else 3;self.cycles+=c
        if self.profile:self.by_function['(rom read)']=self.by_function.get('(rom read)',0)+c
    def load_environment(self,state):
        """Game queues/callback of the snapshot taken at VBlank start: what observe() sees."""
        u=self.u
        u.mem_write(0x03000000,bytes(state[0x19000:0x19000+0x1000]))
        u.mem_write(0x02021800,bytes(state[0x21000+0x21800:0x21000+0x21a00]))
        u.mem_write(0x02037600,bytes(state[0x21000+0x37600:0x21000+0x37800]))
        u.mem_write(0x030022cc,bytes(state[0x19000+0x22cc:0x19000+0x22d0]))
        u.mem_write(0x04000200,struct.pack('<HH',1,1))
    def observe(self):
        self.u.reg_write(UC_ARM_REG_SP,0x0203fc00);self.u.reg_write(UC_ARM_REG_LR,0x03007000)
        self.u.emu_start(self.symbol('observe'),0x03007000,count=2000000)
    def load_graphics(self,gfx):
        u=self.u
        u.mem_write(0x03000818,gfx[:96]);u.mem_write(0x05000000,gfx[256:1280]);u.mem_write(0x07000000,gfx[1280:2304]);u.mem_write(0x06000000,gfx[2304:])
    def tick(self,now,entry_line):
        self.word(0x030022e0,now);self.entry=entry_line;self.cycles=0
        self.u.reg_write(UC_ARM_REG_SP,0x0203fc00);self.u.reg_write(UC_ARM_REG_LR,0x03007000)
        self.u.mem_write(0x04000006,struct.pack('<H',entry_line))
        self.u.emu_start(self.symbol('tick'),0x03007000,count=20000000)
        words=self.bus['words'];self.bus['words']=[]
        return struct.pack('<'+'H'*len(words),*words),len(words)

class Echo:
    def render(self,data):return bytes(data)

def run(args):
    folder=ROOT/args.resident;m=Machine(folder);m.profile=args.profile
    from graphics_stream import GraphicsParser
    from stream_parser import StreamParser
    stream=args.parser=='stream' or (args.parser=='auto' and 'stream' in str(args.resident))
    rom_bytes=(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
    m.load_rom(rom_bytes)
    parser=(StreamParser(Echo(),rom=rom_bytes) if stream else GraphicsParser(Echo()));rng=random.Random(args.seed)
    renderer=None
    if args.render:
        from native_renderer import Renderer
        renderer=Renderer();visual=[]
    truth={};fidelity=[]
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes())
    slow=[];ticks=[];frames=[];last_gfx=None;mismatch=0;checked=0;fn_total={}
    try:
        core.run();core.restore(bytearray(Path(args.state).read_bytes()));core.run(60)
        pending_state=core.state()
        for f in range(args.frames):
            core.run(1,KEYS[args.scenario](f));state=core.state();gfx=graphics_from_state(state)
            # requests queued in the previous snapshot are executed by this VBlank; the resident sees their result
            m.load_environment(pending_state);m.observe();pending_state=state
            m.load_graphics(gfx);truth[f+1]=gfx;truth.pop(f-200,None)
            entry=args.entry if args.entry else rng.choice((198,200,202,204,206,208,210))
            wire,words=m.tick(f+1,entry)
            lines=m.cycles/LINE
            if args.trace and args.trace[0]<=f<args.trace[1]:
                pend=struct.unpack_from('<H',wire,30)[0] if len(wire)>=32 else -1
                print('  f%4d entry %3d lines %5.1f words %3d pending %3d cb %08x'%(f,entry,lines,words,pend,m.read32(0x030022cc)))
            out=parser.feed(wire)
            for seq,img,wire_bytes,codec,meta in out:
                frames.append((f,seq,meta));ref=truth.get(meta.get('end_game_frame',meta.get('game_frame')))
                if ref is not None:
                    bad=[b for b in range(393) if img[b*256:(b+1)*256]!=ref[b*256:(b+1)*256]]
                    fidelity.append((len(bad),sum(1 for b in bad if b<9),f-(meta.get('end_game_frame',f+1)-1)))
                    if renderer is not None and f>=args.warmup:
                        a=renderer.render(img);b=renderer.render(ref)
                        visual.append(sum(1 for i in range(0,76800,2) if a[i:i+2]!=b[i:i+2]))
            ticks.append(dict(frame=f,cycles=m.cycles,words=words,frames_out=len(out)))
            if args.profile and m.cycles>args.slow*LINE:slow.append((f,round(m.cycles/LINE),words,sorted(m.by_function.items(),key=lambda x:-x[1])[:3]))
            if f<args.warmup:fidelity.clear();frames.clear();fn_total.clear()
            if f>=args.warmup:
                for k,v in m.by_function.items():fn_total[k]=fn_total.get(k,0)+v
            m.by_function={}
            if parser.bad_frames or parser.delta_misses:
                if args.stop_on_error:raise SystemExit('parser fault at frame %d: %s'%(f,parser.last_error))
    finally:core.close()
    ticks=ticks[args.warmup:];n=len(ticks);cy=[t['cycles'] for t in ticks];wd=[t['words'] for t in ticks]
    completed=sum(t['frames_out'] for t in ticks)
    def pct(v,p):s=sorted(v);return s[min(len(s)-1,int(len(s)*p))]
    gaps=[];last=None
    for f,seq,meta in frames:
        if last is not None:gaps.append(f-last)
        last=f
    # worst one-second window of published frames (60 ticks)
    per_sec=[sum(t['frames_out'] for t in ticks[i:i+60]) for i in range(0,max(1,n-59),30)]
    result=dict(resident=str(args.resident),scenario=args.scenario,ticks=n,frames_published=completed,
        published_per_60_ticks=round(completed*60/n,2),min_window_60=min(per_sec) if per_sec else None,
        cycles_mean=round(statistics.mean(cy)),cycles_p95=pct(cy,.95),cycles_max=max(cy),
        lines_mean=round(statistics.mean(cy)/LINE,1),lines_p95=round(pct(cy,.95)/LINE,1),lines_max=round(max(cy)/LINE,1),
        words_mean=round(statistics.mean(wd),1),words_max=max(wd),
        max_gap_frames=max(gaps) if gaps else None,
        exact_frames=sum(1 for b,h,d in fidelity if b==0),frames_checked=len(fidelity),
        mean_wrong_blocks=round(statistics.mean(b for b,h,d in fidelity),2) if fidelity else None,
        max_wrong_blocks=max((b for b,h,d in fidelity),default=None),wrong_hot_blocks=sum(h for b,h,d in fidelity),
        mean_delay_ticks=round(statistics.mean(d for b,h,d in fidelity),2) if fidelity else None,max_delay_ticks=max((d for b,h,d in fidelity),default=None),
        forced_releases=getattr(parser,'forced_releases',None),
        **(dict(visually_exact_frames=sum(1 for v in visual if v==0),frames_rendered=len(visual),mean_wrong_pixels=round(statistics.mean(visual),1) if visual else None,max_wrong_pixels=max(visual,default=None),frames_over_100_wrong_pixels=sum(1 for v in visual if v>100)) if renderer is not None else {}),parser_bad_frames=parser.bad_frames,delta_misses=parser.delta_misses,
        scope='mGBA game + Unicorn ARM resident + cycle model; not hardware')
    print(json.dumps(result))
    if args.profile:
        for row in slow[:25]:print('  slow tick',row)
        tot=sum(fn_total.values())
        for k,v in sorted(fn_total.items(),key=lambda x:-x[1])[:14]:print('  %-26s %5.1f%%  %6.0f cycles/tick'%(k,100*v/tot,v/n))
        print('tick() hottest 16-byte blocks (address: cycles per tick incl. warmup):')
        for a,v in sorted(m.pc_cycles.items(),key=lambda x:-x[1])[:14]:print('  %08x %8.0f'%(a,v/max(1,len(ticks)+args.warmup)))
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--resident',default='build/emerald-columns');ap.add_argument('--state',type=Path,default=ROOT/'build/motion/field.state')
    ap.add_argument('--scenario',choices=sorted(KEYS),default='h');ap.add_argument('--frames',type=int,default=600)
    ap.add_argument('--entry',type=int,default=0,help='fixed VBlank handler exit line; default random 198..210');ap.add_argument('--seed',type=int,default=1)
    ap.add_argument('--parser',choices=('auto','stream','graphics'),default='auto')
    ap.add_argument('--warmup',type=int,default=0,help='ticks excluded from statistics');ap.add_argument('--render',action='store_true',help='compare rendered pixels of published frames with the true frame');ap.add_argument('--profile',action='store_true');ap.add_argument('--slow',type=int,default=70,help='profile: list ticks longer than this many lines');ap.add_argument('--stop-on-error',action='store_true');ap.add_argument('--trace',type=int,nargs=2,help='print every tick between two frames')
    run(ap.parse_args())
