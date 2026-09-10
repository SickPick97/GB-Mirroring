"""Local browser preview. No cartridge capture and no virtual webcam."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.dont_write_bytecode=True
import json,time,threading,subprocess,re,datetime,collections,webbrowser,struct
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from sd_video_protocol import Parser
from win_serial import Serial
from link_protocol import bmp
ROOT=Path(__file__).resolve().parents[1]
def main():
 folder=ROOT/'dist/sd-video-reports'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True)
 parser=Parser();lock=threading.Lock();stop=threading.Event();latest=[None];arrivals=collections.deque()
 stats=dict(status='WAITING',valid_frames=0,sequence_gaps=0,duplicates=0,bytes_received=0,codec=None,error=None,scope='Homebrew VRAM over software SD/SC. No cartridge or UVC support.')
 started=time.monotonic();previous=None;events=(folder/'frames.jsonl').open('w',encoding='utf-8');serial=None;server=None;worker=None
 def snapshot():
  with lock:
   now=time.monotonic()
   while arrivals and now-arrivals[0]>5:arrivals.popleft()
   return dict(stats,unique_fps_last_5s=round(len(arrivals)/5,2),crc_errors=parser.bad_frames,header_errors=parser.bad_headers,discarded_bytes=parser.discarded,elapsed_seconds=round(now-started,1))
 def reader():
  nonlocal previous
  try:
   ready=bytearray();deadline=time.monotonic()+10
   while b'READY SD VIDEO 0.4.0\n' not in ready:
    ready.extend(serial.read())
    if time.monotonic()>deadline:raise RuntimeError('Firmware non pronto: usa SD Video 0.4.0 e attendi PRONTO prima di A')
   print('PRONTO. Premi e rilascia A sul GBA. Apri http://127.0.0.1:8765',flush=True)
   with lock:stats['status']='READY: premi A sul GBA'
   last_data=time.monotonic();last_save=0
   while not stop.is_set():
    data=serial.read();now=time.monotonic()
    if data:
     last_data=now
     if b'ERROR SD DMA OVERRUN' in data:raise RuntimeError('Pico DMA overrun: interrompi e conserva i risultati')
     with lock:stats['bytes_received']+=len(data)
     for seq,pixels,wire_bytes,codec in parser.feed(data):
      with lock:
       if previous==seq:stats['duplicates']+=1;continue
       if previous is not None and seq!=((previous+1)&0xffffffff):stats['sequence_gaps']+=1
       previous=seq;stats['valid_frames']+=1;stats['status']='STREAMING';stats['codec']='RLE16' if codec else 'RAW';latest[0]=(seq,pixels);arrivals.append(now)
      events.write(json.dumps(dict(seconds=round(now-started,4),sequence=seq,wire_bytes=wire_bytes,codec=codec))+'\n');events.flush()
    if now-last_data>30:
     with lock:stats['status']='Nessun dato da 30 s: controlla GBA e collegamento'
    if now-last_save>2:
     (folder/'rapporto.json').write_text(json.dumps(snapshot(),indent=2)+'\n',encoding='utf-8');last_save=now
  except Exception as exc:
   with lock:stats['error']=str(exc);stats['status']='ERROR'
   print('ERRORE:',exc,flush=True);stop.set()
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   if self.path=='/':body=(ROOT/'tools/sd_video_viewer.html').read_bytes();mime='text/html; charset=utf-8'
   elif self.path=='/stats':body=json.dumps(snapshot()).encode();mime='application/json'
   elif self.path=='/frame':
    with lock:frame=latest[0]
    if frame is None:self.send_response(204);self.end_headers();return
    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Cache-Control','no-store');self.send_header('X-Frame',str(frame[0]));self.send_header('Content-Length',str(len(frame[1])));self.end_headers();self.wfile.write(frame[1]);return
   else:self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def do_POST(self):
   if self.path!='/stop':self.send_error(404);return
   if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765'):self.send_error(403);return
   self.send_response(200);self.end_headers();stop.set()
 try:
  command="Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_CAFE&PID_4023' } | ForEach-Object { $_.FriendlyName }"
  result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
  ports=re.findall(r'\((COM\d+)\)',result.stdout)
  if len(ports)!=1:raise RuntimeError('Serve un solo Pico con SD Video 0.4.0. Nessun driver Zadig richiesto.')
  server=ThreadingHTTPServer(('127.0.0.1',8765),Handler);server.timeout=.2
  serial=Serial(ports[0]);time.sleep(.4);serial.write(b'START\n')
  worker=threading.Thread(target=reader,daemon=True);worker.start()
  print('Visualizzatore: http://127.0.0.1:8765 - risultati:',folder,flush=True)
  webbrowser.open('http://127.0.0.1:8765')
  while not stop.is_set():server.handle_request()
 except KeyboardInterrupt:stop.set()
 except Exception as exc:stats['error']=str(exc);stats['status']='ERROR';print('ERRORE:',exc)
 finally:
  stop.set()
  if worker:worker.join(3)
  if serial:
   try:serial.write(b'STOP\n')
   except Exception:pass
   serial.close()
  if server:server.server_close()
  events.close();r=snapshot();r['has_verified_frames']=r['valid_frames']>0
  (folder/'rapporto.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
  if latest[0]:bmp(folder/'ultimo-frame.bmp',struct.unpack('<38400H',latest[0][1]))
  print('Risultati salvati:',folder,flush=True)
 return 1 if stats['error'] else 0
if __name__=='__main__':sys.exit(main())
