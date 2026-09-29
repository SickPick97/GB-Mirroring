"""Run the real loader dump routine in an ARM emulator and rebuild the image with the PC receiver."""
import os,struct,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build/pylib'))
from stream_parser import StreamParser
CHUNKS=24
class Echo:
 def render(self,data):return bytes(data)
def rom_image():
 rom=Path(os.environ.get('GBM_ROM') or ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba')
 return rom.read_bytes() if rom.is_file() else None
def build_loader():
 env=dict(os.environ,GBM_BUILD_SUFFIX='-dumptest',GBM_DUMP_CHUNKS=str(CHUNKS))
 subprocess.run([sys.executable,str(ROOT/'tools/build_emerald_stream.py')],check=True,env=env,capture_output=True)
 return ROOT/'build/emerald-stream-dumptest/loader.bin'
def run_loader(binary,rom,keys=0xfffe,count=40000000):
 from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_READ
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for address,size in ((0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x05000000,0x1000),(0x06000000,0x20000),(0x07000000,0x1000),(0x08000000,0x1000000)):u.mem_map(address,size)
 u.mem_write(0x08000000,rom);u.mem_write(0x02000000,binary.read_bytes())
 bus=dict(clock=0,bits=0,word=0,words=[])
 def link(uc,access,address,size,value,user):
  if value&32 and value&1 and not bus['clock']:
   bus['word']=((bus['word']<<1)|((value>>1)&1))&65535;bus['bits']+=1
   if bus['bits']==16:bus['words'].append(bus['word']);bus['bits']=0
  bus['clock']=value&1
 u.hook_add(UC_HOOK_MEM_WRITE,link,begin=0x04000134,end=0x04000135)
 u.hook_add(UC_HOOK_MEM_READ,lambda uc,a,ad,s,v,us:uc.mem_write(0x04000130,struct.pack('<H',keys)),begin=0x04000130,end=0x04000131)
 u.mem_write(0x04000130,struct.pack('<H',keys))
 try:u.emu_start(0x02000000,0,count=count)
 except Exception:pass
 return bus['words']
@unittest.skipUnless(rom_image(),'local cartridge image required')
class Dump(unittest.TestCase):
 def test_loader_dump_matches_cartridge_bytes(self):
  rom=rom_image();words=run_loader(build_loader(),rom)
  parser=StreamParser(Echo());parser.ROM_CHUNKS=CHUNKS
  wire=struct.pack('<'+'H'*len(words),*words)
  for i in range(0,len(wire),4096):parser.feed(wire[i:i+4096])
  self.assertEqual(parser.rom_bad,0);self.assertEqual(parser.rom_received,CHUNKS);self.assertTrue(parser.rom_complete)
  self.assertEqual(bytes(parser.rom_image),rom[:CHUNKS*256]);self.assertEqual(parser.bad_frames,0);self.assertEqual(parser.bad_headers,0)
 def test_start_without_a_does_not_dump(self):
  rom=rom_image();words=run_loader(build_loader(),rom,keys=0xfff7,count=3000000)
  self.assertEqual(words,[])
if __name__=='__main__':unittest.main()
