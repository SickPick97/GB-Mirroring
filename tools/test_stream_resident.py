"""Real ARM resident 0.12 driven by an emulated game: valid packets, complete cache, exact registers/OAM.

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
  self.assertLessEqual(r['words_max'],216+36)
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
 def test_late_handler_exit_only_sends_a_small_tick(self):
  """A handler that ended after scanline 223 leaves no time: the tick still goes out but stays within a few scanlines."""
  import cosim_stream
  m=self.machine();longest=0
  for f in range(1,5):
   wire,words=m.tick(f,226);self.assertGreater(words,0);longest=max(longest,m.cycles/cosim_stream.LINE)
  self.assertLess(longest,30,longest)
 def test_cadence_key_halves_and_thirds_the_rate(self):
  m=self.machine()
  select_r_a=0x3ff&~0x105
  keys={f:select_r_a for f in (3,4)};keys.update({f:0x3ff for f in (5,6)})
  seen=self.packets(m,30,keys=keys)
  self.assertTrue(all(seen[:3]))
  tail=seen[6:];self.assertEqual(sum(tail),len(tail)//2,tail)
  keys2={f:select_r_a for f in (40,41)};keys2.update({f:0x3ff for f in (42,43)})
  seen=self.packets(m,42,keys=keys2,start=31)
  tail=seen[16:];self.assertLessEqual(abs(sum(tail)-len(tail)/3),1,tail)
 def test_select_l_r_pauses_and_resumes(self):
  m=self.machine();toggle=0x3ff&~0x304
  keys={f:toggle for f in (3,4)};keys.update({f:0x3ff for f in (5,6)})
  seen=self.packets(m,10,keys=keys)
  self.assertTrue(all(seen[:2]));self.assertFalse(any(seen[2:]))
  keys2={f:toggle for f in (13,14)};keys2.update({f:0x3ff for f in (15,16)})
  seen=self.packets(m,12,keys=keys2,start=11);self.assertTrue(seen[-1])
if __name__=='__main__':unittest.main()
