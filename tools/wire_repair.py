"""Bounded single-bit wire recovery. Accept only a unique CRC-verified result."""
import struct, zlib, binascii

def from_bits(bits):
 raw=int(bits or '0',2).to_bytes(len(bits)//8,'big')
 out=bytearray(len(raw));out[::2]=raw[1::2];out[1::2]=raw[::2]
 return bytes(out)

def edits(bits,length,start=0):
 """Yield corrected bytes and actual wire-length delta (-1, 0, +1)."""
 current=int(bits[:length],2);short=current>>1
 extra=int(bits[:length+1],2) if len(bits)>length else None
 size=length//8
 def encode(value):
  raw=value.to_bytes(size,'big');out=bytearray(size)
  out[::2]=raw[1::2];out[1::2]=raw[::2];return bytes(out)
 for pos in range(start,length):
  shift=length-1-pos;mask=(1<<shift)-1
  yield encode(current^(1<<shift)),0
  base=((short>>shift)<<(shift+1))|(short&mask)
  yield encode(base),-1
  yield encode(base|(1<<shift)),-1
 if extra is not None:
  for pos in range(start,length+1):
   shift=length-pos
   yield encode(((extra>>(shift+1))<<shift)|(extra&((1<<shift)-1))),1

def valid_header(raw):
 h=struct.unpack('<12H',raw)
 return (h[0:2]==(0xb47e,0x5647) and h[2] in (0x500,0x501,0x600)
         and h[3]<=(6 if h[2]==0x600 else 2) and h[6]<=128
         and h[11]==0x5aa5 and binascii.crc_hqx(raw[4:20],65535)==h[10])

def repair_payload(bits,length,crc):
 matches=set()
 for raw,delta in edits(bits,length):
  if zlib.crc32(raw)==crc:matches.add((raw,delta))
 return next(iter(matches)) if len(matches)==1 else None

def repair_header(bits):
 matches=set();waiting=False
 for raw,delta in edits(bits,192,32):
  if not valid_header(raw):continue
  h=struct.unpack('<12H',raw);start=192+delta;end=start+h[6]*16
  if len(bits)<end:waiting=True;continue
  body=from_bits(bits[start:end])
  if zlib.crc32(body)==(h[8]|h[9]<<16):matches.add((raw,body,end))
 return (next(iter(matches)) if len(matches)==1 else None),waiting
