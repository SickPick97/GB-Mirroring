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

def stream_hash(block):
    """The resident's block hash (fast.S hash_begin): multiply chain and add-rotate over the 64 words, mixed after every
    8 words so that words 32 apart are not interchangeable."""
    a=b=0;words=struct.unpack('<64I',block)
    for g in range(0,64,8):
        for value in words[g:g+8]:
            a=((a^value)*0x9e3779b1)&0xffffffff
            b=((((b<<7)|(b>>25))&0xffffffff)+value)&0xffffffff
        a^=a>>15;b=(b+(b<<7))&0xffffffff
    return a,b

def block_fold(block):
    a,b=stream_hash(block);return a^((b*0x9e3779b1)&0xffffffff)

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

def black(hot):
    """A frame that renders black whatever VRAM holds: forced blank, or every palette entry black."""
    return bool(struct.unpack_from('<H',hot,0)[0]&0x80) or not any(hot[256:1280])

class StreamParser(GraphicsParser):
    def __init__(self,renderer=None,max_hold=30,rom=None,long_hold=240,big_backlog=40,keep=12,fade_keep=40):
        super().__init__(renderer);self.rom=rom;self.keep=keep;self.fade_keep=fade_keep;self.bulk_packets=0;self.raster=[0]*160;self.raster_dest=None;self.load_backlog=8
        self.max_hold=max_hold;self.long_hold=long_hold;self.big_backlog=big_backlog;self.held=[];self.complete=False;self.feedback_available=False
        self.dropped_incomplete=0;self.forced_releases=0;self.ticks=0;self.frames_published=0
        self.rom_image=None;self.rom_seen=None;self.rom_total=None;self.rom_bad=0;self.rom_missing=0
        # Every block content seen, by the resident's hash. A block the GBA announces by hash alone (record 14) is shown
        # at once when its content is here; `waiting` holds the announced blocks whose content must still arrive.
        self.packet_log=None;self.store={};self.rom_index={};self.announced=set();self.waiting={};self.resolved=set();self.resolved=set();self.store_hits=0;self.store_misses=0;self.store_dirty=False
    STORE_MAX=60000
    def remember(self,content):
        if len(self.store)<self.STORE_MAX:
            key=block_fold(content)
            if key not in self.store:self.store[key]=bytes(content);self.store_dirty=True
    def written(self,first,count=1):
        """Content for these blocks has arrived by another record: nothing is outstanding for them any more."""
        for b in range(first,first+count):self.announced.discard(b);self.waiting.pop(b,None);self.resolved.discard(b)
    def outstanding(self,pending,sent_later):
        """Blocks the image must wait for: `pending` (known-changed blocks neither sent nor announced) plus the announced
        blocks whose content is unknown here. `sent_later` (announced, content still to come) is only telemetry."""
        if not sent_later:self.resolved.clear()
        return pending+len(self.waiting)
    def verdict(self):
        """Answer for the resident's control slot (through the Pico): the sequence number read so far and one bit per
        block, set when the content last announced for it is already here; 28 words that xor to 0x5aa5. None while
        the cache is being rebuilt."""
        if self.cache is None or self.previous is None:return None
        masks=[0]*13
        for b in self.resolved:masks[b>>5]|=1<<(b&31)
        words=[self.previous&0xffff]
        for m in masks:words+=[m&0xffff,m>>16]
        check=0x5aa5
        for w in words:check^=w
        return struct.pack('<28H',*words,check)
    def load_store(self,path):
        try:
            with open(path,'rb') as f:data=f.read()
        except OSError:return 0
        for i in range(0,len(data)-259,260):self.store[struct.unpack_from('<I',data,i)[0]]=data[i+4:i+260]
        self.store_dirty=False;return len(self.store)
    def save_store(self,path):
        if not self.store_dirty:return
        temporary=str(path)+'.tmp'
        with open(temporary,'wb') as f:
            for key,content in list(self.store.items()):f.write(struct.pack('<I',key)+content)
        import os;os.replace(temporary,path);self.store_dirty=False
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
        super().fail(reason);self.held=[];self.complete=False;self.announced=set();self.waiting={};self.resolved=set()
    def feed_aligned(self,data):
        self.buffer.extend(data);frames=[]
        while True:
            i=self.buffer.find(MAGIC)
            if i<0:
                n=max(0,len(self.buffer)-3);self.discarded+=n;del self.buffer[:n];break
            if i:self.discarded+=i;del self.buffer[:i]
            if len(self.buffer)<24:break
            h=struct.unpack_from('<12H',self.buffer)
            if h[2]==0x700:ok=h[3] in (10,11,12,13) and h[6]<=240
            elif h[2]==0x600:ok=h[3]==2 and h[6]==12
            else:ok=False
            if not ok or h[11]!=0x5aa5 or binascii.crc_hqx(self.buffer[4:20],65535)!=h[10]:
                self.bad_headers+=1;self.cache=None;self.held=[];self.complete=False;self.announced=set();self.waiting={};self.resolved=set();del self.buffer[:1];continue
            n=24+h[6]*2
            if len(self.buffer)<n:break
            body=bytes(self.buffer[24:n]);del self.buffer[:n]
            if zlib.crc32(body)!=(h[8]|h[9]<<16):self.fail('payload_crc');continue
            if h[2]==0x600:
                mode=struct.unpack_from('<H',body,20)[0];self.feedback_available=bool(mode&256);continue
            if h[3]==11:self.rom_chunk(h[4]|h[5]<<16,body);continue
            if h[3]==12:self.rom_end(body);continue
            if h[3]==13:
                frame=self.apply_bulk(h[4]|h[5]<<16,body,n)
                if frame:frames.extend(frame)
                continue
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
        self.written(9+((dest-0x06000000)>>8),((dest+size-1-0x06000000)>>8)-((dest-0x06000000)>>8)+1)
        # During a scene load (large backlog) the held ticks are the loading screens: tiles copied from the ROM belong in
        # all of them, or the replayed fade would show the old scene under the new palette. While walking, each held tick
        # keeps its own sprite pose.
        for entry in self.held:
            if entry[3]['pending_blocks']>self.load_backlog:entry[4][offset-HOT_BYTES:offset-HOT_BYTES+size]=self.rom[src-0x08000000:src-0x08000000+size]
    def apply_records(self,body,records):
        """Applies the records of a tick or bulk packet to the running cache; returns (regions, codecs)."""
        pos=14;seen=set();regions={};codecs={}
        for _ in range(records):
            if pos+4>len(body):raise StreamError('record_bounds')
            tag,descriptor=struct.unpack_from('<HH',body,pos);pos+=4
            kind=descriptor>>8;size=(descriptor&255)*2;block=tag&511;slot=tag>>9
            if kind not in (1,3,4,5,6,10,12,13,14) or size>(510 if kind==12 else 256) or pos+size>len(body):raise StreamError('record_kind')
            if kind==13:
                self.apply_raster(body[pos:pos+size]);pos+=size
                codecs['13']=codecs.get('13',0)+1;continue
            if kind==14:
                if size!=4 or block<9 or block>=393 or block in seen:raise StreamError('record_block')
                key=struct.unpack_from('<I',body,pos)[0];pos+=size;self.announced.add(block)
                # what the block held is remembered: the game may put it back, and then announces it again
                self.remember(bytes(self.cache[block*256:(block+1)*256]))
                content=self.store.get(key)
                if content is None and key in self.rom_index:
                    data,offset=self.rom_index[key];content=data[offset:offset+256]
                if content is None:self.waiting[block]=key;self.resolved.discard(block);self.store_misses+=1
                else:
                    self.waiting.pop(block,None);self.resolved.add(block);self.store_hits+=1
                    self.cache[block*256:(block+1)*256]=content;self.complete_held(block*256,content)
                codecs['14']=codecs.get('14',0)+1;continue
            if kind==12:
                first=tag&511
                if first>=393-7 or any(b in seen for b in range(first,first+8)):raise StreamError('record_block')
                unit=decode_unit(first,body[pos:pos+size],bytes(self.cache[first*256:(first+8)*256]));pos+=size
                self.cache[first*256:(first+8)*256]=unit;seen.update(range(first,first+8));self.complete_held(first*256,unit);self.written(first,8)
                for i in range(0,2048,256):self.remember(unit[i:i+256])
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
            if block>=9:self.complete_held(block*256,decoded);self.written(block);self.remember(decoded)
            r=regions.setdefault(region(block),dict(blocks=0,payload_bytes=0));r['blocks']+=1;r['payload_bytes']+=size
            codecs[str(kind)]=codecs.get(str(kind),0)+1
        if pos!=len(body):raise StreamError('record_trailing')
        return regions,codecs
    def apply_raster(self,body):
        """Half (80 lines) of the scanline-effect table: one value per line for one video register, raw or run-length."""
        if len(body)<2:raise StreamError('raster_size')
        flags=struct.unpack_from('<H',body)[0];dest=flags&0xff;part=(flags>>10)&1;words=struct.unpack('<%dH'%(len(body)//2-1),body[2:])
        if dest<8 or dest>=0x60 or dest&1:raise StreamError('raster_register')
        if flags&0x800:
            values=[]
            for i in range(0,len(words)-1,2):values+= [words[i+1]]*words[i]
            if len(words)%2 or len(values)!=80:raise StreamError('raster_rle')
        else:
            if len(words)!=80:raise StreamError('raster_size')
            values=list(words)
        if self.raster_dest!=dest:self.raster=[0]*160
        self.raster_dest=dest;self.raster[part*80:part*80+80]=values
    def complete_held(self,offset,data):
        """A block sent as content (not a ROM replay) completes the ticks still held: each keeps its own copy of VRAM,
        so a sprite frame replayed for a later tick never shows up with an earlier tick's sprite positions."""
        for entry in self.held:entry[4][offset-HOT_BYTES:offset-HOT_BYTES+len(data)]=data
    def continues(self,seq):
        """True when seq follows the last packet and the cache is usable; otherwise the cache waits for a keyframe."""
        if self.cache is not None and self.previous is not None and seq==((self.previous+1)&0xffffffff):return True
        self.delta_misses+=1;self.cache=None;self.held=[];self.complete=False;self.announced=set();self.waiting={};self.resolved=set();self.previous=seq;return False
    def apply_tick(self,seq,body,wire):
        if len(body)<2*7:self.fail();return []
        flags,lo,hi,pending,records,telemetry,sent_later=struct.unpack_from('<7H',body)
        interrupts=pending>>9;pending&=511;callback_id=records>>8;records&=255
        key=bool(flags&1);self.feedback_available=bool(flags&256)
        if self.previous is not None and seq==self.previous:return []
        if key:
            self.cache=bytearray(SIZE);self.dictionary={};self.held=[];self.complete=False;self.announced=set();self.waiting={};self.resolved=set()
        elif not self.continues(seq):return []
        try:regions,codecs=self.apply_records(body,records)
        except StreamError as exc:
            self.fail(str(exc));self.previous=seq;return []
        self.previous=seq;self.ticks+=1;pending=self.outstanding(pending,sent_later)
        if not flags&2:self.raster_dest=None
        raster=[self.raster_dest]+self.raster if self.raster_dest is not None else None
        meta=dict(raster=raster,version='emerald-stream-0.14.0',end_game_frame=lo|hi<<16,game_frame=lo|hi<<16,changed_blocks=records,pending_blocks=pending,
            keyframe=key,raster_dma_active=bool(flags&2),feedback_available=bool(flags&256),cadence=(flags>>9)&3,skipped_ticks=(flags>>4)&7,heavy_tick=bool(flags&128),interrupt_enable=interrupts,callback_id=callback_id,unknown_scene=bool(flags&2048),peak_work_scanlines=telemetry&255,idle_slack=telemetry>>8,waiting_blocks=len(self.waiting),announced_blocks=sent_later,
            resource_regions=regions,block_codecs=codecs,idle_packets=0,idle_words=0,scope='Graphics stream; scanline effects and per-tick temporal coherence not fully verified')
        self.held.append((seq,bytes(self.cache[:HOT_BYTES]),wire,meta,bytearray(self.cache[HOT_BYTES:])))
        if self.packet_log:self.packet_log(dict(t='tick',seq=seq,frame=lo|hi<<16,pending=pending,later=sent_later,waiting=len(self.waiting),held=len(self.held),words=wire//2,codecs=codecs,lines=telemetry&255,slack=telemetry>>8,heavy=int(bool(flags&128)),key=int(key),cb=callback_id,skipped=(flags>>4)&7))
        if key:self.complete=False
        return self.settle(pending,pending+sent_later)
    def apply_bulk(self,seq,body,wire):
        """Blocks sent while the game waited for VBlank: they complete the cache of the last tick, no new image."""
        if len(body)<2*7:self.fail();return []
        flags,lo,hi,pending,records,telemetry,sent_later=struct.unpack_from('<7H',body)
        pending&=511;records&=255
        if self.previous is not None and seq==self.previous:return []
        if not self.continues(seq):return []
        try:regions,codecs=self.apply_records(body,records)
        except StreamError as exc:
            self.fail(str(exc));self.previous=seq;return []
        self.previous=seq;self.bulk_packets+=1;pending=self.outstanding(pending,sent_later)
        if self.packet_log:self.packet_log(dict(t='idle',seq=seq,pending=pending,later=sent_later,waiting=len(self.waiting),held=len(self.held),words=wire//2,codecs=codecs))
        if self.held:
            # registers, palette and OAM left over by a heavy tick belong to that tick
            if any(k in regions for k in ('registers','palette','objects')):
                last=self.held[-1];self.held[-1]=(last[0],bytes(self.cache[:HOT_BYTES]),last[2],last[3],last[4])
            m=self.held[-1][3];m['idle_packets']+=1;m['idle_words']=telemetry;m['pending_blocks']=pending
            for k,v in codecs.items():m['block_codecs'][k]=m['block_codecs'].get(k,0)+v
            for k,v in regions.items():
                r=m['resource_regions'].setdefault(k,dict(blocks=0,payload_bytes=0));r['blocks']+=v['blocks'];r['payload_bytes']+=v['payload_bytes']
        return self.settle(pending,pending+sent_later)
    def settle(self,pending,backlog=None):
        """Publishes the held ticks once no known-changed block is outstanding; never mixes old and new tiles unless
        a backlog outlasts the hold limit (then the release is marked incomplete)."""
        if pending==0:self.complete=True
        if not self.held:return []
        if not self.complete:
            # Cache still being rebuilt after a keyframe: nothing meaningful to show yet.
            if len(self.held)>self.keep:self.dropped_incomplete+=len(self.held)-self.keep;del self.held[:len(self.held)-self.keep]
            return []
        # A scene load leaves a long backlog: keep the last complete image and swap in the finished one.
        # How long the wait may last depends on everything the resident still has to send: a missing block's content
        # comes in turn with the contents of the announced blocks already known here.
        limit=self.long_hold if (pending if backlog is None else backlog)>self.big_backlog else self.max_hold
        if pending>0 and len(self.held)<=limit:return []
        forced=pending>0
        # After a long hold (a scene load) the newest held ticks are replayed, so the fade-in of the new scene is seen as
        # in the game; the black frames of the loading screen before it are collapsed into one. The browser then
        # catches up with the live stream.
        long=len(self.held)>self.max_hold
        keep=self.fade_keep if long else self.keep
        if len(self.held)>keep:
            self.dropped_incomplete+=len(self.held)-keep;del self.held[:len(self.held)-keep]
        while long and len(self.held)>1 and black(self.held[0][1]) and black(self.held[1][1]):
            del self.held[0];self.dropped_incomplete+=1
        out=[];last=self.held[-1][0]
        for held_seq,hot,held_wire,held_meta,vram in self.held:
            m=dict(held_meta,held_frames=len(self.held),incomplete=forced and held_seq==last)
            out.append((held_seq,hot+bytes(vram),held_wire,4,m))
        if forced:self.forced_releases+=1
        self.frames_published+=len(out);self.held=[]
        return out
