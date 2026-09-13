"""mGBA scene -> actual ARM GPIO sender -> PC cache, without physical USB.

Each scene is held stable until its transaction finishes. This verifies bytes
and codec references; it deliberately does not measure transport timing.
"""
import argparse,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR
from verify_firmware import elf_symbols
from mgba_headless import Core
from graphics_stream import GraphicsParser,graphics_from_state

class Echo:
 def render(self,data):return bytes(data)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,default=ROOT/'build/sootopolis/field.state');ap.add_argument('--frames',type=int,default=120);args=ap.parse_args()
 folder=ROOT/'build/emerald-columns';sy=elf_symbols((folder/'resident.elf').read_bytes());blob=(folder/'resident.bin').read_bytes()
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000)):u.mem_map(address,size)
 u.mem_write(0x0203cf80,blob);offset=sy['__hot_load__'][0]-0x0203cf80
 u.mem_write(sy['__hot_start__'][0],blob[offset:offset+sy['__hot_end__'][0]-sy['__hot_start__'][0]])
 def word(address,value):u.mem_write(address,struct.pack('<I',value))
 word(sy['enabled'][0],1);u.mem_write(0x04000130,struct.pack('<H',1023));u.mem_write(0x04000006,struct.pack('<H',180))
 word(0x030022cc,0x080863a5);u.mem_write(0x04000134,struct.pack('<H',0x8030))
 parser=GraphicsParser(Echo());bus=dict(clock=0,bits=0,word=0,words=[])
 def write(m,access,address,size,value,user):
  if value&32 and value&1 and not bus['clock']:
   bus['word']=((bus['word']<<1)|((value>>1)&1))&65535;bus['bits']+=1
   if bus['bits']==16:bus['words'].append(bus['word']);bus['bits']=0
  bus['clock']=value&1
 u.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000134,end=0x04000135)
 rom=(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
 core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom);records=[];tick=0
 try:
  core.run();core.restore(args.state.read_bytes())
  for frame in range(args.frames):
   # Horizontal and vertical motion followed by a menu open/close.
   keys=(1<<(7 if frame%16<8 else 6)) if frame<60 else (1<<(5 if frame%16<8 else 4)) if frame<90 else 1<<3 if frame==92 else 1 if frame==108 else 0
   core.run(6,keys);gfx=graphics_from_state(core.state())
   u.mem_write(0x03000818,gfx[:96]);u.mem_write(0x05000000,gfx[256:1280]);u.mem_write(0x07000000,gfx[1280:2304]);u.mem_write(0x06000000,gfx[2304:])
   u.mem_write(sy['dirty_mask'][0],b'\xff'*52)
   completed=[]
   for _ in range(600):
    tick+=1;word(0x030022e0,tick);u.reg_write(UC_ARM_REG_SP,0x0203fc00);u.reg_write(UC_ARM_REG_LR,0x03007000)
    u.emu_start(sy['tick'][0],0x03007000,count=5000000)
    assert len(bus['words'])<=155
    wire=struct.pack('<'+'H'*len(bus['words']),*bus['words']);bus['words']=[]
    completed.extend(parser.feed(wire))
    if parser.bad_frames:
     block,mask,decoded,expected,actual=parser.column_failure
     target=gfx[block*256:(block+1)*256]
     print('column failure',frame,block,mask,expected,actual,'target hash',__import__('graphics_stream').block_hash(target),'diff',[(i,a,b) for i,(a,b) in enumerate(zip(decoded,target)) if a!=b])
    assert parser.bad_frames==0,(frame,parser.last_error)
    if completed:break
   assert len(completed)==1,frame
   assert completed[0][1]==gfx,('cache mismatch',frame)
   records.append(dict(frame=frame,wire_bytes=completed[0][2],regions=completed[0][4]['resource_regions'],codecs=completed[0][4]['block_codecs']))
 finally:core.close()
 result=dict(scope='Frozen mGBA scenes sent by real ARM instructions in Unicorn; byte equality, not timing or physical validation',frames=len(records),exact_frames=len(records),records=records)
 (args.state.parent/'columns-replay.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='records'}))

if __name__=='__main__':main()
