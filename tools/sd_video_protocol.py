"""Bounded decoder: publish only complete frames with valid pixel CRC32."""
import struct,zlib,binascii
MAGIC=struct.pack('<HH',0xb47e,0x5647)
def decode(h,payload,base=None):
 if h[3]==0:
  if len(payload)!=76800:raise ValueError('Raw size')
  pixels=payload
 else:
  words=struct.unpack('<'+'H'*(len(payload)//2),payload);out=[];i=0
  while i<len(words):
   token=words[i];i+=1;n=token&32767
   if not n or len(out)+n>38400:raise ValueError('RLE bounds')
   if token&32768:
    if i>=len(words):raise ValueError('Truncated run')
    out.extend([words[i]]*n);i+=1
   else:
    if i+n>len(words):raise ValueError('Truncated literals')
    out.extend(words[i:i+n]);i+=n
  if len(out)!=38400:raise ValueError('Incomplete frame')
  pixels=struct.pack('<38400H',*out)
 if h[3]==2:
  if base is None:raise ValueError('Missing delta reference')
  pixels=bytes(a^b for a,b in zip(pixels,base))
 if zlib.crc32(pixels)!=(h[8]|h[9]<<16):raise ValueError('Pixel CRC32')
 return pixels
def decode_blocks(payload,base,keyframe):
 out=bytearray(76800) if keyframe else bytearray(base or b'')
 if len(out)!=76800:raise ValueError('Missing block reference')
 w=struct.unpack('<'+'H'*(len(payload)//2),payload);i=0;seen=set()
 while i<len(w):
  if i+2>len(w):raise ValueError('Truncated block')
  block,info=w[i:i+2];i+=2;n=info&32767
  if block>=150 or block in seen or not n or i+n>len(w):raise ValueError('Block bounds')
  seen.add(block);data=w[i:i+n];i+=n
  if info&32768:
   pixels=[];j=0
   while j<n:
    token=data[j];j+=1;count=token&32767
    if not count or len(pixels)+count>256:raise ValueError('Run bounds')
    if token&32768:
     if j>=n:raise ValueError('Run missing color')
     pixels.extend([data[j]]*count);j+=1
    else:
     if j+count>n:raise ValueError('Literal missing pixels')
     pixels.extend(data[j:j+count]);j+=count
  else:pixels=data
  if len(pixels)!=256:raise ValueError('Block size')
  out[block*512:(block+1)*512]=struct.pack('<256H',*pixels)
 if keyframe and len(seen)!=150:raise ValueError('Incomplete keyframe')
 return bytes(out)
class Parser:
 def __init__(self):self.buffer=bytearray();self.bad_headers=0;self.bad_frames=0;self.discarded=0;self.previous=None;self.previous_seq=None;self.delta_misses=0
 def feed(self,data):
  self.buffer.extend(data);frames=[]
  while True:
   i=self.buffer.find(MAGIC)
   if i<0:
    n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
   if i:self.discarded+=i;del self.buffer[:i]
   if len(self.buffer)<24:break
   h=struct.unpack_from('<12H',self.buffer)
   if h[2] not in (0x400,0x401,0x402) or h[3] not in (0,1,2,3) or (h[3]==3)!=(h[2]==0x402) or (h[2]==0x400 and h[3]==2) or not (0<=h[6]<=38700 if h[2]==0x402 else 1<=h[6]<=38400) or h[7]!=38400 or h[11]!=0x5aa5:
    self.bad_headers+=1;del self.buffer[:1];continue
   header_bytes=48 if h[2]>=0x401 else 24
   if len(self.buffer)<header_bytes:break
   checksum_data=self.buffer[4:20]+(self.buffer[24:48] if header_bytes==48 else b'')
   if binascii.crc_hqx(checksum_data,65535)!=h[10]:
    self.bad_headers+=1;del self.buffer[:1];continue
   metadata={}
   if header_bytes==48:
    extra=struct.unpack_from('<12H',self.buffer,24)
    metadata=dict(version='0.4.2' if h[2]==0x402 else '0.4.1',keyframe=bool(extra[1]&4),scene=extra[0],raw_requested=bool(extra[1]&1),sender='baseline' if extra[1]&2 else 'fast')
    for j,name in enumerate(('render','copy','crc','encode','previous_tx')):metadata[name+'_ms']=(extra[2+j*2]|extra[3+j*2]<<16)*1000/65536
   length=header_bytes+h[6]*2
   if len(self.buffer)<length:break
   payload=bytes(self.buffer[header_bytes:length]);del self.buffer[:length]
   seq=h[4]|h[5]<<16
   if (h[3]==2 or (h[3]==3 and not metadata['keyframe'])) and (self.previous_seq is None or seq!=((self.previous_seq+1)&0xffffffff)):
    self.delta_misses+=1;self.previous=None;self.previous_seq=None;continue
   try:
    if h[3]==3:
     if zlib.crc32(payload)!=(h[8]|h[9]<<16):raise ValueError('Payload CRC32')
     pixels=decode_blocks(payload,self.previous,metadata['keyframe'])
    else:pixels=decode(h,payload,self.previous)
    self.previous=pixels;self.previous_seq=seq
    frames.append((seq,pixels,length,h[3],metadata))
   except ValueError:
    self.bad_frames+=1;self.previous=None;self.previous_seq=None
  return frames
