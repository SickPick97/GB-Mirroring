"""Block contents the game can only produce by decompressing cartridge data (tilesets, battle backgrounds, move
effects): the PC unpacks every LZ77 stream of its own cartridge image once and indexes the 256-byte windows by the
resident's block hash. A block the GBA announces by hash is then shown without waiting for its 128 words."""
import struct
from stream_parser import block_fold

def lz77(rom,pos,limit=0x10000):
    """Decompresses a GBA BIOS LZ77 stream at pos; None when it is not a plausible one."""
    if pos+4>len(rom) or rom[pos]!=0x10:return None
    size=rom[pos+1]|rom[pos+2]<<8|rom[pos+3]<<16
    if size<256 or size>limit or size&31:return None
    out=bytearray();pos+=4;end=len(rom)
    while len(out)<size:
        if pos>=end:return None
        flags=rom[pos];pos+=1
        for bit in range(8):
            if len(out)>=size:break
            if flags&(0x80>>bit):
                if pos+2>end:return None
                a=rom[pos];b=rom[pos+1];pos+=2
                count=(a>>4)+3;back=((a&15)<<8|b)+1
                if back>len(out):return None
                for _ in range(count):out.append(out[-back])
            else:
                if pos>=end:return None
                out.append(rom[pos]);pos+=1
    return bytes(out[:size])

def scan(rom,progress=None):
    """Yields (offset, data) for every LZ77 stream found on a 4-byte boundary."""
    pos=rom.find(b'\x10',0)
    while pos>=0:
        if not pos&3:
            data=lz77(rom,pos)
            if data is not None and len(set(data))>2:
                yield pos,data
                if progress:progress(pos)
        pos=rom.find(b'\x10',pos+1)

def build(rom,progress=None):
    """{hash: (stream data, offset)} for every tile-aligned 256-byte window of every stream."""
    index={}
    for _,data in scan(rom,progress):
        for offset in range(0,len(data)-255,32):
            window=data[offset:offset+256]
            if window.count(window[0])==256:continue
            index.setdefault(block_fold(window),(data,offset))
    return index
