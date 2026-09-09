"""Wire protocol v1 for our GBA bench; no USB dependencies."""
import binascii
import struct
from pathlib import Path

MAGIC = [0xb17e, 0x4d47]
WORDS = 72

def crc(words):
    return binascii.crc_hqx(struct.pack('<'+'H'*len(words),*words),0xffff)

def pattern(seq, i):
    if i<12:
        return [0,0xffff,0xa55a,0x7fff,0x8000][i-7]
    x = (seq ^ (0x9e3779b9*(i+1))) & 0xffffffff
    x ^= x>>16
    x = (x*0x45d9f3b)&0xffffffff
    x ^= x>>16
    return x&0xffff

class Parser:
    def __init__(self):
        self.buffer=[]
        self.bad_crc=0
        self.discarded=0
        self.valid=0

    def feed(self, word):
        self.buffer.append(word)
        while len(self.buffer)>=2:
            if self.buffer[:2]!=MAGIC:
                self.discarded+=1
                self.buffer.pop(0)
                continue
            if len(self.buffer)<WORDS:
                return None
            w=self.buffer[:WORDS]
            if w[2]!=1 or w[3] not in (1,2) or w[6]!=64 or crc(w[2:-1])!=w[-1]:
                self.bad_crc+=1
                self.discarded+=1
                self.buffer.pop(0)
                continue
            del self.buffer[:WORDS]
            self.valid+=1
            return (w[3],w[4]|(w[5]<<16),w[7:71])
        return None

def bmp(path, pixels):
    if len(pixels)!=38400:
        raise ValueError('Screenshot incompleto')
    data=bytearray()
    for y in range(159,-1,-1):
        for v in pixels[y*240:(y+1)*240]:
            r,g,b=v&31,(v>>5)&31,(v>>10)&31
            data.extend(((b<<3)|(b>>2),(g<<3)|(g>>2),(r<<3)|(r>>2)))
    header=struct.pack('<2sIHHI',b'BM',54+len(data),0,0,54)
    header+=struct.pack('<IiiHHIIiiII',40,240,160,1,24,0,len(data),2835,2835,0,0)
    Path(path).write_bytes(header+data)

class Measurement:
    def __init__(self, challenge):
        self.challenge=challenge
        self.frames=0
        self.pattern_errors=0
        self.gaps=0
        self.duplicates=0
        self.echoes=0
        self.previous=None
        self.first_errors=None
        self.last_errors=0
        self.keys_seen=0

    def accept(self, frame):
        kind,seq,data=frame
        if kind!=1:
            return
        self.frames+=1
        self.keys_seen |= data[1]
        self.echoes+=data[0]==self.challenge
        if self.previous is not None:
            delta=(seq-self.previous)&0xffffffff
            if delta==0:
                self.duplicates+=1
            elif delta!=1:
                self.gaps+=delta-1 if delta<0x80000000 else 1
        self.previous=seq
        self.pattern_errors+=sum(data[i]!=pattern(seq,i) for i in range(7,64))
        self.last_errors=data[5]|(data[6]<<16)
        if self.first_errors is None:
            self.first_errors=self.last_errors

    def result(self, elapsed, bad_crc):
        errors=(self.last_errors-(self.first_errors or 0))&0xffffffff
        clean=(self.frames>=5 and self.echoes>=2 and not any(
            [bad_crc,self.pattern_errors,self.gaps,self.duplicates,errors]))
        return dict(clean=clean,seconds=round(elapsed,3),packets=self.frames,
                    crc_errors=bad_crc,pattern_errors=self.pattern_errors,
                    missing_packets=self.gaps,duplicates=self.duplicates,
                    challenge_echoes=self.echoes,gba_serial_errors_delta=errors,
                    keys_seen_mask=self.keys_seen,
                    verified_payload_bytes_s=round(self.frames*128/elapsed,1))
