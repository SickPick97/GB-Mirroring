"""CDC adapter for the existing multiboot state machine; no vendor edits."""
import queue,threading,time,struct,json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BootTransport:
 def __init__(self,serial):
  self.serial=serial;self.rx=queue.Queue();self.stop=threading.Event();self.worker=None;self.error=None
  self.restart()
 def restart(self):
  self.finish();self.serial.write(b'STOP\n');time.sleep(.03)
  while self.serial.read():pass
  self.serial.write(b'BOOT\n');buf=bytearray();until=time.monotonic()+5
  while b'READY BOOT 0.6.0\n' not in buf:
   buf.extend(self.serial.read())
   if time.monotonic()>until:raise RuntimeError('Pico unificato: nessuna risposta BOOT')
  self.rx=queue.Queue();self.error=None;self.stop.clear();self.worker=threading.Thread(target=self.reader,daemon=True);self.worker.start()
 def reader(self):
  pending=b''
  try:
   while not self.stop.is_set():
    pending+=self.serial.read();n=len(pending)//2*2
    for word in struct.unpack('<'+'H'*(n//2),pending[:n]):self.rx.put(word)
    pending=pending[n:]
  except Exception as exc:self.error=exc
 def send_words(self,words):
  words=list(words)
  for i in range(0,len(words),1024):
   chunk=words[i:i+1024];self.serial.write(('W%d\n'%len(chunk)).encode()+struct.pack('<'+'H'*len(chunk),*chunk))
 def read_word(self,timeout=3):
  if self.error:raise self.error
  try:return self.rx.get(timeout=timeout)
  except queue.Empty:return None
 def set_timing(self,value,*args):self.serial.write(('T%d\n'%value).encode())
 def drain_rx(self,seconds=.3):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   try:self.rx.get(timeout=.01)
   except queue.Empty:pass
 def finish(self):
  self.stop.set()
  if self.worker:self.worker.join(2)
  if self.worker and self.worker.is_alive():raise RuntimeError('Lettore multiboot non terminato')
  self.worker=None

def boot(serial,folder,baseline=False):
 version="0.6.0" if baseline else "0.7.1"
 sys.path.insert(0,str(ROOT/'vendor/celio_transport'));from mb_multi import Multiboot
 data=(ROOT/('dist/gbmirroring-emerald-v'+version+'.gba')).read_bytes()
 expected=json.loads((ROOT/('dist/verifica-emerald-v'+version+'.json')).read_text())['sha256']
 if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Loader non corrisponde al manifest')
 transport=BootTransport(serial)
 try:
  result=Multiboot(transport,timing_fast=3700,timing_wait=129630,max_attempts=3,detect_s=8).run(data)
  (folder/'multiboot.json').write_text(json.dumps(result,indent=2)+'\n')
 finally:transport.finish();serial.write(b'STOP\n')
 print('Multiboot completato. Sul GBA: inserisci Smeraldo e premi START. Non cambiare firmware Pico.',flush=True)
