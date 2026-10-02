"""CDC multiboot integration using the existing independent BIOS model."""
import sys,struct,threading,time,unittest,collections,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'vendor/celio_transport'))
from mb_multi import SlaveSimulato,Multiboot,prepara_rom
from unified_boot import BootTransport
class SerialModel:
 def __init__(self,rom):self.rom=rom;self.lock=threading.Lock();self.pending=bytearray();self.output=bytearray();self.words=collections.deque();self.need=0;self.timings=[];self.boots=0;self.slave=None
 def write(self,data):
  with self.lock:
   self.pending.extend(data)
   while True:
    if self.need:
     if len(self.pending)<self.need:return
     self.words.extend(struct.unpack('<'+'H'*(self.need//2),self.pending[:self.need]));del self.pending[:self.need];self.need=0
    else:
     if b'\n' not in self.pending:return
     line,_,rest=self.pending.partition(b'\n');self.pending=bytearray(rest)
     if line==b'STOP':self.words.clear();self.output.clear()
     elif line==b'BOOT':self.slave=SlaveSimulato(self.rom);self.boots+=1;self.output.extend(b'READY BOOT 0.6.0\n')
     elif line.startswith(b'T'):self.timings.append(int(line[1:]))
     elif line.startswith(b'W'):self.need=int(line[1:])*2
 def read(self):
  time.sleep(.001)
  with self.lock:
   if self.output:
    b=bytes(self.output[:7]);del self.output[:7];return b
   if self.words:return struct.pack('<H',self.slave.exchange(self.words.popleft()))
   return b''
class Tests(unittest.TestCase):
 def test_multiboot_over_cdc(self):
  for version in ('0.13.2','0.13.1','0.13.0','0.12.3','0.12.2','0.12.1','0.12.0','0.11.0'):
   rom=prepara_rom((ROOT/('dist/gbmirroring-emerald-v'+version+'.gba')).read_bytes());serial=SerialModel(rom);link=BootTransport(serial)
   try:
    result=Multiboot(link,timing_fast=3700,timing_wait=129630,max_attempts=1,verbose=False).run(rom)
    self.assertEqual(serial.slave.verifica(),[],version);self.assertEqual(result['desync'],0);self.assertIn(129630,serial.timings);self.assertIn(3700,serial.timings)
   finally:link.finish()
   self.assertIsNone(link.worker)
 def test_pio_program_matches_tested_master(self):
  old=(ROOT/'firmware/multi-profile/main.c').read_text();new=(ROOT/'firmware/unified/pico.c').read_text()
  extract=lambda s,name:re.search(name+r'\[\]=\{([^}]+)',s).group(1)
  self.assertEqual(extract(old,'code'),extract(new,'boot_code'))
if __name__=='__main__':unittest.main()
