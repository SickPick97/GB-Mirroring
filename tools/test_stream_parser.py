"""Stream 0.12 receiver: ordering, pending-block holds, ROM replay and fault handling."""
import struct,unittest
from graphics_stream import packet,SIZE
from stream_parser import StreamParser,HOT_BYTES
class Echo:
 def render(self,data):return bytes(data)
def record(kind,block,body,slot=0):
 return struct.pack('<HH',(slot<<9)|block,(kind<<8)|(len(body)//2))+body
def tick(seq,frame,records=(),pending=0,key=False,feedback=False,scene=0,later=0):
 body=struct.pack('<7H',int(key)|(256 if feedback else 0)|0x6000,frame&65535,frame>>16,pending,len(records)|(scene<<8),0,later)+b''.join(records)
 return packet(seq,10,0,body,version=0x700)
def raw(block,value,slot=0):return record(4,block,struct.pack('<2H',128,value),slot)  # constant block as RLE (packets are limited to 160 words)
def rom_copy(src,dest,size):return record(10,9+((dest-0x06000000)>>8),struct.pack('<5H',src&65535,src>>16,dest&65535,dest>>16,size))
def announce(block,key):return record(14,block,struct.pack('<II',*key))
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
  p=StreamParser(Echo(),long_hold=3);parse(p,key_all())
  out=[]
  for i in range(1,5):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=5)))
  self.assertEqual(len(out),4);self.assertEqual(p.forced_releases,1);self.assertTrue(out[-1][4]['incomplete'])
  self.assertFalse(out[0][4]['incomplete'])
 def test_announced_block_is_shown_from_contents_seen_before(self):
  """Record 14 (hash only): a content seen earlier is restored at once, and shown when the resident, told by the
  verdict that the PC holds it, has checked the block again and no longer counts it."""
  from stream_parser import stream_hash
  p=StreamParser(Echo());parse(p,key_all())
  parse(p,tick(1,2,[raw(20,0x7777,1)]));known=struct.pack('<H',0x7777)*128
  parse(p,tick(2,3,[raw(20,0x1234,2)]))
  self.assertEqual(parse(p,tick(3,4,[announce(20,stream_hash(known))],pending=1,later=1)),[])
  self.assertEqual(p.store_hits,1);self.assertEqual(p.resolved,{20})
  out=parse(p,tick(4,5,[],pending=0))
  self.assertEqual([f[4]['end_game_frame'] for f in out],[4,5]);self.assertEqual(out[0][1][20*256:21*256],known);self.assertEqual(p.resolved,set());p.resolved={20}
  self.assertEqual(struct.unpack('<28H',p.verdict())[1+2*(20>>5)],1<<20&0xffff)
 def test_unknown_announcement_waits_for_the_content(self):
  p=StreamParser(Echo());parse(p,key_all())
  self.assertEqual(parse(p,tick(1,2,[announce(30,(0xdeadbeef,7))],pending=1,later=1)),[]);self.assertEqual(p.waiting,{30:(0xdeadbeef,7)})
  self.assertEqual(parse(p,tick(2,3,[raw(0,2)],pending=1,later=0)),[])
  out=parse(p,tick(3,4,[raw(30,0x4444,1)],pending=0));self.assertEqual([f[4]['end_game_frame'] for f in out][-1],4)
  self.assertEqual(p.waiting,{});self.assertEqual(out[-1][1][30*256:30*256+2],struct.pack('<H',0x4444))
 def test_announcement_is_found_in_the_cartridge_graphics(self):
  import rom_blocks
  from stream_parser import stream_hash
  data=bytes((i*5+i//7)&255 for i in range(1024))
  packed=bytearray(bytes([16])+struct.pack('<I',len(data))[:3])
  for i in range(0,len(data),8):packed+=bytes(1)+data[i:i+8]
  rom=bytes(16)+bytes(packed)+bytes(64)
  index=rom_blocks.build(rom);window=data[96:352];self.assertIn(stream_hash(window),index)
  p=StreamParser(Echo());p.rom_index=index;parse(p,key_all())
  parse(p,tick(1,2,[announce(40,stream_hash(window))],pending=1,later=1));out=parse(p,tick(2,3,[],pending=0))
  self.assertEqual(out[0][1][40*256:41*256],window)
 def test_announcement_is_found_uncompressed_in_the_cartridge(self):
  import rom_blocks
  from stream_parser import stream_hash
  rom=bytes(100)+bytes((i*7+i//3)&255 for i in range(2000))+bytes(64)
  index=rom_blocks.build_raw(rom)
  if index is None:self.skipTest('runtime/native/gbm_blocks.dll not built')
  window=rom[340:596];p=StreamParser(Echo());p.raw_index=index;parse(p,key_all())
  parse(p,tick(1,2,[announce(40,stream_hash(window))],pending=1,later=1));out=parse(p,tick(2,3,[],pending=0))
  self.assertEqual(out[0][1][40*256:41*256],window)
  # a hash that is nowhere in the image, and the windows of one repeated word, are not found
  self.assertIsNone(index.find((1,2)));self.assertIsNone(index.find(stream_hash(bytes(256))))
 def test_palette_fade_is_computed_from_the_unfaded_palette(self):
  """Record 15: the hash of a palette block during a fade, the fade colour and step. The block is the unfaded one
  held here, blended; record 16 brings the unfaded palette when the PC cannot have it (fade-in of a new scene)."""
  from stream_parser import stream_hash,fade_block
  def fade(block,content,color,step):return record(15,block,struct.pack('<IIHH',*stream_hash(content),color|0x8000,step<<6))
  plain=struct.pack('<128H',*[(i*37+5)&0x7fff for i in range(128)])
  p=StreamParser(Echo());parse(p,key_all());parse(p,tick(1,2,[record(1,2,plain)]))
  # fade to black: the step in the record is the next one, the block holds the one before
  out=parse(p,tick(2,3,[fade(2,fade_block(plain,0,6),0,8)],pending=1,later=1))
  self.assertEqual(len(out),1);self.assertEqual(out[0][1][2*256:3*256],fade_block(plain,0,6));self.assertEqual(p.resolved,{2});self.assertEqual(p.fade_hits,1)
  # a new scene: its palette arrives as record 16 and the fade-in from white is followed from it
  fresh=struct.pack('<128H',*[(i*91+3)&0x7fff for i in range(128)])
  out=parse(p,tick(3,4,[record(16,2,fresh),fade(2,fade_block(fresh,0x7fff,12),0x7fff,10)],pending=1,later=1))
  self.assertEqual(out[0][1][2*256:3*256],fade_block(fresh,0x7fff,12))
  # a palette that is not a blend of the one held here: not shown, waits for its content
  odd=bytes(reversed(fresh))
  self.assertEqual(parse(p,tick(4,5,[fade(2,odd,0,4)],pending=1,later=1)),[]);self.assertIn(2,p.waiting);self.assertEqual(p.resolved,set())
  out=parse(p,tick(5,6,[record(1,2,odd)],pending=0));self.assertEqual(out[-1][1][2*256:3*256],odd);self.assertEqual(p.waiting,{})
 def test_fade_with_two_steps_in_one_block_needs_the_native_solver(self):
  import rom_blocks
  from stream_parser import stream_hash,fade_block
  solve=rom_blocks.fade_solver()
  if solve is None:self.skipTest('runtime/native/gbm_blocks.dll not built')
  plain=struct.pack('<128H',*[(i*37+5)&0x7fff for i in range(128)])
  mixed=fade_block(plain,0,16)[:96]+plain[96:160]+fade_block(plain,0,16)[160:]
  self.assertEqual(solve(plain,0,stream_hash(mixed)),mixed);self.assertEqual(solve(plain,0,stream_hash(fade_block(plain,0,9))),fade_block(plain,0,9))
  self.assertIsNone(solve(plain,0,(1,2)))
  p=StreamParser(Echo());p.fade_solver=solve;parse(p,key_all());parse(p,tick(1,2,[record(1,3,plain)]))
  out=parse(p,tick(2,3,[record(15,3,struct.pack('<IIHH',*stream_hash(mixed),0x8000,14<<6))],pending=1,later=1))
  self.assertEqual(out[0][1][3*256:4*256],mixed)
 def test_ticks_whose_palette_was_held_back_are_not_replayed(self):
  """Flag bit 10: during a scene load the palette waits for the tiles; those ticks would be shown with old colours."""
  def held_back(seq,frame,records,pending):
   body=struct.pack('<7H',0x6000|1024,frame&65535,frame>>16,pending,len(records),0,0)+b''.join(records);return packet(seq,10,0,body,version=0x700)
  p=StreamParser(Echo());parse(p,key_all())
  self.assertEqual(parse(p,held_back(1,2,[raw(20,1)],300)),[]);self.assertEqual(parse(p,held_back(2,3,[raw(21,1)],200)),[])
  self.assertEqual(parse(p,tick(3,4,[raw(22,1)],pending=4)),[])
  out=parse(p,tick(4,5,[raw(1,0x7fff)],pending=0))
  self.assertEqual([f[4]['end_game_frame'] for f in out],[4,5])
 def test_resident_0_13_0_with_six_fields_is_still_followed(self):
  """No bit 14 in the first field: six fixed fields, as the 0.13.0 resident of the stable line sends."""
  def old(seq,frame,records,pending=0,key=False):
   body=struct.pack('<6H',int(key)|0x2000|(1<<9),frame&65535,frame>>16,pending,len(records),0)+b''.join(records);return packet(seq,10,0,body,version=0x700)
  p=StreamParser(Echo());out=parse(p,old(0,1,[raw(0,0x1111)],key=True),old(1,2,[raw(9,0x2222,1)]))
  self.assertEqual(len(out),2);self.assertEqual(out[1][1][9*256:9*256+2],struct.pack('<H',0x2222));self.assertEqual(out[1][4]['version'],'emerald-stream-0.13.0')
  self.assertFalse(out[1][4]['palette_held_back'])
  # and the new one right after, on the same parser (a restart with the other resident)
  out=parse(p,tick(0,1,[raw(0,0x1111)],key=True));self.assertEqual(out[0][4]['version'],'emerald-stream-0.16.0')
 def test_verdict_words_xor_to_the_check_value(self):
  p=StreamParser(Echo());self.assertIsNone(p.verdict());parse(p,key_all());parse(p,tick(1,2,[raw(0,1)]))
  words=struct.unpack('<28H',p.verdict());x=0
  for w in words:x^=w
  self.assertEqual(x,0x5aa5);self.assertEqual(words[0],1)
 def test_battle_effect_is_shown_while_its_graphics_arrive(self):
  """A move keeps a hundred blocks outstanding for its whole length: frames come out every few ticks, marked incomplete."""
  p=StreamParser(Echo());parse(p,key_all());out=[]
  for i in range(1,41):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=100,scene=164)))
  self.assertGreaterEqual(len(out),27);self.assertGreater(p.forced_releases,2)
  self.assertEqual([f[4]['end_game_frame'] for f in out],list(range(2,2+len(out))))
 def test_battle_start_is_still_waited_for(self):
  p=StreamParser(Echo());parse(p,key_all());out=[]
  for i in range(1,61):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=393 if i<20 else 80,scene=164)))
  self.assertEqual(out,[]);self.assertEqual(p.forced_releases,0)
 def test_no_forced_release_while_blocks_keep_arriving(self):
  """A backlog that shrinks is waited for even past forty blocks left: the image is never shown unfinished."""
  p=StreamParser(Echo());parse(p,key_all());out=[]
  for i in range(1,60):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=30 if i<45 else 60-i)))
  self.assertEqual(out,[]);self.assertEqual(p.forced_releases,0)
  out=parse(p,tick(60,61,[raw(0,60)],pending=0));self.assertTrue(out);self.assertFalse(any(f[4]['incomplete'] for f in out))
 def test_long_backlog_keeps_last_image_then_swaps_in_finished_scene(self):
  p=StreamParser(Echo(),max_hold=3,keep=7,fade_keep=1);parse(p,key_all());out=[]
  for i in range(1,40):out.extend(parse(p,tick(i,i+1,[raw(0,i)],pending=140-i)))
  self.assertEqual(out,[]);self.assertEqual(p.forced_releases,0)
  out=parse(p,tick(40,41,[raw(0,99),raw(9,7,1)],pending=0))
  self.assertEqual(len(out),1);self.assertEqual(out[-1][4]['end_game_frame'],41)
  self.assertEqual(out[-1][1][HOT_BYTES:HOT_BYTES+2],struct.pack('<H',7));self.assertEqual(p.dropped_incomplete,40-1)
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
 def test_interrupt_enable_and_callback_id_ride_in_the_high_bits(self):
  p=StreamParser(Echo());parse(p,key_all())
  body=struct.pack('<7H',0x6000|(3<<4)|2048,2,0,(6<<9)|0,(0x5a<<8)|1,0,0)+raw(0,0x7777)
  out=parse(p,packet(1,10,0,body,version=0x700))
  self.assertEqual(len(out),1);m=out[0][4]
  self.assertEqual((m['pending_blocks'],m['changed_blocks'],m['interrupt_enable'],m['callback_id'],m['skipped_ticks'],m['unknown_scene']),(0,1,6,0x5a,3,True))
 def test_bulk_packet_completes_the_held_tick_without_a_new_image(self):
  p=StreamParser(Echo());parse(p,key_all())
  a=parse(p,tick(1,2,[raw(0,0xaaaa)],pending=2))
  body=struct.pack('<7H',0x6000,2,0,1,1,40,0)+raw(9,0x5555,3)
  b=parse(p,packet(2,13,0,body,version=0x700))
  body=struct.pack('<7H',0x6000,2,0,0,1,80,0)+raw(10,0x6666,4)
  c=parse(p,packet(3,13,0,body,version=0x700))
  self.assertEqual((a,b),([],[]));self.assertEqual(len(c),1)
  m=c[0][4];self.assertEqual((m['end_game_frame'],m['idle_packets'],m['pending_blocks'],m['incomplete']),(2,2,0,False))
  g=c[0][1];self.assertEqual(g[:2],struct.pack('<H',0xaaaa));self.assertEqual(g[10*256:10*256+2],struct.pack('<H',0x6666))
  self.assertEqual(p.bulk_packets,2)
 def test_bulk_packet_out_of_sequence_waits_for_a_keyframe(self):
  p=StreamParser(Echo());parse(p,key_all())
  body=struct.pack('<7H',0x6000,1,0,0,1,0,0)+raw(9,1)
  self.assertEqual(parse(p,packet(5,13,0,body,version=0x700)),[]);self.assertIsNone(p.cache);self.assertEqual(p.delta_misses,1)
 def test_scene_load_replays_the_fade_in_after_one_black_frame(self):
  p=StreamParser(Echo(),max_hold=3,keep=3,fade_keep=10);parse(p,key_all());out=[]
  for i in range(1,6):out+=parse(p,tick(i,i+1,[raw(0,i)],pending=100-i))
  for i in range(6,10):out+=parse(p,tick(i,i+1,[raw(0,i),raw(1,0x1000*(i-5),i)],pending=100-i))
  out+=parse(p,tick(10,11,[raw(0,10)],pending=0))
  self.assertEqual([f[4]['end_game_frame'] for f in out],[6,7,8,9,10,11])
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
  self.assertEqual(len(out),1);self.assertEqual(out[0][4]["end_game_frame"],3);self.assertEqual(out[-1][1][10*256:10*256+2],struct.pack('<H',3))
 def test_scene_load_replays_reach_every_held_loading_frame(self):
  rom=bytes((i*7)&255 for i in range(0x4000));p=StreamParser(Echo(),rom=rom);parse(p,key_all())
  parse(p,tick(1,2,[raw(0,1)],pending=50));parse(p,tick(2,3,[raw(0,2)],pending=50))
  out=parse(p,tick(3,4,[raw(0,3),rom_copy(0x08000100,0x06010000,0x80)],pending=0))
  self.assertEqual(len(out),3);self.assertTrue(all(f[1][HOT_BYTES+0x10000:HOT_BYTES+0x10080]==rom[0x100:0x180] for f in out))
 def test_held_tick_keeps_its_own_sprite_frame(self):
  """A ROM replay of a later tick (next sprite pose) must not appear in an earlier held tick; content blocks complete it."""
  rom=bytes((i*7)&255 for i in range(0x4000));p=StreamParser(Echo(),rom=rom);parse(p,key_all())
  a=parse(p,tick(1,2,[raw(0,1)],pending=1))
  b=parse(p,tick(2,3,[raw(0,2),rom_copy(0x08000100,0x06010000,0x80),raw(20,0x5555,2)],pending=0))
  self.assertEqual(a,[]);self.assertEqual([f[4]['end_game_frame'] for f in b],[2,3])
  first,second=b[0][1][HOT_BYTES:],b[1][1][HOT_BYTES:]
  self.assertEqual(first[0x10000:0x10080],bytes(0x80));self.assertEqual(second[0x10000:0x10080],rom[0x100:0x180])
  self.assertEqual(first[11*256:11*256+2],struct.pack('<H',0x5555))
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
