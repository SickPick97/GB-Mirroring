"""Transactional graphics cache: GBA 0x500 packets, no game ROM on receiver."""
import struct,zlib,binascii
MAGIC=struct.pack('<HH',0xb47e,0x5647)
SIZE=393*256
class GraphicsParser:
 def __init__(self,renderer):
  self.renderer=renderer;self.buffer=bytearray();self.bad_frames=0;self.bad_headers=0;self.discarded=0;self.delta_misses=0
  self.cache=None;self.pending=None;self.previous=None;self.sequence=None;self.seen=set();self.wire=0;self.key=False
 def fail(self):self.cache=None;self.pending=None;self.bad_frames+=1
 def feed(self,data):
  self.buffer.extend(data);frames=[]
  while True:
   i=self.buffer.find(MAGIC)
   if i<0:
    n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
   if i:self.discarded+=i;del self.buffer[:i]
   if len(self.buffer)<24:break
   h=struct.unpack_from('<12H',self.buffer)
   if h[2]!=0x500 or h[3]>2 or h[6]>128 or h[11]!=0x5aa5 or binascii.crc_hqx(self.buffer[4:20],65535)!=h[10]:
    self.bad_headers+=1;self.cache=None;self.pending=None;del self.buffer[:1];continue
   n=24+h[6]*2
   if len(self.buffer)<n:break
   body=bytes(self.buffer[24:n]);del self.buffer[:n]
   if zlib.crc32(body)!=(h[8]|h[9]<<16):self.fail();continue
   seq=h[4]|h[5]<<16
   if h[3]==0:
    if len(body)!=6:self.fail();continue
    key,lo,hi=struct.unpack('<3H',body)
    if key not in (0,1):self.fail();continue
    self.sequence=seq;self.seen=set();self.wire=n;self.key=bool(key)
    if not key and (self.cache is None or seq!=((self.previous+1)&0xffffffff)):
     self.delta_misses+=1;self.pending=None;self.cache=None;continue
    self.pending=bytearray(SIZE) if key else bytearray(self.cache);self.game_frame=lo|hi<<16
   elif seq!=self.sequence or self.pending is None:continue
   elif h[3]==1:
    block=h[7]
    if len(body)!=256 or block>=393 or block in self.seen:self.fail();continue
    self.seen.add(block);self.wire+=n;self.pending[block*256:(block+1)*256]=body
   else:
    if len(body)!=8:self.fail();continue
    lo,hi,count,raster=struct.unpack('<4H',body)
    if count!=len(self.seen) or (self.key and count!=393) or (lo|hi<<16)!=self.game_frame:self.fail();continue
    self.cache=self.pending;self.pending=None;self.previous=seq
    pixels=self.renderer.render(self.cache)
    frames.append((seq,pixels,self.wire+n,4,dict(version='emerald-experimental',game_frame=self.game_frame,changed_blocks=count,keyframe=self.key,raster_dma_active=bool(raster),scope='Static graphics snapshot; scanline effects not yet reproduced')))
  return frames

def graphics_from_state(s):
 if len(s)<0x61000 or s[0x1c:0x20]!=b'BPEI':raise ValueError('Italian Emerald state required')
 return bytes(s[0x19818:0x19878])+bytes(160)+bytes(s[0x800:0x19000])

def packet(seq,kind,block,body):
 crc=zlib.crc32(body);h=[0xb47e,0x5647,0x500,kind,seq&65535,seq>>16,len(body)//2,block,crc&65535,crc>>16,0,0x5aa5]
 h[10]=binascii.crc_hqx(struct.pack('<8H',*h[2:10]),65535)
 return struct.pack('<12H',*h)+body

def encode_snapshot(seq,game_frame,current,previous=None):
 if len(current)!=SIZE:raise ValueError('Graphics size')
 parts=[packet(seq,0,0,struct.pack('<3H',previous is None,game_frame&65535,game_frame>>16))];count=0
 for block in range(393):
  data=current[block*256:(block+1)*256]
  if previous is None or data!=previous[block*256:(block+1)*256]:parts.append(packet(seq,1,block,data));count+=1
 parts.append(packet(seq,2,0,struct.pack('<4H',game_frame&65535,game_frame>>16,count,0)))
 return b''.join(parts)
