"""Stream 0.12 receiver: ordering, pending-block holds, ROM replay and fault handling."""
import struct,unittest
from graphics_stream import packet,SIZE
from stream_parser import StreamParser,HOT_BYTES
class Echo:
 def render(self,data):return bytes(data)
def record(kind,block,body,slot=0):
 return struct.pack('<HH',(slot<<9)|block,(kind<<8)|(len(body)//2))+body
def tick(seq,frame,records=(),pending=0,key=False,feedback=False):
 body=struct.pack('<6H',int(key)|(256 if feedback else 0)|0x2000,frame&65535,frame>>16,pending,len(records),0)+b''.join(records)
 return packet(seq,10,0,body,version=0x700)
def raw(block,value,slot=0):return record(4,block,struct.pack('<2H',128,value),slot)  # constant block as RLE (packets are limited to 160 words)
def rom_copy(src,dest,size):return record(10,9+((dest-0x06000000)>>8),struct.pack('<5H',src&65535,src>>16,dest&65535,dest>>16,size))
def parse(parser,*packets):
 out=[]
 for p in packets:out.extend(parser.feed_aligned(p))
 return out
def key_all(seq=0,frame=1):
 """Keyframe that fills block 0 with a marker and leaves everything else zero."""
 return tick(seq,frame,[raw(0,0x1111)],pending=0,key=True)
class Tests(unittest.TestCase):
 def test_key_publishes_hot_state_and_vram(self):
  p=StreamParser(Echo());out=parse(p,tick(0,1,[raw(0,0x1111),raw(9,0x2222,1)],key=True))
  self.assertEqual(len(out),1);g=out[0][1];self.assertEqual(len(g),SIZE)
  self.assertEqual(g[:2],struct.pack('<H',0x1111));self.assertEqual(g[9*256:9*256+2],struct.pack('<H',0x2222))
  self.assertEqual(out[0][4]['end_game_frame'],1)
 def test_pending_frames_wait_and_release_in_order_with_own_state(self):
  p=StreamParser(Echo());parse(p,key_all())
  a=parse(p,tick(1,2,[raw(0,0xaaaa),raw(9,0x3333,2)],pending=2))
  b=parse(p,tick(2,3,[raw(0,0xbbbb)],pending=1))
  self.assertEqual((a,b),([],[]))
  c=parse(p,tick(3,4,[raw(0,0xcccc),raw(10,0x4444,3)],pending=0))
  self.assertEqual([f[4]['end_game_frame'] for f in c],[2,3,4])
  self.assertEqual([f[1][:2] for f in c],[struct.pack('<H',v) for v in (0xaaaa,0xbbbb,0xcccc)])
  self.assertTrue(all(f[1][9*256+256:9*256+258]==struct.pack('<H',0x4444) for f in c))
  self.assertEqual([f[4]['held_frames'] for f in c],[3,3,3])
 def test_forced_release_after_bounded_hold(self):
  p=StreamParser(Echo(),max_hold=3);parse(p,key_all())
  out=[]
  for i in range(1,6):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=5)))
  self.assertEqual(len(out),4);self.assertEqual(p.forced_releases,1);self.assertTrue(out[-1][4]['incomplete'])
  self.assertFalse(out[0][4]['incomplete'])
 def test_long_backlog_keeps_last_image_then_swaps_in_finished_scene(self):
  p=StreamParser(Echo(),max_hold=3);parse(p,key_all());out=[]
  for i in range(1,40):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=100)))
  self.assertEqual(out,[]);self.assertEqual(p.forced_releases,0)
  out=parse(p,tick(40,41,[raw(0,99),raw(9,7,1)],pending=0))
  self.assertEqual(len(out),3+4);self.assertEqual(out[-1][4]['end_game_frame'],41)
  self.assertEqual(out[-1][1][HOT_BYTES:HOT_BYTES+2],struct.pack('<H',7));self.assertEqual(p.dropped_incomplete,40-7)
 def test_layer_patch_applies_columns_and_rows_and_checks_the_reference(self):
  from stream_parser import block_fold
  p=StreamParser(Echo());parse(p,key_all())
  first=233;layer=bytearray(2048)
  def patch(cols,rows,layer_new,partial=False):
   data=bytearray(struct.pack('<5H',1 if partial else 0,sum(1<<c for c in cols),sum(1<<r for r in rows),0,0))
   for g in cols:
    for r in range(32):data+=layer_new[r*64+g*4:r*64+g*4+4]
   for q in rows:data+=layer_new[q*128:(q+1)*128]
   fold=0
   for i in range(8):fold^=block_fold(bytes(layer_new[i*256:(i+1)*256]))
   struct.pack_into('<2H',data,6,fold&65535,fold>>16)
   return record(12,first,bytes(data))
  new=bytearray(layer)
  for r in range(32):new[r*64+12:r*64+16]=bytes([r+1,0,r+2,0])          # column pair 3
  out=parse(p,tick(1,2,[patch([3],[],new)]))
  self.assertEqual(out[0][1][HOT_BYTES+(first-9)*256:HOT_BYTES+(first-9)*256+2048],bytes(new))
  self.assertEqual(out[0][4]['block_codecs'],{'12':1})
  newer=bytearray(new);newer[5*128:6*128]=bytes([9])*128                 # row pair 5 (rows 10 and 11)
  out=parse(p,tick(2,3,[patch([],[5],newer)]))
  self.assertEqual(out[0][1][HOT_BYTES+(first-9)*256:HOT_BYTES+(first-9)*256+2048],bytes(newer))
  wrong=bytearray(newer);wrong[0]=77
  self.assertEqual(parse(p,tick(3,4,[patch([],[],wrong).replace(struct.pack('<5H',0,0,0,0,0),struct.pack('<5H',0,0,0,1,2))])),[])
  self.assertGreater(p.bad_frames,0);self.assertIsNone(p.cache)
 def test_layer_patch_rejects_bad_base_and_lengths(self):
  for body in (struct.pack('<5H',0,1,0,0,0),struct.pack('<5H',0,0,0,0,0)+bytes(3),struct.pack('<5H',2,0,0,0,0)):
   p=StreamParser(Echo());parse(p,key_all())
   self.assertEqual(parse(p,tick(1,2,[record(12,233,body)])),[]);self.assertGreater(p.bad_frames,0)
  p=StreamParser(Echo());parse(p,key_all())
  self.assertEqual(parse(p,tick(1,2,[record(12,234,struct.pack('<5H',0,0,0,0,0))])),[]);self.assertGreater(p.bad_frames,0)
 def test_partial_layer_patch_is_not_verified_until_the_last_piece(self):
  from stream_parser import block_fold
  p=StreamParser(Echo());parse(p,key_all());first=233
  new=bytearray(2048)
  for r in range(32):new[r*64+8:r*64+12]=bytes([1,r,2,r]);new[r*64+16:r*64+20]=bytes([3,r,4,r])
  def piece(cols,partial):
   data=bytearray(struct.pack('<5H',int(partial),sum(1<<c for c in cols),0,0,0))
   for g in cols:
    for r in range(32):data+=new[r*64+g*4:r*64+g*4+4]
   if not partial:
    fold=0
    for i in range(8):fold^=block_fold(bytes(new[i*256:(i+1)*256]))
    struct.pack_into('<2H',data,6,fold&65535,fold>>16)
   return record(12,first,bytes(data))
  self.assertEqual(parse(p,tick(1,2,[piece([2],True)],pending=1)),[])
  out=parse(p,tick(2,3,[piece([4],False)]))
  self.assertEqual(len(out),2);self.assertEqual(out[-1][1][HOT_BYTES+(first-9)*256:HOT_BYTES+(first-9)*256+2048],bytes(new))
 def test_missing_tick_needs_keyframe(self):
  p=StreamParser(Echo());parse(p,key_all())
  self.assertEqual(parse(p,tick(2,3,[raw(0,7)])),[])
  self.assertEqual(p.delta_misses,1);self.assertIsNone(p.cache)
  self.assertEqual(parse(p,tick(3,4,[raw(0,8)])),[])
  self.assertEqual(len(parse(p,tick(4,5,[raw(0,9)],key=True))),1)
 def test_no_frames_before_first_keyframe(self):
  p=StreamParser(Echo());self.assertEqual(parse(p,tick(7,1)),[]);self.assertEqual(p.delta_misses,1)
 def test_frames_during_key_rebuild_are_not_published(self):
  p=StreamParser(Echo())
  self.assertEqual(parse(p,tick(0,1,[raw(0,1)],pending=390,key=True)),[])
  self.assertEqual(parse(p,tick(1,2,[raw(9,2,1)],pending=200)),[])
  out=parse(p,tick(2,3,[raw(10,3,2)],pending=0))
  self.assertEqual(len(out),3);self.assertEqual(out[-1][1][10*256:10*256+2],struct.pack('<H',3))
 def test_rom_copy_replays_cartridge_bytes(self):
  rom=bytes((i*7)&255 for i in range(0x4000));p=StreamParser(Echo(),rom=rom);parse(p,key_all())
  out=parse(p,tick(1,2,[rom_copy(0x08000100,0x06000200,0x80)]))
  vram=out[0][1][HOT_BYTES:];self.assertEqual(vram[0x200:0x280],rom[0x100:0x180]);self.assertEqual(vram[0x280:0x282],b'\0\0')
  self.assertEqual(out[0][4]['block_codecs'],{'10':1});self.assertEqual(out[0][4]['resource_regions']['rom_copies']['blocks'],1)
 def test_rom_copy_rejects_bad_ranges_and_missing_rom(self):
  for rom,record_bytes in ((bytes(0x400),rom_copy(0x08000000,0x06000000,0x800)),(bytes(0x400),rom_copy(0x08000000,0x06017f00,0x200)),(None,rom_copy(0x08000000,0x06000000,0x80)),(bytes(0x400),rom_copy(0x08000000,0x06000002,0x81))):
   p=StreamParser(Echo(),rom=rom);parse(p,key_all())
   self.assertEqual(parse(p,tick(1,2,[record_bytes])),[]);self.assertGreater(p.bad_frames,0);self.assertIsNone(p.cache)
 def test_rom_copy_followed_by_literal_block_in_same_tick(self):
  rom=bytes(range(256))*64;p=StreamParser(Echo(),rom=rom);parse(p,key_all())
  out=parse(p,tick(1,2,[rom_copy(0x08000000,0x06000000,0x200),raw(9,0x5555)]))
  vram=out[0][1][HOT_BYTES:];self.assertEqual(vram[:2],struct.pack('<H',0x5555));self.assertEqual(vram[0x100:0x120],rom[0x100:0x120])
 def test_dictionary_and_rle_records(self):
  p=StreamParser(Echo());parse(p,key_all())
  rle=record(4,9,struct.pack('<2H',128,0x7777),4)
  self.assertEqual(parse(p,tick(1,2,[rle]))[0][1][HOT_BYTES:HOT_BYTES+2],struct.pack('<H',0x7777))
  hit=record(3,11,struct.pack('<H',4),4)
  out=parse(p,tick(2,3,[hit]));self.assertEqual(out[0][1][HOT_BYTES+2*256:HOT_BYTES+2*256+2],struct.pack('<H',0x7777))
  self.assertEqual(parse(p,tick(3,4,[record(3,12,struct.pack('<H',9),9)])),[]);self.assertGreater(p.bad_frames,0)
 def test_corrupt_payload_and_duplicate_block(self):
  p=StreamParser(Echo());parse(p,key_all());data=bytearray(tick(1,2,[raw(9,1)]));data[40]^=0x55
  self.assertEqual(parse(p,bytes(data)),[]);self.assertEqual(p.payload_crc_errors,1)
  q=StreamParser(Echo());parse(q,key_all())
  self.assertEqual(parse(q,tick(1,2,[raw(9,1),raw(9,2)])),[]);self.assertGreater(q.bad_frames,0)
 def test_control_end_reports_feedback_without_publishing(self):
  p=StreamParser(Echo());parse(p,key_all())
  end=packet(9,2,0,struct.pack('<12H',0,0,0,0,0,0,1,10,0,10,2|256,3),version=0x600)
  self.assertEqual(parse(p,end),[]);self.assertTrue(p.feedback_available)
 def test_wire_level_alignment_recovers_a_tick(self):
  p=StreamParser(Echo());first=key_all();second=tick(1,2,[raw(9,0x4242)])
  def bits(data):return ''.join(format(w,'016b') for w in struct.unpack('<'+'H'*(len(data)//2),data))
  for offset in (0,1,7,15):
   q=StreamParser(Echo());stream=bits(first)+'1'*offset+bits(second)+'0'*16
   wire=struct.pack('<'+'H'*(len(stream)//16),*(int(stream[i:i+16],2) for i in range(0,len(stream)-15,16)))
   out=[]
   for i in range(0,len(wire),97):out.extend(q.feed(wire[i:i+97]))
   self.assertEqual(len(out),2,offset);self.assertEqual(out[1][1][HOT_BYTES:HOT_BYTES+2],struct.pack('<H',0x4242))
if __name__=='__main__':unittest.main()
