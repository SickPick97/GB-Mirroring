"""Block contents the game can only produce by decompressing cartridge data (tilesets, battle backgrounds, move
effects): the PC unpacks every LZ77 stream of its own cartridge image once and indexes the 256-byte windows by the
resident's block hash. A block the GBA announces by hash is then shown without waiting for its 128 words."""
import struct
import ctypes
from pathlib import Path
from stream_parser import stream_hash

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
    """{(hash a, hash b): (stream data, offset)} for every tile-aligned 256-byte window of every stream."""
    index={}
    for _,data in scan(rom,progress):
        for offset in range(0,len(data)-255,32):
            window=data[offset:offset+256]
            if window.count(window[0])==256:continue
            index.setdefault(stream_hash(window),(data,offset))
    return index

class RawIndex:
    """The 256-byte windows of the cartridge image itself (graphics the game copies unchanged: sprites, some tilesets),
    by the resident's hash. Built by runtime/native/gbm_blocks.dll in about a second; without the library the
    index is simply absent and those blocks arrive as data."""
    class Entry(ctypes.Structure):_fields_=[('a',ctypes.c_uint32),('b',ctypes.c_uint32),('offset',ctypes.c_uint32)]
    def __init__(self,rom,library=None):
        library=Path(library) if library else Path(__file__).resolve().parents[1]/'runtime/native/gbm_blocks.dll'
        self.lib=ctypes.CDLL(str(library));self.rom=bytes(rom)
        self.lib.gbm_blocks_index.restype=ctypes.c_uint32;self.lib.gbm_blocks_index.argtypes=[ctypes.c_char_p,ctypes.c_uint32,ctypes.c_void_p]
        self.lib.gbm_blocks_find.restype=ctypes.c_uint32;self.lib.gbm_blocks_find.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32]
        self.entries=(self.Entry*(len(self.rom)//4+1))()
        self.count=self.lib.gbm_blocks_index(self.rom,len(self.rom),self.entries)
    def find(self,key):
        offset=self.lib.gbm_blocks_find(self.entries,self.count,key[0],key[1])
        if offset==0xffffffff:return None
        content=self.rom[offset:offset+256]
        return content if stream_hash(content)==tuple(key) else None
def build_raw(rom):
    try:return RawIndex(rom)
    except OSError:return None

def fade_solver(library=None):
    """Callable (unfaded block, colour, (hash a, hash b), reported step) -> block or None from the native library: every fade step,
    also two steps shared among the eight palettes. None without the library (the parser then tries single steps)."""
    try:
        lib=ctypes.CDLL(str(Path(library) if library else Path(__file__).resolve().parents[1]/'runtime/native/gbm_blocks.dll'))
        lib.gbm_blocks_fade.restype=ctypes.c_int;lib.gbm_blocks_fade.argtypes=[ctypes.c_char_p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_char_p]
    except (OSError,AttributeError):return None
    def solve(unfaded,color,key,hint=16):
        out=ctypes.create_string_buffer(256)
        return out.raw if lib.gbm_blocks_fade(bytes(unfaded),color,hint,key[0],key[1],out) else None
    return solve
