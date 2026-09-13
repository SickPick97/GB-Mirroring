"""Expanded dictionary and raw fallback regression tests for the shipped resident."""
import random,struct,unittest
from graphics_stream import GraphicsParser,packet,encode_snapshot,SIZE

class Echo:
 def render(self,data):return bytes(data)

class Tests(unittest.TestCase):
 def test_highest_slot_reference_and_bounds(self):
  p=GraphicsParser(Echo());p.feed(encode_snapshot(0,0,bytes(SIZE)))
  begin=packet(1,0,0,struct.pack('<3H',0,2,0),0x600)
  body=struct.pack('<7H',(127<<9)|9,0x402,128,0x1234,10,0x301,127)
  end=packet(1,2,0,struct.pack('<12H',2,0,2,0,2,0,1,0,0,8,8194,2),0x600)
  frames=p.feed(begin+packet(1,7,0,body,0x600)+end)
  self.assertEqual(frames[0][1][9*256:11*256],struct.pack('<H',0x1234)*256)
  self.assertEqual(frames[0][4]['version'],'emerald-cache-0.10.0')
  p.feed(packet(2,0,0,struct.pack('<3H',0,3,0),0x600)+packet(2,3,11,struct.pack('<H',128),0x600))
  self.assertIsNone(p.pending);self.assertGreater(p.bad_frames,0)

if __name__=='__main__':unittest.main()
