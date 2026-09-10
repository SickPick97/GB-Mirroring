"""Bounded decoder: publish only complete frames with valid pixel CRC32."""
import struct,zlib,binascii
MAGIC=struct.pack('<HH',0xb47e,0x5647)
def decode(h,payload):
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
 if zlib.crc32(pixels)!=(h[8]|h[9]<<16):raise ValueError('Pixel CRC32')
 return pixels
class Parser:
 def __init__(self):self.buffer=bytearray();self.bad_headers=0;self.bad_frames=0;self.discarded=0
 def feed(self,data):
  self.buffer.extend(data);frames=[]
  while True:
   i=self.buffer.find(MAGIC)
   if i<0:
    n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
   if i:self.discarded+=i;del self.buffer[:i]
   if len(self.buffer)<24:break
   h=struct.unpack_from('<12H',self.buffer)
   if h[2]!=0x400 or h[3] not in (0,1) or not 1<=h[6]<=38400 or h[7]!=38400 or h[11]!=0x5aa5 or binascii.crc_hqx(self.buffer[4:20],65535)!=h[10]:
    self.bad_headers+=1;del self.buffer[:1];continue
   length=24+h[6]*2
   if len(self.buffer)<length:break
   payload=bytes(self.buffer[24:length]);del self.buffer[:length]
   try:frames.append((h[4]|h[5]<<16,decode(h,payload),length,h[3]))
   except ValueError:self.bad_frames+=1
  return frames
