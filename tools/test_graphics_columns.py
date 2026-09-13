"""Column geometry, bounds and independent reference validation."""
import struct,unittest
from graphics_stream import GraphicsParser,encode_snapshot,packet,SIZE,block_hash

class Echo:
 def render(self,data):return bytes(data)

class Tests(unittest.TestCase):
 def parser(self):
  p=GraphicsParser(Echo());p.feed(encode_snapshot(0,0,bytes(SIZE)))
  p.feed(packet(1,0,0,struct.pack('<3H',0,2,0),0x600));return p
 def body(self,mask):
  data=bytearray(256);parts=[]
  for col in range(8):
   if mask&(1<<col):
    for row in range(4):
     part=bytes([col*4+row+1])*8;data[row*64+col*8:row*64+col*8+8]=part;parts.append(part)
  return data,struct.pack('<HII',mask,*block_hash(data))+b''.join(parts)
 def test_all_groups_and_batch(self):
  for mask in [1<<i for i in range(8)]+[0,129,7]:
   with self.subTest(mask=mask):
    data,body=self.body(mask);p=self.parser()
    p.feed(packet(1,7,0,struct.pack('<HH',233,(9<<8)|(len(body)//2))+body,0x600))
    self.assertEqual(p.pending[233*256:234*256],data)
    self.assertEqual(p.dictionary[0],data)
 def test_wrong_reference_rejected_even_with_valid_wire_crc(self):
  data,body=self.body(1);p=self.parser();p.pending[233*256+50]=1
  p.feed(packet(1,9,233,body,0x600))
  self.assertEqual(p.last_error,'column_reference_hash');self.assertIsNone(p.pending)
 def test_invalid_region_length_and_mask(self):
  _,body=self.body(1)
  for block,raw in [(232,body),(257,body),(233,body[:-2]),(233,struct.pack('<HII',256,0,0)),(233,b'')]:
   p=self.parser();p.feed(packet(1,9,block,raw,0x600));self.assertIsNone(p.pending)
 def test_empty_mask_cannot_hide_signature_collision(self):
  p=self.parser();p.feed(packet(1,9,233,struct.pack('<HII',0,1,0),0x600))
  self.assertEqual(p.last_error,'column_reference_hash')

if __name__=='__main__':unittest.main()
