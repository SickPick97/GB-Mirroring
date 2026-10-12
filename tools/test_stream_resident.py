"""Real ARM resident driven by an emulated game: valid packets, complete cache, exact registers/OAM.

Needs the local cartridge image and the motion state (tools/prepare_motion_state.py); skipped otherwise.
Timing is an approximate cycle model, so only structural properties are asserted here.
"""
import os,struct,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/pylib'))
ROM=Path(os.environ.get('GBM_ROM') or ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba')
STATE=ROOT/'build/motion/field.state'
RESIDENT=ROOT/os.environ.get("GBM_RESIDENT","build/emerald-stream")
def ready():return ROM.is_file() and STATE.is_file() and (RESIDENT/'resident.elf').is_file()
@unittest.skipUnless(ready(),'local cartridge, motion state and built resident required')
class Resident(unittest.TestCase):
 def run_cosim(self,scenario,frames,warmup):
  result=subprocess.run([sys.executable,str(ROOT/'tools/cosim_stream.py'),'--resident','build/emerald-stream','--scenario',scenario,'--frames',str(frames),'--warmup',str(warmup),'--idle-start','70','--stop-on-error'],capture_output=True,text=True,cwd=ROOT)
  self.assertEqual(result.returncode,0,result.stderr[-800:]+result.stdout[-800:])
  import json
  return json.loads(result.stdout.strip().splitlines()[0])
 def test_static_scene_completes_cache_and_publishes_every_tick(self):
  r=self.run_cosim('stay',560,380)
  self.assertEqual(r['parser_bad_frames'],0);self.assertEqual(r['delta_misses'],0)
  self.assertGreaterEqual(r['published_per_60_ticks'],58)
  self.assertEqual(r['wrong_hot_blocks'],0)
  self.assertLess(r['mean_wrong_blocks'],3)
  self.assertLessEqual(r['words_max'],225+36)
 def test_walking_publishes_continuously(self):
  r=self.run_cosim('h',600,400)
  self.assertEqual(r['parser_bad_frames'],0);self.assertEqual(r['wrong_hot_blocks'],0)
  self.assertGreaterEqual(r['published_per_60_ticks'],58)
  self.assertLessEqual(r['max_delay_ticks'],8)

def built():return (RESIDENT/'resident.elf').is_file()
@unittest.skipUnless(built(),'built resident required')
class Controls(unittest.TestCase):
 """Key combinations and tick gating, driven directly on the ARM code (no game needed)."""
 def machine(self):
  sys.path.insert(0,str(ROOT/'tools'))
  os.environ.setdefault('GBM_ARM_TOOLCHAIN','D:/Progettini')
  import cosim_stream
  m=cosim_stream.Machine(RESIDENT);m.load_graphics(bytes(100608));return m
 def packets(self,m,frames,keys=None,entry=205,start=1):
  emitted=[]
  for f in range(start,start+frames):
   if keys:m.u.mem_write(0x04000130,struct.pack('<H',keys.get(f,0x3ff)))
   wire,words=m.tick(f,entry);emitted.append(words>0)
  return emitted
 def longest_tick(self,m,frames,before=None):
  import cosim_stream
  longest=0
  for f in range(1,frames+1):
   if before:before(m,f)
   m.tick(f,205);longest=max(longest,m.cycles/cosim_stream.LINE)
  return longest
 def test_unknown_scene_never_runs_a_tick_past_the_budget(self):
  """Battle and other unknown callbacks: sweeping a static screen must stay bounded (0.12.0 spent whole frames here)."""
  m=self.machine();self.assertLess(self.longest_tick(m,60,lambda mm,f:mm.word(0x030022cc,0x08123457)),90)
 def test_link_register_poked_every_frame_does_not_force_full_sweeps(self):
  m=self.machine();self.assertLess(self.longest_tick(m,60,lambda mm,f:mm.u.mem_write(0x04000134,struct.pack('<H',0))),90)
 def test_hblank_scene_gets_a_full_tick(self):
  """0.13 runs the tick with the game's interrupts enabled, so HBlank scenes are no longer cut short."""
  import random
  m=self.machine();rng=random.Random(3);m.load_graphics(bytes(rng.getrandbits(8) for _ in range(100608)))
  m.u.mem_write(0x04000200,struct.pack('<H',0x0003));m.word(0x030022cc,0x080863a5)
  m.tick(1,205);m.idle(60)
  m.load_graphics(bytes(rng.getrandbits(8) for _ in range(100608)))
  wire,words=m.tick(2,205);self.assertGreater(words,100)
 def test_unknown_scene_with_hblank_still_sends_registers(self):
  m=self.machine();m.u.mem_write(0x04000200,struct.pack('<H',0x0003));m.word(0x030022cc,0x08123457)
  wire,words=m.tick(1,205);self.assertGreater(words,12)
 def test_capture_every_vblank_by_default(self):
  m=self.machine();self.assertTrue(all(self.packets(m,12)))
 def test_late_handler_exit_skips_the_tick(self):
  """As in 0.13.0, the resident this one is built on: a handler that ended after scanline 223 leaves no time."""
  m=self.machine();self.assertEqual(self.packets(m,4,entry=226),[False]*4)
 def test_select_r_a_no_longer_changes_the_rate(self):
  """The cadence key of 0.11-0.15 is gone (its code made room for the announcements): every VBlank is captured."""
  m=self.machine();select_r_a=0x3ff&~0x105
  keys={f:select_r_a for f in (3,4)};keys.update({f:0x3ff for f in (5,6)})
  self.assertTrue(all(self.packets(m,30,keys=keys)))
 def settled(self,m,parser,gfx,frames=40,start=1):
  """Runs ticks and idle time with the PC's verdict fed back, as the bench does; returns the next frame number."""
  for f in range(start,start+frames):
   m.verdict=parser.verdict();m.load_graphics(bytes(gfx))
   wire,_=m.tick(f,205);parser.feed(wire);wire,_=m.idle(40);parser.feed(wire)
  return start+frames
 def test_palette_fade_is_announced_and_rebuilt_by_the_pc(self):
  """A normal fade of a whole palette block goes as its hash plus colour and step (record 15); the unfaded palette
  the PC lacks goes once (record 16). The PC's palette is exactly the console's at every step."""
  import random
  sys.path.insert(0,str(ROOT/'tools'))
  from stream_parser import StreamParser,fade_block
  from test_stream_parser import Echo
  m=self.machine();parser=StreamParser(Echo());rng=random.Random(5);kinds={}
  parser.packet_log=lambda e:[kinds.__setitem__(k,kinds.get(k,0)+v) for k,v in e['codecs'].items()]
  gfx=bytearray(100608);plain=bytes(b&0x7f if i&1 else b for i,b in enumerate(rng.randbytes(1024)));gfx[256:1280]=plain
  m.u.mem_write(0x02037714,plain);m.word(0x02037fd4,0);m.word(0x02037fd8,0);m.word(0x02037fdc,0)
  f=self.settled(m,parser,gfx);self.assertEqual(bytes(parser.cache[256:1280]),plain);self.assertGreater(m.read32(m.symbol('verdict_ok')),0)
  def fade(unfaded,color,step,frame):
   m.u.mem_write(0x02037714,unfaded);m.word(0x02037fd4,0xffffffff);m.u.mem_write(0x02037fd8,struct.pack('<HH',step<<6,0x8000|color))
   now=b''.join(fade_block(unfaded[i:i+256],color,step) for i in range(0,1024,256));gfx[256:1280]=now
   frame=self.settled(m,parser,gfx,3,frame);self.assertEqual(bytes(parser.cache[256:1280]),now,(color,step));return frame
  kinds.clear()
  for step in (2,4,6,8,10,12,14,16):f=fade(plain,0,step,f)
  self.assertGreaterEqual(kinds.get('15',0),32);self.assertNotIn('16',kinds);self.assertNotIn('1',kinds)
  # a new scene fades in from white: its palette is not on the PC yet
  fresh=bytes(b&0x7f if i&1 else b for i,b in enumerate(rng.randbytes(1024)));kinds.clear()
  for step in (14,10,6,2,0):f=fade(fresh,0x7fff,step,f)
  self.assertEqual(kinds.get('16'),4);self.assertGreaterEqual(kinds.get('15',0),16)
  self.assertEqual(m.read32(m.symbol('pal_raw')),0)
 def test_fade_of_part_of_a_palette_block_goes_as_data(self):
  """Only some palettes of the block selected: other effects may own the rest, so the block is sent, not announced."""
  import random
  sys.path.insert(0,str(ROOT/'tools'))
  from stream_parser import StreamParser,fade_block
  from test_stream_parser import Echo
  m=self.machine();parser=StreamParser(Echo());rng=random.Random(6);kinds={}
  parser.packet_log=lambda e:[kinds.__setitem__(k,kinds.get(k,0)+v) for k,v in e['codecs'].items()]
  gfx=bytearray(100608);plain=bytes(b&0x7f if i&1 else b for i,b in enumerate(rng.randbytes(1024)));gfx[256:1280]=plain
  m.u.mem_write(0x02037714,plain);m.word(0x02037fd4,0);m.word(0x02037fd8,0);m.word(0x02037fdc,0)
  f=self.settled(m,parser,gfx);kinds.clear()
  m.word(0x02037fd4,0x00000003);m.u.mem_write(0x02037fd8,struct.pack('<HH',8<<6,0x8000))
  gfx[256:288]=fade_block(plain[:256],0,8)[:32];f=self.settled(m,parser,gfx,3,f)
  self.assertEqual(bytes(parser.cache[256:1280]),bytes(gfx[256:1280]));self.assertNotIn('15',kinds)
 def test_inside_the_adapter_probe_packets_end_before_the_games_timer(self):
  """After a door the game waits on timer 3 in 27-scanline steps: the resident sends only what is finished before
  the timer reaches 32, so the game is not delayed (the whole frame used there made the entrance 50 frames longer)."""
  import random,cosim_stream
  sys.path.insert(0,str(ROOT/'tools'))
  from stream_parser import StreamParser
  from test_stream_parser import Echo
  m=self.machine();parser=StreamParser(Echo());rng=random.Random(7)
  gfx=bytearray(rng.randbytes(100608));f=self.settled(m,parser,gfx,120)
  self.assertEqual(bytes(parser.cache[2304:]),bytes(gfx[2304:]))
  # a scene change, then the probe: everything is new
  gfx[2304:]=rng.randbytes(100608-2304);m.word(0x030022cc,0x08123457);m.verdict=parser.verdict();m.load_graphics(bytes(gfx))
  wire,_=m.tick(f,205);parser.feed(wire);sent=0;packets=0
  for start in (0,3,6,9,11,0,2,5,8,0,4,7,10,1):
   m.verdict=parser.verdict();m.probe=start;wire,words=m.idle(40+packets%60);m.probe=None;parser.feed(wire)
   self.assertLessEqual(start+m.cycles//1024,32,'idle work ran past the end of the game\'s wait (started at step %d)'%start)
   self.assertLessEqual(words,2*(140+12));sent+=words;packets+=words>0
  self.assertGreater(sent,200,'nothing was sent inside the probe');self.assertEqual(parser.bad_frames,0)
  # too late in a wait: nothing is started
  m.probe=20;wire,words=m.idle(60);m.probe=None;self.assertEqual(words,0);self.assertLess(m.cycles,1232)
 def test_select_l_r_pauses_and_resumes(self):
  m=self.machine();toggle=0x3ff&~0x304
  keys={f:toggle for f in (3,4)};keys.update({f:0x3ff for f in (5,6)})
  seen=self.packets(m,10,keys=keys)
  self.assertTrue(all(seen[:2]));self.assertFalse(any(seen[2:]))
  keys2={f:toggle for f in (13,14)};keys2.update({f:0x3ff for f in (15,16)})
  seen=self.packets(m,12,keys=keys2,start=11);self.assertTrue(seen[-1])
if __name__=='__main__':unittest.main()
