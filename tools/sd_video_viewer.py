"""Local browser preview. No cartridge capture and no virtual webcam."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.dont_write_bytecode=True
import json,time,threading,subprocess,re,datetime,collections,webbrowser,struct,queue
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from sd_video_protocol import Parser
from win_serial import Serial
from link_protocol import bmp
ROOT=Path(__file__).resolve().parents[1]
def main(emerald=False,unified=False,resume=False,log_path=None,baseline=False):
 folder=ROOT/('dist/emerald-reports' if emerald else 'dist/sd-video-reports')/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True)
 parser=Parser();lock=threading.Lock();stop=threading.Event();latest=[None];arrivals=collections.deque()
 stats=dict(changed_images=0,resync_requests=0,status='WAITING',valid_frames=0,sequence_gaps=0,duplicates=0,bytes_received=0,codec=None,error=None,scope='Experimental Italian Emerald graphics. Scanline effects incomplete; no UVC.' if emerald else 'Homebrew VRAM over software SD/SC. No cartridge or UVC support.')
 raw_tail=bytearray();render_queue=queue.Queue(2);render_thread=None
 stats.update(presented_frames=0,render_drops=0,render_peak_ms=0,phases=[])
 def present(seq,pixels):
  nonlocal last_pixels
  with lock:
   if pixels!=last_pixels:stats['changed_images']+=1;last_pixels=pixels
   latest[0]=(seq,pixels);stats['presented_frames']+=1
 def render_loop():
  try:
   while not stop.is_set() or not render_queue.empty():
    try:seq,gfx=render_queue.get(timeout=.1)
    except queue.Empty:continue
    began=time.monotonic();pixels=renderer.render(gfx)
    with lock:stats['render_peak_ms']=max(stats['render_peak_ms'],round((time.monotonic()-began)*1000,2))
    present(seq,pixels)
  except Exception as exc:
   with lock:stats['error']='Renderer: '+str(exc)
   stop.set()
 started=time.monotonic();previous=None;last_pixels=None;events=(folder/'frames.jsonl').open('w',encoding='utf-8');serial=None;server=None;worker=None;renderer=None
 def snapshot():
  with lock:
   now=time.monotonic()
   while arrivals and now-arrivals[0]>5:arrivals.popleft()
   return dict(stats,usb_queue_peak_lag_ms=round(getattr(serial,"peak_lag_ms",0),2),unique_fps_last_5s=round(len(arrivals)/5,2),bit_resyncs=getattr(parser,"bit_resyncs",0),delta_reference_misses=parser.delta_misses,crc_errors=parser.bad_frames,payload_crc_errors=getattr(parser,"payload_crc_errors",0),transaction_errors=getattr(parser,"transaction_errors",0),last_validation_error=getattr(parser,"last_error",None),header_errors=parser.bad_headers,discarded_bytes=parser.discarded,elapsed_seconds=round(now-started,1))
 def reader():
  nonlocal previous,last_pixels
  try:
   ready=bytearray();deadline=time.monotonic()+10
   while b'READY SD VIDEO 0.4.0\n' not in ready:
    ready.extend(serial.read())
    if time.monotonic()>deadline:raise RuntimeError('Firmware non pronto: usa SD Video 0.4.0 e attendi PRONTO prima di A')
   print('PRONTO. Premi SELECT + L + R nel gioco.' if emerald else 'PRONTO. Premi e rilascia A sul GBA. Apri http://127.0.0.1:8765',flush=True)
   with lock:stats['status']='READY: SELECT + L + R' if emerald else 'READY: premi A sul GBA'
   last_data=time.monotonic();last_save=0;last_recovery=0;last_faults=0;last_good=last_data
   if unified:serial.write(b'CONTROL\n'+(b'RESYNC\n' if resume else b''))
   while not stop.is_set():
    data=serial.read();now=time.monotonic()
    if data:
     last_data=now
     if emerald:
      raw_tail.extend(data);del raw_tail[:-65536]
     if b'ERROR SD DMA OVERRUN' in data:raise RuntimeError('Pico DMA overrun: interrompi e conserva i risultati')
     with lock:stats['bytes_received']+=len(data)
     for seq,pixels,wire_bytes,codec,metadata in parser.feed(data):
      with lock:
       if previous==seq:stats['duplicates']+=1;continue
       if previous is not None and seq!=((previous+1)&0xffffffff):stats['sequence_gaps']+=1
       last_good=now
       stats['gba']=metadata
       previous=seq;stats['valid_frames']+=1;stats['status']='STREAMING';stats['codec']=('RAW','RLE16','DELTA-RLE16','BLOCKS','GRAPHICS')[codec];arrivals.append(now)
      if emerald:
       try:render_queue.put_nowait((seq,pixels))
       except queue.Full:
        try:render_queue.get_nowait()
        except queue.Empty:pass
        render_queue.put_nowait((seq,pixels))
        with lock:stats['render_drops']+=1
      else:present(seq,pixels)
      events.write(json.dumps(dict(seconds=round(now-started,4),sequence=seq,wire_bytes=wire_bytes,codec=codec,gba=metadata))+'\n');events.flush()
    faults=parser.bad_frames+parser.delta_misses+parser.bad_headers
    if unified and ((faults>last_faults) or (now-last_good>5 and data)) and now-last_recovery>4:
     serial.write(b'RESYNC\n');last_recovery=now;last_faults=faults
     with lock:stats['resync_requests']+=1
     (folder/('errore-'+str(stats['resync_requests']%4)+'.bin')).write_bytes(raw_tail)
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
   if self.path.split('?')[0]=='/':body=(ROOT/('tools/emerald_viewer.html' if emerald else 'tools/sd_video_viewer.html')).read_bytes();mime='text/html; charset=utf-8'
   elif self.path=='/stats':body=json.dumps(snapshot()).encode();mime='application/json'
   elif self.path=='/frame':
    with lock:frame=latest[0]
    if frame is None:self.send_response(204);self.end_headers();return
    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Cache-Control','no-store');self.send_header('X-Frame',str(frame[0]));self.send_header('Content-Length',str(len(frame[1])));self.end_headers();self.wfile.write(frame[1]);return
   else:self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def do_POST(self):
   if self.path not in ('/stop','/phase','/resync'):self.send_error(404);return
   if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765'):self.send_error(403);return
   if self.path=='/phase':
    try:n=int(self.headers.get('Content-Length','0'))
    except ValueError:self.send_error(400);return
    if not 0<n<=128:self.send_error(400);return
    phase=self.rfile.read(n).decode('utf-8',errors='replace')
    if phase not in ('statico','cammino','menu','centro','battaglia','ripresa'):self.send_error(400);return
    with lock:stats['phases'].append(dict(phase=phase,seconds=round(time.monotonic()-started,3),valid_frames=stats['valid_frames']))
   elif self.path=='/resync':
    if unified and serial:serial.write(b'RESYNC\n')
   else:stop.set()
   self.send_response(200);self.end_headers()
 try:
  if emerald:
   from graphics_renderer import Renderer
   from graphics_stream import GraphicsParser
   renderer=Renderer()
   class GraphicsSnapshot:
    def render(self,graphics):return bytes(graphics)
   parser=GraphicsParser(GraphicsSnapshot())
  command="Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match 'VID_CAFE&PID_4023' } | ForEach-Object { $_.FriendlyName }"
  if unified:command=command.replace('PID_4023','PID_4024')
  result=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,check=True)
  ports=re.findall(r'\((COM\d+)\)',result.stdout)
  if len(ports)!=1:raise RuntimeError('Serve un solo Pico con firmware UNIFIED 0.7.0. Nessun driver Zadig richiesto.' if unified else 'Serve un solo Pico con SD Video 0.4.0. Nessun driver Zadig richiesto.')
  server=ThreadingHTTPServer(('127.0.0.1',8765),Handler);server.timeout=.2
  serial=Serial(ports[0],read_timeout=5) if unified else Serial(ports[0]);time.sleep(.4)
  if unified and not resume:
   from unified_boot import boot
   boot(serial,folder,baseline=baseline)
  serial.write(b'START\n')
  if unified:
   from buffered_serial import BufferedSerial
   serial=BufferedSerial(serial)
  if emerald:render_thread=threading.Thread(target=render_loop,daemon=True);render_thread.start()
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
  if render_thread:render_thread.join(3)
  if render_thread and render_thread.is_alive():stats['error']='Renderer non terminato'
  elif renderer:renderer.close()
  events.close();r=snapshot();r['has_verified_frames']=r['valid_frames']>0
  r['stopped_cleanly']=not r['error'] and (worker is None or not worker.is_alive())
  if r['stopped_cleanly']:r['status']='STOPPED'
  (folder/'rapporto.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
  if emerald and raw_tail:(folder/'usb-tail.bin').write_bytes(raw_tail)
  if latest[0]:bmp(folder/'ultimo-frame.bmp',struct.unpack('<38400H',latest[0][1]))
  print('Risultati salvati:',folder,flush=True)
  if log_path:(folder/'console.txt').write_bytes(Path(log_path).read_bytes())
 return 1 if stats['error'] else 0
if __name__=='__main__':sys.exit(main('--emerald' in sys.argv))
