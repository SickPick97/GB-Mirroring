"""Transactional graphics cache: GBA 0x500 packets, no game ROM on receiver."""
import struct,zlib,binascii
MAGIC=struct.pack('<HH',0xb47e,0x5647)
SIZE=393*256
class GraphicsParser:
 def __init__(self,renderer):
  self.renderer=renderer;self.buffer=bytearray();self.bad_frames=0;self.bad_headers=0;self.discarded=0;self.delta_misses=0
  self.cache=None;self.pending=None;self.previous=None;self.sequence=None;self.seen=set();self.wire=0;self.key=False
 def feed(self,data):
  # PIO groups every 16 edges; game reinitialization can insert an extra edge.
  # Recover packet boundaries at any bit position, validating the header first.
  if not hasattr(self,'raw_tail'):
   self.raw_tail=b'';self.bits='';self.bit_resyncs=0;self.discarded_bits=0
  data=self.raw_tail+data;self.raw_tail=data[len(data)//2*2:]
  self.bits+=''.join(format(w,'016b') for w in struct.unpack('<'+'H'*(len(data)//2),data[:len(data)//2*2]))
  magic=format(0xb47e,'016b')+format(0x5647,'016b');out=[]
  while True:
   i=self.bits.find(magic)
   if i<0:
    n=max(0,len(self.bits)-31);self.discarded_bits+=n;self.bits=self.bits[n:];break
   if i:self.discarded_bits+=i;self.bit_resyncs+=1;self.bits=self.bits[i:]
   if len(self.bits)<192:break
   h=[int(self.bits[j:j+16],2) for j in range(0,192,16)]
   header=struct.pack('<12H',*h)
   if h[2] not in (0x500,0x501) or h[3]>2 or h[6]>128 or h[11]!=0x5aa5 or binascii.crc_hqx(header[4:20],65535)!=h[10]:
    self.bad_headers+=1;self.bits=self.bits[1:];self.discarded_bits+=1;continue
   n=192+h[6]*16
   if len(self.bits)<n:break
   body=struct.pack('<'+'H'*h[6],*(int(self.bits[j:j+16],2) for j in range(192,n,16)))
   self.bits=self.bits[n:];out.extend(self.feed_aligned(header+body))
  self.discarded=self.discarded_bits//8
  return out
 def fail(self):self.cache=None;self.pending=None;self.bad_frames+=1
 def feed_aligned(self,data):
  self.buffer.extend(data);frames=[]
  while True:
   i=self.buffer.find(MAGIC)
   if i<0:
    n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
   if i:self.discarded+=i;del self.buffer[:i]
   if len(self.buffer)<24:break
   h=struct.unpack_from('<12H',self.buffer)
   if h[2] not in (0x500,0x501) or h[3]>2 or h[6]>128 or h[11]!=0x5aa5 or binascii.crc_hqx(self.buffer[4:20],65535)!=h[10]:
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
    frames.append((seq,pixels,self.wire+n,4,dict(version='emerald-sliced-0.5.1' if h[2]==0x501 else 'emerald-experimental',game_frame=self.game_frame,changed_blocks=count,keyframe=self.key,raster_dma_active=bool(raster),scope='Static graphics snapshot; scanline effects not yet reproduced')))
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
