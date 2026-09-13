"""Execute the real Thumb/ARM column sender with four strided tilemap changes."""
import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR
from verify_firmware import elf_symbols
from graphics_stream import GraphicsParser,SIZE

class Echo:
 def render(self,data):return bytes(data)

class Tests(unittest.TestCase):
 def test_real_column_roundtrip(self):
  folder=ROOT/'build/emerald-columns';sy=elf_symbols((folder/'resident.elf').read_bytes());blob=(folder/'resident.bin').read_bytes()
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)):u.mem_map(address,size)
  u.mem_write(0x0203cf80,blob);offset=sy['__hot_load__'][0]-0x0203cf80
  u.mem_write(sy['__hot_start__'][0],blob[offset:offset+sy['__hot_end__'][0]-sy['__hot_start__'][0]])
  vram=bytes(range(256))*384;u.mem_write(0x06000000,vram)
  u.mem_write(sy['enabled'][0],struct.pack('<I',1));u.mem_write(0x04000130,struct.pack('<H',1023));u.mem_write(0x04000006,struct.pack('<H',180))
  u.mem_write(0x030022cc,struct.pack('<I',0x080863a5));u.mem_write(0x04000134,struct.pack('<H',0x8030))
  receiver=GraphicsParser(Echo());state=dict(clock=0,bits=0,word=0,words=[])
  def write(m,access,address,size,value,user):
   if value&32 and value&1 and not state['clock']:
    state['word']=((state['word']<<1)|((value>>1)&1))&65535;state['bits']+=1
    if state['bits']==16:state['words'].append(state['word']);state['bits']=0
   state['clock']=value&1
  u.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000134,end=0x04000135)
  frames=[];mutated=False
  for tick in range(1,1000):
   if frames and not mutated:

    for row in range(4):u.mem_write(0x0600e008+row*64,b'\x77'*8)
    mutated=True
    address=sy['dirty_mask'][0]+(233>>5)*4
    mask=struct.unpack('<I',u.mem_read(address,4))[0];u.mem_write(address,struct.pack('<I',mask|(1<<(233&31))))
   u.mem_write(0x030022e0,struct.pack('<I',tick));u.reg_write(UC_ARM_REG_SP,0x0203fc00);u.reg_write(UC_ARM_REG_LR,0x03007000)
   u.emu_start(sy['tick'][0],0x03007000,count=5000000)
   self.assertLessEqual(len(state['words']),155)
   wire=struct.pack('<'+'H'*len(state['words']),*state['words']);state['words']=[]
   frames.extend(receiver.feed(wire))
   if len(frames)>=2:break
  self.assertEqual(len(frames),2);self.assertEqual(receiver.bad_frames,0)
  expected=bytearray(bytes(2304)+vram);
  for row in range(4):expected[2304+0xe008+row*64:2304+0xe010+row*64]=b'\x77'*8
  self.assertEqual(frames[1][1],expected)
  self.assertEqual(frames[1][4]['block_codecs'],{'9':1})
  self.assertLess(frames[1][2],180)
  print('Column delta bytes:',frames[1][2])

if __name__=='__main__':unittest.main()
