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
      # build/motion/surf.state: wild battle whose first move was set to Surf; A every half second uses it.
      'surf':lambda f:1<<8 if f%30<3 else 0,
      'battle':lambda f:1<<8 if f>=300 and f%40<3 else 0,
      'menus':lambda f:(1<<3 if 120<=f<123 else 1<<8 if 240<=f<243 else 1 if 480<=f<483 or 660<=f<663 else 0),
      'team':lambda f:(1<<3 if 120<=f<123 else 1<<5 if 180<=f<183 else 1<<8 if 240<=f<243 else 1 if 480<=f<483 or 660<=f<663 else 0)}

def _recorded(name):
    # keys recorded with a fixture (one value per 16 frames), e.g. the walk into the grass before a wild battle
    path=ROOT/'build/motion'/(name+'.keys')
    keys=[int(x) for x in path.read_text().split(',')] if path.is_file() else []
    return lambda f:keys[f//16] if f<len(keys)*16 else 0
KEYS['prebattle']=_recorded('pre_battle')

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
        u.hook_add(UC_HOOK_MEM_READ,self._sd,begin=0x04000134,end=0x04000135)
        self.slot=None;self.slot_pos=0;self.slot_done=False;self.slots=0;self.verdict=None;self.link_value=0x8030
        self.pio=None;self.pio_last=0;self.pio_debt=0.0;self.contention=0
        u.hook_add(UC_HOOK_MEM_READ,self._vcount,begin=0x04000006,end=0x04000007)
        u.hook_add(UC_HOOK_MEM_READ,self._timer3,begin=0x0400010c,end=0x0400010f);self.probe=None
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
        # Pico 0.8.1 control slot: with SD released by the GBA, a rising SC starts the answer (present, no resync, then
        # the 448 verdict bits); every falling SC moves to the next bit, and the last one releases SD (pulled high).
        if self.pio is not None:
            # instruction-level Pico model (test_control.Machine), stepped by elapsed GBA cycles
            self._pio_advance()
            if self.pio.direction and value&32:self.contention+=1
        elif value&32:self.slot=None;self.slot_done=False
        else:
            if value&1 and not b['clock'] and self.slot is None and not self.slot_done:
                data=self.verdict or b'\xff'*56
                self.slot=[0,0]+[(data[i>>3]>>(i&7))&1 for i in range(448)];self.slot_pos=0;self.slot_done=True;self.slots+=1
            elif b['clock'] and not value&1 and self.slot is not None:
                self.slot_pos+=1
                if self.slot_pos>=len(self.slot):self.slot=None
        self.link_value=value
        if value&32 and value&1 and not b['clock']:
            b['word']=((b['word']<<1)|((value>>1)&1))&65535;b['bits']+=1
            if b['bits']==16:b['words'].append(b['word']);b['bits']=0
        b['clock']=value&1
    def _pio_advance(self):
        # 125 MHz / 16 per PIO instruction against 16.78 MHz GBA cycles
        self.pio_debt+=(self.cycles-self.pio_last)*(125e6/16/16777216);self.pio_last=self.cycles
        steps=int(self.pio_debt);self.pio_debt-=steps
        for _ in range(steps):self.pio.step(self.bus['clock'])
    def _sd(self,uc,access,address,size,value,user):
        if self.pio is not None:
            self._pio_advance();bit=self.pio.pin if self.pio.direction else 1
            uc.mem_write(0x04000134,struct.pack('<H',(self.link_value&~2)|(bit<<1)));return
        bit=self.slot[self.slot_pos] if self.slot is not None else 1
        uc.mem_write(0x04000134,struct.pack('<H',(self.link_value&~2)|(bit<<1)))
    def _timer3(self,uc,access,address,size,value,user):
        # The game's wireless-adapter probe: timer 3 runs (0x83) and counts 1024 cycles a step from `probe` while the
        # resident works inside one of its waits; stopped otherwise.
        if self.probe is None:uc.mem_write(0x0400010c,bytes(4))
        else:uc.mem_write(0x0400010c,struct.pack('<HH',min(0xffff,self.probe+self.cycles//1024),0x83))
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
        u.mem_write(0x02038c00,bytes(state[0x21000+0x38c00:0x21000+0x39c00]))
        # scanline effect: gScanlineEffect, its double buffer and DMA0 control (the resident reads them after VBlank)
        u.mem_write(0x040000ba,bytes(state[0x400+0xba:0x400+0xbc]))
        u.mem_write(0x030022cc,bytes(state[0x19000+0x22cc:0x19000+0x22d0]))
        u.mem_write(0x04000200,struct.pack('<HH',1,1))
    def observe(self):
        self.u.reg_write(UC_ARM_REG_SP,0x03007f00);self.u.reg_write(UC_ARM_REG_LR,0x03007000)
        self.u.emu_start(self.symbol('observe'),0x03007000,count=2000000)
    def load_graphics(self,gfx):
        u=self.u
        u.mem_write(0x03000818,gfx[:96]);u.mem_write(0x05000000,gfx[256:1280]);u.mem_write(0x07000000,gfx[1280:2304]);u.mem_write(0x06000000,gfx[2304:])
    def tick(self,now,entry_line,irq_lr=0x080008ca):
        self.word(0x030022e0,now);self.entry=entry_line;self.cycles=0
        # by default the game was waiting in WaitForVBlank (0x080008c6) when VBlank came
        if 'irq_lr' in self.sy:self.word(self.symbol('irq_lr'),irq_lr)
        self.u.reg_write(UC_ARM_REG_SP,0x03007f00);self.u.reg_write(UC_ARM_REG_LR,0x03007000)
        self.u.mem_write(0x04000006,struct.pack('<H',entry_line))
        self.u.emu_start(self.symbol('tick'),0x03007000,count=20000000)
        words=self.bus['words'];self.bus['words']=[]
        return struct.pack('<'+'H'*len(words),*words),len(words)
    def idle(self,entry_line):
        """The resident's idle-time work (timer 1 while the game waits for VBlank), from entry_line."""
        if 'idle' not in self.sy:return b'',0
        self.entry=entry_line;self.cycles=0
        # waiting in WaitForVBlank: gMain.intrCheck VBlank flag clear
        self.u.mem_write(0x030022dc,struct.pack('<H',struct.unpack('<H',self.u.mem_read(0x030022dc,2))[0]&~1))
        self.u.reg_write(UC_ARM_REG_SP,0x03007f00);self.u.reg_write(UC_ARM_REG_LR,0x03007000)
        self.u.emu_start(self.symbol('idle'),0x03007000,count=40000000)
        words=self.bus['words'];self.bus['words']=[]
        return struct.pack('<'+'H'*len(words),*words),len(words)

def measure_timing(args,frames):
    """Game-alone timing from mGBA with the MEASURE build of the resident injected (it sends nothing): for every
    VBlank the scanline where the game's handler ended, the interrupted address (busy or waiting) and the scanline
    where the game started waiting for the next VBlank (2-line steps, 0 when it never did)."""
    from verify_firmware import elf_symbols
    folder=ROOT/'build/emerald-stream-misura'
    sy=elf_symbols((folder/'resident.elf').read_bytes());blob=bytearray((folder/'resident.bin').read_bytes())
    state=bytearray(Path(args.state).read_bytes())
    rom=(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom);rows=[]
    rd=lambda st,n:struct.unpack_from('<I',st,0x21000+sy[n][0]-0x02000000)[0]
    try:
        core.run();core.restore(state);core.run(60);st=bytearray(core.state())
        struct.pack_into('<I',blob,4,struct.unpack_from('<I',st,0x20ffc)[0]);st[0x5df80:0x5df80+len(blob)]=blob
        struct.pack_into('<I',st,0x20ffc,0x0203cf80);struct.pack_into('<I',st,0x21000+sy['enabled'][0]-0x02000000,1)
        core.restore(st)
        for f in range(frames):
            core.run(1,KEYS[args.scenario](f));st=core.state()
            rows.append((rd(st,'m_first'),rd(st,'m_lr'),rd(st,'m_line')))
    finally:core.close()
    return rows

def parser_pending(wire):
    """pending field of the last packet in a chunk of wire words (0x700 tick or bulk)"""
    i=wire.rfind(bytes((0x7e,0xb4,0x47,0x56)))
    return struct.unpack_from('<H',wire,i+24+6)[0]&511 if i>=0 and len(wire)>=i+32 else -1

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
    if stream and args.store:parser.load_store(args.store)
    if stream and args.rom_index:
        import rom_blocks;parser.rom_index=rom_blocks.build(rom_bytes);parser.raw_index=rom_blocks.build_raw(rom_bytes)
    verdict_now=None
    if stream:
        import rom_blocks;parser.fade_solver=rom_blocks.fade_solver()
    renderer=None
    if args.render:
        from native_renderer import Renderer
        renderer=Renderer();visual=[]
    truth={};fidelity=[]
    # one emulator instance at a time: the measuring pass ends before the main one starts
    timing=measure_timing(args,args.frames+3) if args.timing=='measured' else None
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes())
    slow=[];ticks=[];frames=[];last_gfx=None;mismatch=0;checked=0;fn_total={}
    try:
        core.run();core.restore(bytearray(Path(args.state).read_bytes()));core.run(60)
        pending_state=core.state()
        debt=0.0;carry_busy=False;packets=[];model=dict(busy_ticks=0,idle_frames=0,no_idle_frames=0)
        if stream:parser.packet_log=lambda e:packets.append(dict(e,f=f))
        for f in range(args.frames):
            core.run(1,KEYS[args.scenario](f));state=core.state();gfx=graphics_from_state(state)
            # requests queued in the previous snapshot are executed by this VBlank; the resident sees their result
            m.load_environment(pending_state);m.observe();pending_state=state
            m.load_graphics(gfx);truth[f+1]=gfx;truth.pop(f-200,None)
            # the game's unfaded palette and fade state, as the tick after this VBlank finds them
            m.u.mem_write(0x02037714,bytes(state[0x21000+0x37714:0x21000+0x37fe0]))
            entry=args.entry if args.entry else rng.choice((198,200,202,204,206,208,210))
            idle_at=args.idle_start
            if stream and args.verdict:m.verdict=verdict_now
            if timing:
                # Closed loop on measured game timing: the tick delays the game's frame by its own length; the game
                # then starts waiting (idle time) that much later, or is still busy at the next VBlank.
                lr,line=timing[f+1][1],timing[f+1][2];first=timing[f+2][0]
                entry=line if 160<=line<228 else 200
                at_wait=((lr-0x080008ca)&0xffffffff)<=8;probing=((lr-0x082e7d5c)&0xffffffff)<=6
                busy=carry_busy or not at_wait
                wire,words=m.tick(f+1,entry,lr if probing else 0x08000100 if busy else (lr if at_wait else 0x080008ca))
                tick_lines=m.cycles/LINE;model['busy_ticks']+=busy
                to_vblank=(160+228-entry)%228
                if not first:carry_busy=False;debt=min(debt+tick_lines,228.0);idle_at=None
                else:
                    reach=(first-1+228-entry)%228+tick_lines+debt
                    if reach>=to_vblank:carry_busy=True;debt=reach-to_vblank;idle_at=None
                    else:
                        carry_busy=False;debt=0.0
                        # the idle timer runs every ten scanlines from the end of the tick
                        steps=max(1,-(-(reach-tick_lines)//10))
                        at=entry+tick_lines+10*steps
                        # a check that lands in the VBlank lines is repeated every ten lines until the frame starts
                        while 160<=at%228:at+=10
                        idle_at=int(at)%228
                        if not idle_at<156 or at>=entry+to_vblank:idle_at=None
                if probing:idle_at=None;carry_busy=False;debt=0.0
                model['idle_frames' if idle_at is not None else 'no_idle_frames']+=1
            else:
                wire,words=m.tick(f+1,entry)
            lines=m.cycles/LINE;tick_cycles=m.cycles
            if args.trace and args.trace[0]<=f<args.trace[1]:
                pend=struct.unpack_from('<H',wire,30)[0] if len(wire)>=32 else -1
                print('  f%4d entry %3d lines %5.1f words %3d pending %3d cb %08x'%(f,entry,lines,words,pend,m.read32(0x030022cc)))
            out=parser.feed(wire)
            idle_words=0
            if timing and probing:
                # Inside the probe the game waits about 27 scanlines at a time, eight times a frame; the resident's
                # timer finds each wait a few scanlines in (the emulated game gives 0-12 steps).
                m.load_environment(state);model['probe_frames']=model.get('probe_frames',0)+1
                for k in range(8):
                    line=int(entry+tick_lines+2+27*k)%228
                    if line>=150:continue
                    m.probe=rng.randrange(0,13)
                    probe_wire,probe_words=m.idle(line);m.probe=None
                    model['probe_overrun']=max(model.get('probe_overrun',0),m.cycles//1024+0)
                    idle_words+=probe_words;out+=parser.feed(probe_wire)
            if idle_at is not None:
                # the game finished its frame and waits for the next VBlank: queues for that VBlank are final
                m.load_environment(state)
                idle_wire,idle_words=m.idle(idle_at);out+=parser.feed(idle_wire)
                if args.trace and args.trace[0]<=f<args.trace[1]:print('  f%4d idle words %4d idle lines %5.1f pending after idle %d held %d'%(f,idle_words,m.cycles/LINE,parser_pending(idle_wire),len(parser.held)))
            if stream:verdict_now=parser.verdict()
            for seq,img,wire_bytes,codec,meta in out:
                frames.append((f,seq,meta));ref=truth.get(meta.get('end_game_frame',meta.get('game_frame')))
                if ref is not None:
                    bad=[b for b in range(393) if img[b*256:(b+1)*256]!=ref[b*256:(b+1)*256]]
                    fidelity.append((len(bad),sum(1 for b in bad if b<9),f-(meta.get('end_game_frame',f+1)-1)))
                    if args.show_wrong and bad and f>=args.warmup:
                        from stream_parser import block_fold
                        hs=m.u.mem_read(m.symbol('hashes'),393*4)
                        for b in bad[:4]:
                            tw=struct.unpack('<64I',ref[b*256:(b+1)*256]);pw=struct.unpack('<64I',img[b*256:(b+1)*256])
                            print('    diff words',[(i,hex(tw[i]),hex(pw[i])) for i in range(64) if tw[i]!=pw[i]][:10])
                            print('    block %d gba-hash %08x truth %08x pc %08x'%(b,struct.unpack_from('<I',hs,b*4)[0],block_fold(ref[b*256:(b+1)*256]),block_fold(img[b*256:(b+1)*256])))
                    if args.show_wrong and bad and f>=args.warmup:print('  wrong f%d tick %d held %s idle %s blocks %s'%(f,meta.get('end_game_frame'),meta.get('held_frames'),meta.get('idle_packets'),bad[:10]))
                    if renderer is not None and f>=args.warmup:
                        a=renderer.render(img);b=renderer.render(ref)
                        visual.append(sum(1 for i in range(0,76800,2) if a[i:i+2]!=b[i:i+2]))
            ticks.append(dict(frame=f,cycles=tick_cycles,words=words,idle_words=idle_words,frames_out=len(out)))
            if args.profile and tick_cycles>args.slow*LINE:slow.append((f,round(m.cycles/LINE),words,sorted(m.by_function.items(),key=lambda x:-x[1])[:3]))
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
        frames_held_over_8=sum(1 for f,q,mt in frames if mt.get('held_frames',1)>8),frames_held_over_1=sum(1 for f,q,mt in frames if mt.get('held_frames',1)>1),
        **(dict(visually_exact_frames=sum(1 for v in visual if v==0),frames_rendered=len(visual),mean_wrong_pixels=round(statistics.mean(visual),1) if visual else None,max_wrong_pixels=max(visual,default=None),frames_over_100_wrong_pixels=sum(1 for v in visual if v>100)) if renderer is not None else {}),parser_bad_frames=parser.bad_frames,delta_misses=parser.delta_misses,
        scope='mGBA game + Unicorn ARM resident + cycle model; not hardware')
    if stream and packets:
        # scene loads as the hardware log shows them: from more than 300 blocks outstanding until none
        loads=[];i=0
        while i<len(packets):
            if packets[i]['pending']>300 and (i==0 or packets[i-1]['pending']<100):
                j=next((k for k in range(i,len(packets)) if packets[k]['pending']==0),len(packets)-1);seg=packets[i:j+1]
                loads.append(dict(start_frame=packets[i]['f'],frames=packets[j]['f']-packets[i]['f'],ticks=sum(1 for q in seg if q['t']=='tick'),idle_packets=sum(1 for q in seg if q['t']=='idle'),
                    words=sum(q['words'] for q in seg),raw_blocks=sum(q['codecs'].get('1',0) for q in seg),empty_ticks=sum(1 for q in seg if q['t']=='tick' and q['words']<=20)));i=j
            i+=1
        totals={}
        for q in packets:
            for k,v in q['codecs'].items():totals[k]=totals.get(k,0)+v
        result['records_by_kind']=dict(sorted(totals.items(),key=lambda kv:int(kv[0])));result['fade_hits']=parser.fade_hits
        result['loads']=loads;result['model']=model;result['store_hits']=parser.store_hits;result['store_misses']=parser.store_misses;result['control_slots']=m.slots
        if args.store:parser.save_store(args.store)
        result['idle_packets_per_tick']=round(sum(1 for q in packets if q['t']=='idle')/max(1,sum(1 for q in packets if q['t']=='tick')),2)
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
    ap.add_argument('--rom-index',action='store_true',help='index the LZ77 graphics of the cartridge image, as the viewer does')
    ap.add_argument('--store',help='block contents seen in earlier runs: loaded before, saved after')
    ap.add_argument('--no-verdict',dest='verdict',action='store_false',help='no answer in the control slot (Pico 0.7)')
    ap.add_argument('--timing',choices=('fixed','measured'),default='fixed',help='measured: game timing from mGBA with the MEASURE build (build/emerald-stream-misura), tick delay fed back')
    ap.add_argument('--entry',type=int,default=0,help='fixed VBlank handler exit line; default random 198..210');ap.add_argument('--seed',type=int,default=1);ap.add_argument('--idle-start',type=int,default=None,help='model idle time from this scanline to the resident IDLE_END each frame')
    ap.add_argument('--parser',choices=('auto','stream','graphics'),default='auto')
    ap.add_argument('--warmup',type=int,default=0,help='ticks excluded from statistics');ap.add_argument('--render',action='store_true',help='compare rendered pixels of published frames with the true frame');ap.add_argument('--profile',action='store_true');ap.add_argument('--slow',type=int,default=70,help='profile: list ticks longer than this many lines');ap.add_argument('--stop-on-error',action='store_true');ap.add_argument('--show-wrong',action='store_true');ap.add_argument('--trace',type=int,nargs=2,help='print every tick between two frames')
    run(ap.parse_args())
