"""Saving the game with the resident active must write exactly the same save as the game alone.

The emulated game (mGBA, local cartridge image and a copy of the local save, all in memory) opens the start menu,
chooses SAVE and confirms, with and without the resident injected; the resulting flash contents are compared byte
for byte. Nothing is written to disk. Needs the local cartridge, save and the field fixture; skipped otherwise.
"""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
SOURCE=ROOT/'PROGETTO AMICO/MGBA TEST'
ROM=SOURCE/'Pokemon - Versione Smeraldo (Italy).gba';SAVE=SOURCE/'Pokemon - Versione Smeraldo (Italy).sav'
FIELD=ROOT/'build/motion/field.state';RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
START,DOWN,A,B=1<<3,1<<5,1<<8,1
UP=1<<4
def save_game(resident,script,shots=None):
    from mgba_headless import Core
    state=bytearray(FIELD.read_bytes())
    if resident:
        from verify_firmware import elf_symbols
        sy=elf_symbols((RESIDENT/'resident.elf').read_bytes());blob=bytearray((RESIDENT/'resident.bin').read_bytes())
        struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0]);state[0x5df80:0x5df80+len(blob)]=blob
        struct.pack_into('<I',state,0x20ffc,0x203cf80);struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1)
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',ROM.read_bytes())
    try:
        core.load_save_copy(SAVE.read_bytes());core.run();core.restore(state)
        for i,(key,frames) in enumerate(script):
            core.run(4,key);core.run(frames)
            if shots is not None:shots.append(core.rgb555())
        core.lib.retro_get_memory_size.restype=__import__('ctypes').c_size_t;core.lib.retro_get_memory_data.restype=__import__('ctypes').c_void_p
        n=core.lib.retro_get_memory_size(0);ptr=core.lib.retro_get_memory_data(0)
        return __import__('ctypes').string_at(ptr,n)
    finally:core.close()
# START (cursor on POKeDEX), five down to SALVA, A, confirm YES, confirm overwrite, wait for the write, close.
SCRIPT=[(START,40)]+[(DOWN,12)]*5+[(A,60),(A,120),(A,500),(B,60),(B,60)]
@unittest.skipUnless(ROM.is_file() and SAVE.is_file() and FIELD.is_file() and (RESIDENT/'resident.elf').is_file(),'cartridge, save, field fixture and built resident required')
class SaveIntegrity(unittest.TestCase):
    def test_save_written_with_the_resident_is_identical(self):
        """Same bytes as the game alone, except the play-time clock (a busy game runs a few frames slower while the
        resident is active) and the checksum of the section holding it."""
        original=SAVE.read_bytes()
        alone=save_game(False,SCRIPT);with_resident=save_game(True,SCRIPT)
        self.assertNotEqual(alone[:len(original)],original[:len(alone)],'the scripted save did not change the flash; check the menu script')
        allowed=set()
        for sector in range(len(alone)//0x1000):
            base=sector*0x1000
            section,_,signature=struct.unpack_from('<HHI',alone,base+0xff4)
            if signature==0x08012025 and section==0:allowed|={base+0x0e,base+0x0f,base+0x10,base+0x11,base+0x12,base+0xff6,base+0xff7}
        differing=[i for i in range(len(alone)) if alone[i]!=with_resident[i]]
        self.assertTrue(allowed,'no SaveBlock2 section found')
        self.assertEqual([hex(i) for i in differing if i not in allowed],[])
        # the checksum of the section with the play time must still be valid
        for sector in range(len(with_resident)//0x1000):
            base=sector*0x1000;section,checksum,signature=struct.unpack_from('<HHI',with_resident,base+0xff4)
            if signature==0x08012025 and section==0:
                total=sum(struct.unpack_from('<%dI'%(0xf2c//4),with_resident,base))&0xffffffff
                self.assertEqual(((total>>16)+total)&0xffff,checksum)
if __name__=='__main__':unittest.main()
