"""Bounded publisher for browser presentation; slow consumers never block USB."""
import collections,threading,struct,hashlib,base64,select
class FrameHub:
 def __init__(self,capacity=32):
  if capacity<1:raise ValueError('Frame capacity must be positive')
  self.frames=collections.deque(maxlen=capacity);self.condition=threading.Condition();self.closed=False;self.serial=0
 def publish(self,sequence,game_frame,pixels):
  with self.condition:
   if self.closed:return
   self.serial+=1;self.frames.append((self.serial,struct.pack('<II',sequence,game_frame)+pixels));self.condition.notify_all()
 def next(self,after,timeout=1):
  with self.condition:
   self.condition.wait_for(lambda:self.closed or (self.frames and self.frames[-1][0]>after),timeout)
   if self.closed:return None
   if not self.frames:return None
   if after==0:return self.frames[-1]
   return next((f for f in self.frames if f[0]>after),None)
 def close(self):
  with self.condition:self.closed=True;self.condition.notify_all()
def websocket(handler,hub,stop):
 if handler.headers.get('Origin') not in (None,'http://127.0.0.1:8765'):
  handler.send_error(403);return
 key=handler.headers.get('Sec-WebSocket-Key','')
 try:valid=len(base64.b64decode(key,validate=True))==16
 except Exception:valid=False
 if (not valid or handler.headers.get('Sec-WebSocket-Version')!='13'
     or handler.headers.get('Upgrade','').lower()!='websocket'
     or 'upgrade' not in [s.strip().lower() for s in handler.headers.get('Connection','').split(',')]):
  handler.send_error(400);return
 accept=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
 handler.send_response(101);handler.send_header('Upgrade','websocket');handler.send_header('Connection','Upgrade');handler.send_header('Sec-WebSocket-Accept',accept);handler.end_headers();handler.wfile.flush()
 handler.connection.settimeout(.5);cursor=0;handler.close_connection=True;incoming=bytearray()
 def send(opcode,data):
  size=len(data)
  header=bytes([0x80|opcode])+(bytes([size]) if size<126 else b'\x7e'+struct.pack('>H',size) if size<65536 else b'\x7f'+struct.pack('>Q',size))
  handler.connection.sendall(header+data)
 try:
  while not stop.is_set():
   if select.select([handler.connection],[],[],0)[0]:
    chunk=handler.connection.recv(1024)
    if not chunk:return
    incoming.extend(chunk)
   while len(incoming)>=2:
    first,second=incoming[:2];size=second&127;opcode=first&15
    # This endpoint only accepts masked, unfragmented control frames.
    # Telemetry is sent through the separately bounded HTTP endpoint.
    if first&0xf0!=0x80 or not second&0x80 or opcode not in (8,9,10) or size>125:
     send(8,struct.pack('>H',1002));return
    if len(incoming)<6+size:break
    mask=incoming[2:6];data=bytes(v^mask[i%4] for i,v in enumerate(incoming[6:6+size]));del incoming[:6+size]
    if opcode==8:
     if size==1:send(8,struct.pack('>H',1002))
     else:send(8,data)
     return
    if opcode==9:send(10,data)
   frame=hub.next(cursor,.05)
   if hub.closed:return
   if frame:
    cursor,data=frame
    send(2,data)
  send(8,struct.pack('>H',1001))
 except (OSError,TimeoutError):pass
