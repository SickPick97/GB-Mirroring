"""Local browser preview. No cartridge capture and no virtual webcam."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent));sys.dont_write_bytecode=True
import json,time,threading,subprocess,re,datetime,collections,webbrowser,struct,queue
from urllib.parse import urlsplit,parse_qs
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from sd_video_protocol import Parser
from win_serial import Serial
from link_protocol import bmp
from recovery_policy import RecoveryPolicy
from frame_hub import FrameHub,websocket
ROOT=Path(__file__).resolve().parents[1]
def main(emerald=False,unified=False,resume=False,log_path=None,baseline=False):
 folder=ROOT/('dist/emerald-reports' if emerald else 'dist/sd-video-reports')/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');folder.mkdir(parents=True)
 parser=Parser();lock=threading.Lock();stop=threading.Event();latest=[None];arrivals=collections.deque();presentations=collections.deque();changes=collections.deque()
 stats=dict(changed_images=0,resync_requests=0,status='WAITING',valid_frames=0,sequence_gaps=0,duplicates=0,bytes_received=0,codec=None,error=None,scope='Experimental Italian Emerald graphics. Scanline effects incomplete; no UVC.' if emerald else 'Homebrew VRAM over software SD/SC. No cartridge or UVC support.')
 raw_tail=bytearray();render_queue=queue.Queue(64);render_thread=None;hub=FrameHub()
 stats.update(presented_frames=0,render_drops=0,render_peak_ms=0,phases=[])
 def present(seq,pixels,game_frame=0):
  nonlocal last_pixels
  with lock:
   now=time.monotonic();presentations.append(now)
   if pixels!=last_pixels:stats['changed_images']+=1;last_pixels=pixels;changes.append(now)
   latest[0]=(seq,pixels);stats['presented_frames']+=1
  if emerald:hub.publish(seq,game_frame,pixels)
 def render_loop():
  try:
   while not stop.is_set() or not render_queue.empty():
    try:seq,gfx,game_frame,raster=render_queue.get(timeout=.1)
    except queue.Empty:continue
    began=time.monotonic();pixels=renderer.render(gfx,raster)
    with lock:stats['render_peak_ms']=max(stats['render_peak_ms'],round((time.monotonic()-began)*1000,2))
    present(seq,pixels,game_frame)
  except Exception as exc:
   with lock:stats['error']='Renderer: '+str(exc)
   stop.set()
 started=time.monotonic();previous=None;last_pixels=None;events=(folder/'frames.jsonl').open('w',encoding='utf-8');serial=None;server=None;worker=None;renderer=None
 def snapshot():
  with lock:
   now=time.monotonic()
   while arrivals and now-arrivals[0]>5:arrivals.popleft()
   for times in (presentations,changes):
    while times and now-times[0]>5:times.popleft()
   stats.update(stream_fps_last_5s=round(len(arrivals)/5,2),presented_fps_last_5s=round(len(presentations)/5,2),changed_fps_last_5s=round(len(changes)/5,2))
   # 0.13 bulk packets use sequence numbers without producing an image: real losses are the parser's delta misses
   if hasattr(parser,"bulk_packets"):stats["sequence_gaps"]=parser.delta_misses
   return dict(stats,held_ticks=len(getattr(parser,"held",()) or ()),usb_queue_peak_lag_ms=round(getattr(serial,"peak_lag_ms",0),2),unique_fps_last_5s=round(len(arrivals)/5,2),bit_resyncs=getattr(parser,"bit_resyncs",0),delta_reference_misses=parser.delta_misses,crc_errors=parser.bad_frames,repaired_payloads=getattr(parser,"repaired_payloads",0),repaired_headers=getattr(parser,"repaired_headers",0),payload_crc_errors=getattr(parser,"payload_crc_errors",0),transaction_errors=getattr(parser,"transaction_errors",0),last_validation_error=getattr(parser,"last_error",None),header_errors=parser.bad_headers,discarded_bytes=parser.discarded,elapsed_seconds=round(now-started,1))
 def make_bundle(notes=''):
  """One zip with every log of the session, written next to the reports and ready to send."""
  import log_summary,tempfile,os
  with lock:
   try:events.flush()
   except (ValueError,OSError):pass
   pixels=latest[0][1] if latest[0] else None;tail=bytes(raw_tail)
  bmp_bytes=None
  if pixels:
   try:
    fd,tmp=tempfile.mkstemp(suffix='.bmp',dir=folder);os.close(fd)
    bmp(tmp,struct.unpack('<38400H',pixels));bmp_bytes=Path(tmp).read_bytes();Path(tmp).unlink()
   except Exception:bmp_bytes=None
  data,summary=log_summary.bundle(folder,folder/'frames.jsonl',snapshot(),log_path,tail,bmp_bytes,resident='0.13.0',notes=notes)
  target=folder/('log-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip');target.write_bytes(data)
  return target,data,summary
 def reader():
  nonlocal previous,last_pixels
  try:
   ready=bytearray();deadline=time.monotonic()+10
   while b'READY SD VIDEO 0.4.0\n' not in ready:
    ready.extend(serial.read())
    if time.monotonic()>deadline:raise RuntimeError('Firmware non pronto: usa SD Video 0.4.0 e attendi PRONTO prima di A')
   print('PRONTO. Premi SELECT + L + R nel gioco.' if emerald else 'PRONTO. Premi e rilascia A sul GBA. Apri http://127.0.0.1:8765',flush=True)
   with lock:stats['status']='READY: SELECT + L + R' if emerald else 'READY: premi A sul GBA'
   last_data=time.monotonic();last_save=0;recovery=RecoveryPolicy()
   if unified:serial.write(b'CONTROL\n'+(b'RESYNC\n' if resume else b''))
   while not stop.is_set():
    data=serial.read();now=time.monotonic();received_valid=False
    if data:
     last_data=now
     if emerald:
      raw_tail.extend(data);del raw_tail[:-65536]
     if b'ERROR SD DMA OVERRUN' in data:raise RuntimeError('Pico DMA overrun: interrompi e conserva i risultati')
     with lock:stats['bytes_received']+=len(data)
     decoded=parser.feed(data)
     if emerald and not baseline and getattr(parser,'rom_image',None) is not None and not parser.rom_complete:
      with lock:stats['status']='COPIA CARTUCCIA %d%%'%(parser.rom_received*100//parser.ROM_CHUNKS)
     if emerald and not baseline and parser.rom_complete:
      import rom_cache
      saved=rom_cache.save(bytes(parser.rom_image))
      print('Cache ROM salvata:',saved,flush=True)
      print('Chiudi questo programma, riavvia il GBA e ripeti la procedura scegliendo START.',flush=True)
      with lock:stats['status']='CACHE ROM CREATA: riavvia il GBA e premi START'
      stop.set();break
     if emerald and not baseline and getattr(parser,'rom_missing',0):
      raise RuntimeError('Il GBA trasmette con la cache ROM ma questa e assente sul PC. Riavvia il GBA e al menu premi A per copiare la cartuccia.')
     for seq,pixels,wire_bytes,codec,metadata in decoded:
      with lock:
       if previous==seq:stats['duplicates']+=1;continue
       if previous is not None and seq!=((previous+1)&0xffffffff):stats['sequence_gaps']+=1
       received_valid=True
       stats['gba']=metadata
       previous=seq;stats['valid_frames']+=1;stats['status']='STREAMING';stats['codec']=('RAW','RLE16','DELTA-RLE16','BLOCKS','GRAPHICS')[codec];arrivals.append(now)
      if emerald:
       item=(seq,pixels,metadata.get('end_game_frame',metadata.get('game_frame',seq)),metadata.pop('raster',None))
       try:render_queue.put_nowait(item)
       except queue.Full:
        try:render_queue.get_nowait()
        except queue.Empty:pass
        render_queue.put_nowait(item)
        with lock:stats['render_drops']+=1
      else:present(seq,pixels)
      events.write(json.dumps(dict(seconds=round(now-started,4),sequence=seq,wire_bytes=wire_bytes,codec=codec,gba=metadata))+'\n');events.flush()
    faults=parser.bad_frames+parser.delta_misses+parser.bad_headers
    if unified and recovery.update(now,faults,received_valid and parser.cache is not None,getattr(parser,'pending',None) is not None):
     serial.write(b'RESYNC\n')
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
   if self.path=='/stream' and emerald:websocket(self,hub,stop);return
   if self.path=='/playout.js':body=(ROOT/'tools/playout.js').read_bytes();mime='text/javascript; charset=utf-8'
   elif self.path.split('?')[0]=='/':body=(ROOT/('tools/emerald_viewer.html' if emerald else 'tools/sd_video_viewer.html')).read_bytes();mime='text/html; charset=utf-8'
   elif self.path=='/stats':body=json.dumps(snapshot()).encode();mime='application/json'
   elif self.path.split('?')[0]=='/logs.zip':
    try:target,body,summary=make_bundle()
    except Exception as exc:self.send_error(500,str(exc)[:80]);return
    self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename="'+target.name+'"');self.send_header('X-Log-Path',target.name);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
   elif urlsplit(self.path).path=='/frame':
    with lock:frame=latest[0]
    if frame is None:self.send_response(204);self.end_headers();return
    if parse_qs(urlsplit(self.path).query).get('after')==[str(frame[0])]:
     self.send_response(204);self.send_header('Cache-Control','no-store');self.end_headers();return
    self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Cache-Control','no-store');self.send_header('X-Frame',str(frame[0]));self.send_header('Content-Length',str(len(frame[1])));self.end_headers();self.wfile.write(frame[1]);return
   else:self.send_error(404);return
   self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  def do_POST(self):
   if self.path not in ('/stop','/phase','/resync','/presentation'):self.send_error(404);return
   if self.headers.get('Origin') not in (None,'http://127.0.0.1:8765'):self.send_error(403);return
   if self.path=='/presentation':
    try:
     n=int(self.headers.get('Content-Length','0'))
     if not 0<n<=1024:raise ValueError('size')
     report=json.loads(self.rfile.read(n))
     allowed=('presented','dropped','resets','queued','fps','late_ms','hidden')
     if set(report)!=set(allowed) or any(type(v) not in (int,float,bool) or not 0<=v<=1e12 for v in report.values()):raise ValueError('telemetry')
    except (ValueError,TypeError):self.send_error(400);return
    with lock:stats['browser']=dict(report,received_seconds=round(time.monotonic()-started,3))
   elif self.path=='/phase':
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
   from native_renderer import Renderer
   from graphics_stream import GraphicsParser
   renderer=Renderer()
   class GraphicsSnapshot:
    def render(self,graphics):return bytes(graphics)
   if baseline:parser=GraphicsParser(GraphicsSnapshot())
   else:
    import rom_cache
    from stream_parser import StreamParser
    try:rom=rom_cache.load()
    except rom_cache.RomCacheError as exc:raise RuntimeError('Cache ROM non valida: %s. Cancella runtime/cache e ripeti la copia dalla cartuccia.'%exc)
    parser=StreamParser(GraphicsSnapshot(),rom=rom)
    # Every packet received, also the ticks later dropped while the page waited: what happens during a scene load.
    packets=(folder/'pacchetti.jsonl').open('w',encoding='utf-8',buffering=1)
    def packet_log(entry):
     entry['s']=round(time.monotonic()-started,3);packets.write(json.dumps(entry,separators=(',',':'))+chr(10))
    parser.packet_log=packet_log
    if rom is None:print('Cache ROM assente: al menu del GBA premi A (non START) per copiare la cartuccia, circa 3 minuti. Succede una sola volta.',flush=True)
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
  hub.close()
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
  if emerald:
   try:
    target,_,_=make_bundle('Generato alla chiusura della sessione');print('File log pronto da inviare:',target,flush=True)
   except Exception as exc:print('Log non creato:',exc,flush=True)
 return 1 if stats['error'] else 0
if __name__=='__main__':sys.exit(main('--emerald' in sys.argv))
