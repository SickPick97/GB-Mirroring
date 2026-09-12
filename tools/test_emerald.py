"""Protocol fault tests and execution of the actual resident ARM sender."""
import sys,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from graphics_stream import packet,GraphicsParser,encode_snapshot,graphics_from_state,SIZE
class Echo:
 def render(self,data):return bytes(data)
class Tests(unittest.TestCase):
 def test_observer_marks_pending_ranges_and_ignores_non_video(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
  from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR
  from verify_firmware import elf_symbols
  sym=elf_symbols((ROOT/'build/emerald/resident.elf').read_bytes())
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000)):uc.mem_map(address,size)
  uc.mem_write(0x0203cf80,(ROOT/'build/emerald/resident.bin').read_bytes())
  uc.mem_write(sym['enabled'][0],struct.pack('<I',1))
  uc.mem_write(0x04000200,struct.pack('<HH',1,1))
  # Two DMA requests: only the VRAM destination should mark blocks.
  uc.mem_write(0x03000010,struct.pack('<IIHHI',0x02000000,0x060001f0,32,1,0))
  uc.mem_write(0x03000020,struct.pack('<IIHHI',0x02000000,0x02002000,256,1,0))
  uc.mem_write(0x02021834,b'\x01\x01')
  uc.mem_write(0x02021838,struct.pack('<IIHH',0x08000000,0x06010000,64,0))
  uc.reg_write(UC_ARM_REG_SP,0x0203fc00);uc.reg_write(UC_ARM_REG_LR,0x03007000)
  uc.emu_start(sym['observe'][0],0x03007000,count=100000)
  words=struct.unpack('<13I',uc.mem_read(sym['dirty_mask'][0],52))
  marked={i for i in range(393) if words[i>>5]&(1<<(i&31))}
  self.assertEqual(marked,{10,11,265})
  self.assertEqual(struct.unpack('<I',uc.mem_read(0x03000014,4))[0],0x060001f0)
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
 def test_bit_alignment_recovers(self):
  a=bytes(SIZE);b=bytearray(a);b[900]=77
  first=encode_snapshot(0,6,a);second=encode_snapshot(1,12,b,a)
  def bits(data):return ''.join(format(w,'016b') for w in struct.unpack('<'+'H'*(len(data)//2),data))
  for offset in range(1,16):
   stream=bits(first)+'1'*offset+bits(second)+'0'*16
   wire=struct.pack('<'+'H'*(len(stream)//16),*(int(stream[i:i+16],2) for i in range(0,len(stream)-15,16)))
   p=GraphicsParser(Echo());result=[]
   for i in range(0,len(wire),113):result.extend(p.feed(wire[i:i+113]))
   self.assertEqual(len(result),2);self.assertEqual(result[-1][1],b);self.assertGreater(p.discarded_bits,0)
 def test_cached_packet_validation(self):
  def p(seq,kind,block,body):return packet(seq,kind,block,body,version=0x600)
  def begin(seq,key):return p(seq,0,0,struct.pack('<3H',key,6,0))
  def end(seq,count):return p(seq,2,0,struct.pack('<12H',6,0,count,0,12,0,6,100,0,10,1,6))
  key=begin(0,1)+p(0,4,0,struct.pack('<2H',128,0))+b''.join(p(0,3,i,bytes(2)) for i in range(1,393))+end(0,393)
  parser=GraphicsParser(Echo());self.assertEqual(parser.feed(key)[0][1],bytes(SIZE))
  delta=begin(1,0)+p(1,5,0,struct.pack('<9H',1,0,0,0,0,0,0,0,123))+end(1,1)
  self.assertEqual(parser.feed(delta)[0][1][:2],struct.pack('<H',123))
  self.assertEqual(parser.feed(begin(2,0)+p(2,3,0,struct.pack('<H',63))+end(2,1)),[])
  self.assertGreater(parser.bad_frames,0)
  malformed=begin(3,1)+p(3,4,0,struct.pack('<4H',128,0,0,1))
  self.assertEqual(parser.feed(malformed),[]);self.assertIsNone(parser.cache)
  self.assertEqual(len(parser.feed(key)),1)
 def test_actual_resident_gpio(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_CODE,UC_HOOK_MEM_READ
  from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_CPSR
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)):uc.mem_map(address,size)
  # Synthetic graphics input keeps this test independent of a commercial ROM.
  for address,size in ((0x05000000,1024),(0x06000000,98304),(0x07000000,1024)):
   uc.mem_write(address,bytes((i*17+i//257)&255 for i in range(size)))
  uc.mem_write(0x03000818,bytes(96));payload=bytearray((ROOT/'build/emerald/resident.bin').read_bytes());struct.pack_into('<I',payload,4,0x03002750);uc.mem_write(0x0203cf80,bytes(payload))
  uc.mem_write(0x03002750,struct.pack('<I',0xe3a03301));uc.mem_write(0x030022e0,struct.pack('<I',6));uc.mem_write(0x04000130,struct.pack('<H',1023^0x304))
  state=dict(clock=0,bits=0,value=0,words=[],poll_reads=0,nack=False);parser=GraphicsParser(Echo());frames=[]
  def write(m,access,address,size,value,user):
   if value&32 and value&1 and not state['clock']:
    state['value']=((state['value']<<1)|((value>>1)&1))&65535;state['bits']+=1
    if state['bits']==16:
     state['total']=state.get('total',0)+1;state['bits']=0
     if state['words'] or state['value']:state['words'].append(state['value'])
     w=state['words']
     if len(w)>=12 and len(w)==12+w[6]:frames.extend(parser.feed(struct.pack('<'+'H'*len(w),*w)));state['words']=[]
   state['clock']=value&1
  def read(m,access,address,size,value,user):
   current=struct.unpack('<H',m.mem_read(address,2))[0]
   if current&0x30==0x10:
    state['poll_reads']+=1
    nack=len(frames)==4 and state['poll_reads']%2==0 and not state['nack']
    if nack:state['nack']=True
    m.mem_write(address,struct.pack('<H',(current&~2)|(2 if nack else 0)))
  uc.hook_add(UC_HOOK_MEM_READ,read,begin=0x04000134,end=0x04000135)
  def original(m,address,size,user):m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  uc.hook_add(UC_HOOK_CODE,original,begin=0x03002750,end=0x03002750)
  uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000134,end=0x04000135)
  max_words=0;mutated=False;restored=False
  original_oam=bytes(uc.mem_read(0x07000000,1024))
  for game_frame in range(6,1200):
   if len(frames)==2 and not mutated:
    uc.mem_write(0x07000000,b"\x43\x21");mutated=True
   if len(frames)==3 and not restored:
    uc.mem_write(0x07000000,original_oam);restored=True
   before_words=state.get("total",0)
   uc.mem_write(0x030022e0,struct.pack('<I',game_frame))
   uc.mem_write(0x04000006,struct.pack('<H',224 if game_frame==6 else 160))
   if game_frame>6:uc.mem_write(0x04000134,struct.pack('<H',0x803c))
   if game_frame==7:uc.mem_write(0x04000130,struct.pack('<H',1023))
   uc.reg_write(UC_ARM_REG_CPSR,0xd2);uc.reg_write(UC_ARM_REG_SP,0x03007f00);uc.reg_write(UC_ARM_REG_LR,0x03007000)
   uc.emu_start(0x0203cf80,0x03007000,count=100000000)
   if game_frame==6:self.assertEqual(state.get("total",0),0)
   max_words=max(max_words,state.get("total",0)-before_words)
   if len(frames)==5:break
  self.assertTrue(state['nack'],str((state['poll_reads'],len(frames))));self.assertTrue(frames[4][4]['keyframe'],str([x[4]['keyframe'] for x in frames]))
  self.assertLessEqual(max_words,155)
  expected=bytes(256)+bytes(uc.mem_read(0x05000000,1024))+bytes(uc.mem_read(0x07000000,1024))+bytes(uc.mem_read(0x06000000,98304))
  self.assertEqual(struct.unpack('<H',uc.mem_read(0x04000134,2))[0],0x8030);self.assertEqual(len(frames),5);self.assertEqual(frames[0][1],expected);self.assertEqual(frames[1][1],expected);self.assertEqual(frames[1][4]['changed_blocks'],0);self.assertEqual(frames[3][1],expected);self.assertEqual(frames[2][1][5*256:5*256+2],b'\x43\x21')
if __name__=='__main__':unittest.main()
