"""Stream 0.12 receiver: one 0x700 packet per GBA VBlank, applied to a running cache.

Registers, palette and OAM (blocks 0..8) are captured for every tick; VRAM blocks that
changed but did not fit are reported as *pending* and arrive in later ticks. Frames are
held in order while blocks are pending and published together, each with its own state,
once the cache is complete. The playout buffer in the browser absorbs the resulting burst.
"""
import binascii,struct,zlib
from graphics_stream import GraphicsParser,MAGIC,SIZE,block_hash
HOT_BYTES=9*256
class StreamError(Exception):pass

def decode_record(kind,tag,body,base,dictionary):
    """Return the 256-byte block described by one record; base is the cached block or None."""
    if kind==1:
        if len(body)!=256:raise StreamError('raw_size')
        return bytes(body)
    if kind==3:
        if len(body)!=2:raise StreamError('dict_size')
        slot=struct.unpack('<H',body)[0]
        if slot not in dictionary:raise StreamError('dict_missing')
        return dictionary[slot]
    if kind==4:
        words=struct.unpack('<'+'H'*(len(body)//2),body)
        if len(words)%2:raise StreamError('rle_odd')
        out=bytearray()
        for count,value in zip(words[::2],words[1::2]):
            if count==0 or len(out)+count*2>256:raise StreamError('rle_bounds')
            out.extend(struct.pack('<H',value)*count)
        if len(out)!=256:raise StreamError('rle_size')
        return bytes(out)
    if kind==5:
        if base is None or len(body)<16:raise StreamError('patch_base')
        masks=struct.unpack_from('<8H',body);values=struct.unpack('<'+'H'*((len(body)-16)//2),body[16:])
        if sum(bin(m).count('1') for m in masks)!=len(values):raise StreamError('patch_count')
        out=bytearray(base);i=0
        for word in range(128):
            if masks[word>>4]&(1<<(word&15)):struct.pack_into('<H',out,word*2,values[i]);i+=1
        return bytes(out)
    if kind==6:
        words=struct.unpack('<'+'H'*(len(body)//2),body);result=[];pos=0
        while pos<len(words):
            token=words[pos];pos+=1
            if token&0x8000:
                count=((token&0x7fff)>>7)+3;distance=(token&127)+1
                if distance>len(result) or len(result)+count>128:raise StreamError('lz_bounds')
                for _ in range(count):result.append(result[-distance])
            else:
                if not token or pos+token>len(words) or len(result)+token>128:raise StreamError('lz_literal')
                result.extend(words[pos:pos+token]);pos+=token
        if len(result)!=128:raise StreamError('lz_size')
        return struct.pack('<128H',*result)
    if kind==9:
        block=tag&511
        if base is None or not 233<=block<257 or len(body)<10:raise StreamError('column_base')
        mask,first,second=struct.unpack_from('<HII',body)
        if mask>255 or len(body)!=10+32*bin(mask).count('1'):raise StreamError('column_bounds')
        out=bytearray(base);pos=10
        for column in range(8):
            if mask&(1<<column):
                for row in range(4):
                    offset=row*64+column*8;out[offset:offset+8]=body[pos:pos+8];pos+=8
        if block_hash(out)!=(first,second):raise StreamError('column_reference_hash')
        return bytes(out)
    raise StreamError('kind')

def block_fold(block):
    a,b=block_hash(block);return a^((b*0x9e3779b1)&0xffffffff)

def decode_unit(first,data,base):
    """Apply a layer patch (kind 12) to the 2 KB of the eight blocks starting at `first`.

    Body: flags (bit0 partial), column-pair mask, row-pair mask, 32-bit reference, then the data.
    A partial patch belongs to a larger change sent over several packets: only the last one is verified.
    """
    if first not in (233,241,249) or len(data)<10:raise StreamError('unit_base')
    flags,colmask,rowmask,lo,hi=struct.unpack_from('<5H',data)
    groups=bin(colmask).count('1')+bin(rowmask).count('1')
    if flags>1 or len(data)!=10+groups*128:raise StreamError('unit_bounds')
    out=bytearray(base);pos=10
    for g in range(16):
        if colmask>>g&1:
            for r in range(32):out[r*64+g*4:r*64+g*4+4]=data[pos:pos+4];pos+=4
    for q in range(16):
        if rowmask>>q&1:out[q*128:(q+1)*128]=data[pos:pos+128];pos+=128
    if not flags&1:
        fold=0
        for i in range(8):fold^=block_fold(bytes(out[i*256:(i+1)*256]))
        if fold!=(lo|hi<<16):raise StreamError('unit_reference_hash')
    return bytes(out)

def region(block):
    return 'registers' if block==0 else 'palette' if block<5 else 'objects' if block<9 else 'field_maps' if 233<=block<257 else 'vram_other'

class StreamParser(GraphicsParser):
    def __init__(self,renderer=None,max_hold=8,rom=None,long_hold=180,big_backlog=40):
        super().__init__(renderer);self.rom=rom
        self.max_hold=max_hold;self.long_hold=long_hold;self.big_backlog=big_backlog;self.held=[];self.complete=False;self.feedback_available=False
        self.dropped_incomplete=0;self.forced_releases=0;self.ticks=0;self.frames_published=0
        self.rom_image=None;self.rom_seen=None;self.rom_total=None;self.rom_bad=0;self.rom_missing=0
    ROM_CHUNKS=65536
    def rom_chunk(self,seq,body):
        """256-byte piece of the cartridge image, sent once by the GBA dump mode."""
        if len(body)!=260:self.rom_bad+=1;return
        chunk=body[0]|body[1]<<8|body[2]<<16|body[3]<<24
        if chunk!=seq or chunk>=self.ROM_CHUNKS:self.rom_bad+=1;return
        if self.rom_image is None:self.rom_image=bytearray(self.ROM_CHUNKS*256);self.rom_seen=bytearray(self.ROM_CHUNKS)
        self.rom_image[chunk*256:(chunk+1)*256]=body[4:];self.rom_seen[chunk]=1
    def rom_end(self,body):
        if len(body)==4:self.rom_total=body[0]|body[1]<<8|body[2]<<16|body[3]<<24
    @property
    def rom_received(self):return sum(self.rom_seen) if self.rom_image is not None else 0
    @property
    def rom_complete(self):
        return self.rom_image is not None and self.rom_total==self.ROM_CHUNKS and self.rom_received==self.ROM_CHUNKS
    def fail(self,reason='transaction'):
        super().fail(reason);self.held=[];self.complete=False
    def feed_aligned(self,data):
        self.buffer.extend(data);frames=[]
        while True:
            i=self.buffer.find(MAGIC)
            if i<0:
                n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
            if i:self.discarded+=i;del self.buffer[:i]
            if len(self.buffer)<24:break
            h=struct.unpack_from('<12H',self.buffer)
            if h[2]==0x700:ok=h[3] in (10,11,12) and h[6]<=240
            elif h[2]==0x600:ok=h[3]==2 and h[6]==12
            else:ok=False
            if not ok or h[11]!=0x5aa5 or binascii.crc_hqx(self.buffer[4:20],65535)!=h[10]:
                self.bad_headers+=1;self.cache=None;self.held=[];self.complete=False;del self.buffer[:1];continue
            n=24+h[6]*2
            if len(self.buffer)<n:break
            body=bytes(self.buffer[24:n]);del self.buffer[:n]
            if zlib.crc32(body)!=(h[8]|h[9]<<16):self.fail('payload_crc');continue
            if h[2]==0x600:
                mode=struct.unpack_from('<H',body,20)[0];self.feedback_available=bool(mode&256);continue
            if h[3]==11:self.rom_chunk(h[4]|h[5]<<16,body);continue
            if h[3]==12:self.rom_end(body);continue
            frame=self.apply_tick(h[4]|h[5]<<16,body,n)
            if frame:frames.extend(frame)
        return frames
    def apply_rom_copy(self,body):
        if self.rom is None:self.rom_missing+=1;raise StreamError('rom_missing')
        if len(body)!=10:raise StreamError('rom_copy_size')
        lo,hi,dlo,dhi,size=struct.unpack('<5H',body);src=lo|hi<<16;dest=dlo|dhi<<16
        if not(0x08000000<=src and src-0x08000000+size<=len(self.rom) and 0x06000000<=dest and dest+size<=0x06018000 and size%4==0 and size>0):raise StreamError('rom_copy_bounds')
        offset=HOT_BYTES+dest-0x06000000
        self.cache[offset:offset+size]=self.rom[src-0x08000000:src-0x08000000+size]
    def apply_tick(self,seq,body,wire):
        if len(body)<2*6:self.fail();return []
        flags,lo,hi,pending,records,telemetry=struct.unpack_from('<6H',body)
        interrupts=pending>>9;pending&=511;callback_id=records>>8;records&=255
        key=bool(flags&1);self.feedback_available=bool(flags&256)
        if self.previous is not None and seq==self.previous:return []
        if key:
            self.cache=bytearray(SIZE);self.dictionary={};self.held=[];self.complete=False
        elif self.cache is None or self.previous is None or seq!=((self.previous+1)&0xffffffff):
            self.delta_misses+=1;self.cache=None;self.held=[];self.complete=False;self.previous=seq;return []
        pos=12;seen=set();regions={};codecs={}
        try:
            for _ in range(records):
                if pos+4>len(body):raise StreamError('record_bounds')
                tag,descriptor=struct.unpack_from('<HH',body,pos);pos+=4
                kind=descriptor>>8;size=(descriptor&255)*2;block=tag&511;slot=tag>>9
                if kind not in (1,3,4,5,6,10,12) or size>(510 if kind==12 else 256) or pos+size>len(body):raise StreamError('record_kind')
                if kind==12:
                    first=tag&511
                    if first>=393-7 or any(b in seen for b in range(first,first+8)):raise StreamError('record_block')
                    unit=decode_unit(first,body[pos:pos+size],bytes(self.cache[first*256:(first+8)*256]));pos+=size
                    self.cache[first*256:(first+8)*256]=unit;seen.update(range(first,first+8))
                    r=regions.setdefault('field_maps',dict(blocks=0,payload_bytes=0));r['blocks']+=8;r['payload_bytes']+=size
                    codecs['12']=codecs.get('12',0)+1;continue
                if kind==10:
                    self.apply_rom_copy(body[pos:pos+size]);pos+=size
                    r=regions.setdefault('rom_copies',dict(blocks=0,payload_bytes=0));r['blocks']+=1;r['payload_bytes']+=size
                    codecs['10']=codecs.get('10',0)+1;continue
                if block>=393 or block in seen or slot>=128:raise StreamError('record_block')
                base=bytes(self.cache[block*256:(block+1)*256])
                decoded=decode_record(kind,tag,body[pos:pos+size],base,self.dictionary);pos+=size
                if kind!=3:self.dictionary[slot]=decoded
                self.cache[block*256:(block+1)*256]=decoded;seen.add(block)
                r=regions.setdefault(region(block),dict(blocks=0,payload_bytes=0));r['blocks']+=1;r['payload_bytes']+=size
                codecs[str(kind)]=codecs.get(str(kind),0)+1
            if pos!=len(body):raise StreamError('record_trailing')
        except StreamError as exc:
            self.fail(str(exc));self.previous=seq;return []
        self.previous=seq;self.ticks+=1
        meta=dict(version='emerald-stream-0.12.2',end_game_frame=lo|hi<<16,game_frame=lo|hi<<16,changed_blocks=records,pending_blocks=pending,
            keyframe=key,raster_dma_active=bool(flags&2),feedback_available=bool(flags&256),cadence=(flags>>9)&3,skipped_ticks=(flags>>4)&7,interrupt_enable=interrupts,callback_id=callback_id,unknown_scene=bool(flags&2048),peak_work_scanlines=telemetry&255,previous_words=telemetry>>8,
            resource_regions=regions,block_codecs=codecs,scope='Graphics stream; scanline effects and per-tick temporal coherence not fully verified')
        self.held.append((seq,bytes(self.cache[:HOT_BYTES]),wire,meta))
        if key:self.complete=False
        if pending==0:self.complete=True
        if not self.complete:
            # Cache still being rebuilt after a keyframe: nothing meaningful to show yet.
            if len(self.held)>self.max_hold+4:del self.held[0];self.dropped_incomplete+=1
            return []
        # A scene load leaves a long backlog: keep the last complete image and swap in the finished one.
        limit=self.long_hold if pending>self.big_backlog else self.max_hold
        if pending>0 and len(self.held)<=limit:return []
        forced=pending>0
        if len(self.held)>self.max_hold+4:
            self.dropped_incomplete+=len(self.held)-(self.max_hold+4);del self.held[:len(self.held)-(self.max_hold+4)]
        vram=bytes(self.cache[HOT_BYTES:]);out=[]
        for held_seq,hot,held_wire,held_meta in self.held:
            m=dict(held_meta,held_frames=len(self.held),incomplete=forced and held_seq==seq)
            out.append((held_seq,hot+vram,held_wire,4,m))
        if forced:self.forced_releases+=1
        self.frames_published+=len(out);self.held=[]
        return out
