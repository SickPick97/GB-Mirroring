"""Protocol fault tests and execution of the actual resident ARM sender."""
import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from graphics_stream import GraphicsParser,encode_snapshot,graphics_from_state,SIZE
class Echo:
 def render(self,data):return bytes(data)
class Tests(unittest.TestCase):
 def test_transactions_and_missing_block(self):
  a=bytes(SIZE);b=bytearray(a);b[700]=1
  p=GraphicsParser(Echo());self.assertEqual(p.feed(encode_snapshot(0,6,a))[0][1],a)
  self.assertEqual(p.feed(encode_snapshot(1,12,b,a))[0][1],b)
  data=encode_snapshot(2,18,a,b);self.assertEqual(p.feed(data[:30]+data[-32:]),[])
  self.assertEqual(p.feed(encode_snapshot(3,24,b,a)),[])
  self.assertEqual(p.feed(encode_snapshot(4,30,a))[0][1],a)
 def test_corruption(self):
  p=GraphicsParser(Echo());data=bytearray(encode_snapshot(0,6,bytes(SIZE)));data[100]^=1
  self.assertEqual(p.feed(data),[]);self.assertGreater(p.bad_frames,0)
 def test_actual_resident_gpio(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
  from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_CPSR
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)):uc.mem_map(address,size)
  # Synthetic graphics input keeps this test independent of a commercial ROM.
  for address,size in ((0x05000000,1024),(0x06000000,98304),(0x07000000,1024)):
   uc.mem_write(address,bytes((i*17+i//257)&255 for i in range(size)))
  uc.mem_write(0x03000818,bytes(96));payload=bytearray((ROOT/'build/emerald/resident.bin').read_bytes());struct.pack_into('<I',payload,4,0x03002750);uc.mem_write(0x0203cf80,bytes(payload))
  uc.mem_write(0x03002750,struct.pack('<I',0xe3a03301));uc.mem_write(0x030022e0,struct.pack('<I',6));uc.mem_write(0x04000130,struct.pack('<H',1023^0x304))
  state=dict(clock=0,bits=0,value=0,words=[]);parser=GraphicsParser(Echo());frames=[]
  def write(m,access,address,size,value,user):
   if value&1 and not state['clock']:
    state['value']=((state['value']<<1)|((value>>1)&1))&65535;state['bits']+=1
    if state['bits']==16:
     state['words'].append(state['value']);state['bits']=0;w=state['words']
     if len(w)>=12 and len(w)==12+w[6]:frames.extend(parser.feed(struct.pack('<'+'H'*len(w),*w)));state['words']=[]
   state['clock']=value&1
  def original(m,address,size,user):m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  uc.hook_add(UC_HOOK_CODE,original,begin=0x03002750,end=0x03002750)
  uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000134,end=0x04000135)
  for game_frame in (6,12):
   uc.mem_write(0x030022e0,struct.pack('<I',game_frame))
   if game_frame==12:uc.mem_write(0x04000130,struct.pack('<H',1023))
   uc.reg_write(UC_ARM_REG_CPSR,0xd2);uc.reg_write(UC_ARM_REG_SP,0x03007f00);uc.reg_write(UC_ARM_REG_LR,0x03007000)
   uc.emu_start(0x0203cf80,0x03007000,count=100000000)
  expected=bytes(256)+bytes(uc.mem_read(0x05000000,1024))+bytes(uc.mem_read(0x07000000,1024))+bytes(uc.mem_read(0x06000000,98304))
  self.assertEqual(struct.unpack('<H',uc.mem_read(0x04000134,2))[0],0x8030);self.assertEqual(len(frames),2);self.assertEqual(frames[0][1],expected);self.assertEqual(frames[1][1],expected);self.assertEqual(frames[1][4]['changed_blocks'],0)
if __name__=='__main__':unittest.main()
