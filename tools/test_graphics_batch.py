"""Batch integrity, exact byte accounting and rejection before presentation."""
import struct,unittest
from graphics_stream import GraphicsParser,packet,encode_snapshot,SIZE

class Echo:
 def render(self,data):return bytes(data)

class Tests(unittest.TestCase):
 def parser(self):
  p=GraphicsParser(Echo());p.feed(encode_snapshot(0,0,bytes(SIZE)));return p
 def begin(self):return packet(1,0,0,struct.pack('<3H',0,2,0),0x600)
 def end(self,count):return packet(1,2,0,struct.pack('<12H',2,0,count,0,2,0,1,0,0,10,2050,2),0x600)
 def test_multiple_blocks_share_crc_and_keep_wire_accounting(self):
  body=struct.pack('<6H',9,0x402,128,123,10,0x301)+struct.pack('<H',0)
  wire=self.begin()+packet(1,7,0,body,0x600)+self.end(2)
  p=self.parser();frames=p.feed(wire)
  self.assertEqual(len(frames),1);self.assertEqual(frames[0][2],len(wire))
  self.assertEqual(frames[0][1][9*256:11*256],struct.pack('<H',123)*256)
  self.assertEqual(frames[0][4]['version'],'emerald-batched-0.9.0')
 def test_malformed_batch_never_presents_partial_state(self):
  cases=[b'',b'\0\0',struct.pack('<2H',9,0x701),struct.pack('<3H',9,0x480,1),
         struct.pack('<4H',9,0x402,128,123)+b'\0\0']
  for body in cases:
   with self.subTest(body=body):
    p=self.parser();self.assertEqual(p.feed(self.begin()+packet(1,7,0,body,0x600)+self.end(1)),[])
    self.assertGreater(p.bad_frames,0)

if __name__=='__main__':unittest.main()
