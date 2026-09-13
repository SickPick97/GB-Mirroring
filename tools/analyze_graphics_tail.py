"""Inspect CRC-verified records in an incomplete USB tail; never invent frames."""
import argparse,struct,zlib,json,collections
from pathlib import Path
from wire_repair import valid_header,from_bits
from graphics_stream import GraphicsParser,packet,SIZE

def analyze(data):
 bits=''.join(format(w,'016b') for w in struct.unpack('<'+'H'*(len(data)//2),data[:len(data)//2*2]))
 magic=format(0xb47e,'016b')+format(0x5647,'016b');position=0;records=[];verified=0
 while True:
  start=bits.find(magic,position)
  if start<0 or start+192>len(bits):break
  position=start+1;header=from_bits(bits[start:start+192])
  if not valid_header(header):continue
  h=struct.unpack('<12H',header);end=start+192+h[6]*16
  if end>len(bits):break
  body=from_bits(bits[start+192:end])
  if zlib.crc32(body)!=(h[8]|h[9]<<16):continue
  position=end;verified+=1
  if h[3]==7:
   pos=0
   while pos+4<=len(body):
    tag,desc=struct.unpack_from('<HH',body,pos);pos+=4;n=(desc&255)*2
    if pos+n>len(body):break
    records.append((desc>>8,tag,body[pos:pos+n]));pos+=n
  else:records.append((h[3],h[7],body))
 p=GraphicsParser(None);p.pending=bytearray(SIZE);p.sequence=1;p.key=False
 known=set();hist=collections.Counter();cost=0;ideal=0;comparisons=0;regions=collections.Counter()
 for kind,tag,body in records:
  hist[kind]+=1
  if kind==0:
   if len(body)==6 and struct.unpack_from('<H',body)[0]:known.clear();p.dictionary={}
   continue
  if kind not in (1,3,4,5,6,8):continue
  block=tag&511
  if block>=393 or (kind in (5,8) and block not in known):continue
  if kind==3 and (len(body)!=2 or struct.unpack('<H',body)[0] not in p.dictionary):continue
  old=bytes(p.pending[block*256:(block+1)*256]);p.seen=set()
  p.feed_aligned(packet(1,kind,tag,body,0x600))
  if p.pending is None:
   p.pending=bytearray(SIZE);p.sequence=1;known.clear();continue
  new=bytes(p.pending[block*256:(block+1)*256])
  if block>=9 and block in known:
   stripes=sum(old[i:i+16]!=new[i:i+16] for i in range(0,256,16))
   cost+=len(body);ideal+=min(len(body),6+16*stripes);comparisons+=1
  regions['registers' if block==0 else 'palette' if block<5 else 'oam' if block<9 else 'vram']+=len(body)
  known.add(block)
 return dict(scope='Partial tail, not a full session or FPS estimate; ideal unbounded stripe cache is only a byte comparison',verified_packets=verified,record_types=dict(hist),region_payload_bytes=dict(regions),known_vram_comparisons=comparisons,existing_payload_bytes=cost,ideal_sparse_payload_bytes=ideal)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('path');args=ap.parse_args()
 print(json.dumps(analyze(Path(args.path).read_bytes()),indent=2))
