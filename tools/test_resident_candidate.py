"""Run existing ARM protocol/codec checks on the isolated budget candidate."""
import shutil,tempfile,unittest,os
from pathlib import Path
import test_emerald,test_graphics_lz
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'build'/os.environ.get('GBM_CANDIDATE','emerald-next')

class ScanBounds(unittest.TestCase):
 def test_empty_mask_finishes_and_visible_lines_yield(self):
  import struct
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3
  from verify_firmware import elf_symbols
  folder=CANDIDATE;sym=elf_symbols((folder/'resident.elf').read_bytes())
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000)):u.mem_map(address,size)
  blob=(folder/'resident.bin').read_bytes();u.mem_write(0x0203cf80,blob)
  offset=sym['__hot_load__'][0]-0x0203cf80;size=sym['__hot_end__'][0]-sym['__hot_start__'][0]
  u.mem_write(sym['__hot_start__'][0],blob[offset:offset+size])
  for line,expected in ((160,393),(0,0x80000000),(224,0x80000000)):
   u.mem_write(0x04000006,struct.pack('<H',line))
   for reg,value in ((UC_ARM_REG_SP,0x0203fc00),(UC_ARM_REG_LR,0x03007000),(UC_ARM_REG_R0,0),(UC_ARM_REG_R1,0x02001000),(UC_ARM_REG_R2,0),(UC_ARM_REG_R3,0x02002000)):u.reg_write(reg,value)
   u.emu_start(sym['scan_next'][0],0x03007000,count=5000)
   self.assertEqual(u.reg_read(UC_ARM_REG_R0),expected)

def main():
    with tempfile.TemporaryDirectory(prefix='gbm-candidate-') as directory:
        root=Path(directory);target=root/'build/emerald';target.mkdir(parents=True)
        for name in ('resident.elf','resident.bin'):
            shutil.copyfile(CANDIDATE/name,target/name)
        originals=(test_emerald.ROOT,test_graphics_lz.ROOT)
        try:
            test_emerald.ROOT=root;test_graphics_lz.ROOT=root
            suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
                                     for m in (test_emerald,test_graphics_lz))
            suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(ScanBounds))
            result=unittest.TextTestRunner(verbosity=2).run(suite)
        finally:test_emerald.ROOT,test_graphics_lz.ROOT=originals
    return not result.wasSuccessful()

if __name__=='__main__':raise SystemExit(main())
