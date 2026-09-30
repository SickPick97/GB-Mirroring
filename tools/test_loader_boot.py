"""The real loader (START path) must leave the resident installed and jump into the game, with the boot stage running
from inside the resident's own hash table. Run in an ARM emulator against the local cartridge image; skipped without it."""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/pylib'));sys.path.insert(0,str(ROOT/'tools'))
RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
ROM=Path(os.environ.get('GBM_ROM') or ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba')
GAME_ENTRY=0x080003cf
@unittest.skipUnless(ROM.is_file() and (RESIDENT/'loader.bin').is_file(),'local cartridge image and built loader required')
class LoaderBoot(unittest.TestCase):
 def test_start_installs_the_resident_and_enters_the_game(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_CODE,UC_HOOK_INTR
  from verify_firmware import elf_symbols
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000),(0x08000000,0x1000000)):u.mem_map(address,size)
  rom=ROM.read_bytes();u.mem_write(0x08000000,rom);u.mem_write(0x02000000,(RESIDENT/'loader.bin').read_bytes())
  u.mem_write(0x04000130,struct.pack('<H',0xfff7))
  u.hook_add(UC_HOOK_MEM_READ,lambda uc,a,ad,s,v,us:uc.mem_write(0x04000130,struct.pack('<H',0xfff7)),begin=0x04000130,end=0x04000131)
  u.hook_add(UC_HOOK_INTR,lambda uc,n,us:None)  # BIOS calls are skipped
  reached=[]
  def stop(uc,address,size,user):
   if address==GAME_ENTRY-1:reached.append(address);uc.emu_stop()
  u.hook_add(UC_HOOK_CODE,stop,begin=GAME_ENTRY-1,end=GAME_ENTRY)
  u.mem_write(0x03007ffc,struct.pack('<I',0x03002750))  # the game's interrupt handler
  try:u.emu_start(0x02000000,0,count=60000000)
  except Exception:pass
  self.assertTrue(reached,'the loader never reached the game entry')
  blob=(RESIDENT/'resident.bin').read_bytes()
  image=bytes(u.mem_read(0x0203cf80,len(blob)))
  self.assertEqual(image[:4]+image[8:],blob[:4]+blob[8:],'resident not copied intact')
  self.assertEqual(struct.unpack('<I',u.mem_read(0x03007ffc,4))[0],0x0203cf80,'interrupt vector not pointed at the resident')
  self.assertEqual(struct.unpack('<I',u.mem_read(0x0203cf84,4))[0],0x03002750,'original handler not saved')
  table=elf_symbols((RESIDENT/'resident.elf').read_bytes())['hashes'][0]
  stage=(RESIDENT/'stage.bin').read_bytes()
  self.assertEqual(bytes(u.mem_read(table,len(stage))),stage,'boot stage not placed in the hash table')
  self.assertGreater(table,0x0203cf80+len(blob)-1,'hash table overlaps the loaded image')
if __name__=='__main__':unittest.main()
