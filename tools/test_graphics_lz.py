"""Execute the compiled GBA encoder; decode exact data and reject invalid tokens."""
import sys,struct,unittest,random,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from graphics_stream import GraphicsParser,packet
from verify_firmware import elf_symbols
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR
class Echo:
 def render(self,data):return bytes(data)
def decode(body):
 p=GraphicsParser(Echo());p.feed(packet(0,0,0,struct.pack('<3H',1,0,0),version=0x600))
 p.feed(packet(0,6,9,body,version=0x600));return p
class Tests(unittest.TestCase):
 def test_real_arm_encoder(self):
  sym=elf_symbols((ROOT/'build/emerald/resident.elf').read_bytes());u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  u.mem_map(0x02000000,0x40000);u.mem_map(0x03000000,0x8000)
  u.mem_write(0x0203cf80,(ROOT/'build/emerald/resident.bin').read_bytes())
  rng=random.Random(872);cases=[list(range(16))*8,[23]*128,list(range(128))]
  cases += [[rng.randrange(65536) for _ in range(128)] for _ in range(20)]
  cases += [(lambda tile:(tile*32)[:128])([rng.randrange(65536) for _ in range(4)]) for _ in range(20)]
  sizes=[]
  for words in cases:
   source=struct.pack('<128H',*words);u.mem_write(0x02001000,source)
   u.mem_write(0x0203f800,b'\xa5'*1024)
   u.mem_write(sym['packet'][0]+24,b'\x5a'*256)
   u.reg_write(UC_ARM_REG_R0,0x02001000);u.reg_write(UC_ARM_REG_R1,128);u.reg_write(UC_ARM_REG_SP,0x0203fc00);u.reg_write(UC_ARM_REG_LR,0x03007000)
   u.emu_start(sym['compress_lz'][0],0x03007000,count=1000000);n=u.reg_read(UC_ARM_REG_R0);sizes.append(n)
   self.assertEqual(bytes(u.mem_read(0x0203f800,256)),b'\xa5'*256)
   if n<128:
    p=decode(bytes(u.mem_read(sym['packet'][0]+24,n*2)));self.assertEqual(p.bad_frames,0);self.assertEqual(p.pending[9*256:10*256],source)
   else:self.assertEqual(bytes(u.mem_read(sym['packet'][0]+24,256)),b'\x5a'*256)
  self.assertLess(sizes[0],24);self.assertEqual(sizes[2],128)
 def test_invalid_tokens(self):
  for words in ([0],[0x8000],[1,7,0xffff],[1,3,0x8000|(124<<7),0], [1], [1,5,0x8000]):
   with self.subTest(words=words[:4]):
    p=decode(struct.pack('<'+'H'*len(words),*words));self.assertTrue(p.bad_frames or p.bad_headers);self.assertTrue(p.pending is None)
if __name__=='__main__':unittest.main()
