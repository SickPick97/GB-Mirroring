import struct,unittest,zlib
from graphics_stream import GraphicsParser,encode_snapshot,packet,SIZE

class Echo:
 def render(self,data):return bytes(data)

class Tests(unittest.TestCase):
 def setup_parser(self):
  p=GraphicsParser(Echo());p.feed(encode_snapshot(0,0,bytes(SIZE)))
  p.feed(packet(1,0,0,struct.pack('<3H',0,2,0),0x600));return p
 def test_exact_patch_and_reference_checksum(self):
  block=bytearray(256);block[32:48]=b'x'*16
  body=struct.pack('<HI',4,zlib.crc32(block))+b'x'*16
  p=self.setup_parser();p.feed(packet(1,8,9,body,0x600))
  self.assertEqual(p.pending[2304:2560],block)
  # A perfectly valid wire CRC must not hide an incorrect base resource.
  p=self.setup_parser();p.pending[2304]=1
  p.feed(packet(1,8,9,body,0x600))
  self.assertIsNone(p.pending);self.assertEqual(p.last_error,'stripe_reference_crc')
 def test_bounds_and_invalid_regions(self):
  for body,block in ((b'',9),(struct.pack('<HI',3,0)+bytes(16),9),
                     (struct.pack('<HI',0,0)+bytes(16),9),(struct.pack('<HI',0,0),5)):
   with self.subTest(body=body,block=block):
    p=self.setup_parser();p.feed(packet(1,8,block,body,0x600));self.assertIsNone(p.pending)
 def test_empty_mask_cannot_silently_accept_fingerprint_collision(self):
  p=self.setup_parser();p.feed(packet(1,8,9,struct.pack('<HI',0,zlib.crc32(b'x'*256)),0x600))
  self.assertIsNone(p.pending)

if __name__=='__main__':unittest.main()
