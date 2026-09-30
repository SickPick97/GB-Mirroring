"""The real resident, injected into the emulated game, must not stop the game at the start of a wild battle.

Regression for the 0.12.0-0.12.2 crash: work done before the game's own VBlank handler (reading the copy queues)
desynchronised the per-scanline interrupts of the battle transition and the game never ran again.
Needs the local cartridge and the fixtures from prepare_motion_state.py and prepare_battle_state.py; skipped otherwise.
"""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
ROM=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
STATE=ROOT/'build/motion/pre_battle.state';RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
BATTLE_VBLANK=0x08038a2d
@unittest.skipUnless(ROM.is_file() and STATE.is_file() and (RESIDENT/'resident.elf').is_file(),'cartridge, battle fixture and built resident required')
class BattleTransition(unittest.TestCase):
 def test_game_keeps_running_into_the_battle(self):
  from mgba_headless import Core
  from verify_firmware import elf_symbols
  state=bytearray(STATE.read_bytes());keys=[int(x) for x in (ROOT/'build/motion/pre_battle.keys').read_text().split(',')]
  sy=elf_symbols((RESIDENT/'resident.elf').read_bytes());blob=bytearray((RESIDENT/'resident.bin').read_bytes())
  struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0]);state[0x5df80:0x5df80+len(blob)]=blob
  struct.pack_into('<I',state,0x20ffc,0x203cf80);struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1)
  core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',ROM.read_bytes())
  try:
   core.run();core.restore(state);counters=[];callbacks=set()
   for f in range(400):
    core.run(1,keys[f//16] if f<len(keys)*16 else 0);s=core.state()
    counters.append(struct.unpack_from('<I',s,0x19000+0x22e0)[0]);callbacks.add(struct.unpack_from('<I',s,0x19000+0x22cc)[0])
  finally:core.close()
  self.assertIn(BATTLE_VBLANK,callbacks,'the battle never started')
  self.assertGreaterEqual(counters[-1]-counters[0],390,'the game stopped counting VBlanks')
  self.assertGreater(counters[-1],counters[-60])
if __name__=='__main__':unittest.main()
