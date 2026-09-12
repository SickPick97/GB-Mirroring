"""Synthetic wire faults: preserve exact resources and subsequent framing."""
import struct, unittest, zlib
from graphics_stream import GraphicsParser, encode_snapshot, SIZE, packet
from wire_repair import repair_payload, repair_header
from recovery_policy import RecoveryPolicy

def bits(data):
 return ''.join(format(w,'016b') for w in struct.unpack('<'+'H'*(len(data)//2),data))
def wire(value):
 value+='0'*((-len(value))%16)
 return struct.pack('<'+'H'*(len(value)//16),*(int(value[i:i+16],2) for i in range(0,len(value),16)))
class Echo:
 def render(self,data):return bytes(data)
class Tests(unittest.TestCase):
 def test_fragmented_transaction_repair(self):
  source=bytes((i*37+i//17)&255 for i in range(SIZE))
  stream=bits(encode_snapshot(0,6,source))
  # BEGIN is 30 bytes; corrupt the following RAW packet header or payload.
  for position in (240+51,240+175,240+192+1393):
   for kind in ('flip','insert','delete'):
    with self.subTest(position=position,kind=kind):
     if kind=='flip': damaged=stream[:position]+str(1-int(stream[position]))+stream[position+1:]
     elif kind=='insert':damaged=stream[:position]+'1'+stream[position:]
     else:damaged=stream[:position]+stream[position+1:]
     damaged+=bits(encode_snapshot(1,12,source,source))+'0'*16
     parser=GraphicsParser(Echo());frames=[];data=wire(damaged)
     for i in range(0,len(data),113):frames.extend(parser.feed(data[i:i+113]))
     self.assertEqual([f[0] for f in frames],[0,1])
     self.assertEqual(frames[-1][1],source)
     self.assertEqual(parser.bad_frames,0)
     self.assertEqual(parser.repaired_headers+parser.repaired_payloads,1)
 def test_double_error_rejected(self):
  data=bytes(range(256));value=bits(data)
  value='1'+value[1:120] +str(1-int(value[120]))+value[121:]+'0'
  self.assertIsNone(repair_payload(value,2048,zlib.crc32(data)))
 def test_header_wait_and_payload_crc(self):
  original=bits(packet(0,1,0,bytes(range(256))))
  damaged=original[:60]+str(1-int(original[60]))+original[61:]
  fixed,waiting=repair_header(damaged[:193]);self.assertIsNone(fixed);self.assertTrue(waiting)
  fixed,_=repair_header(damaged+'0');self.assertIsNotNone(fixed)
  damaged=damaged[:500]+str(1-int(damaged[500]))+damaged[501:]
  self.assertIsNone(repair_header(damaged+'0')[0])
 def test_recovery_lifecycle(self):
  p=RecoveryPolicy()
  self.assertFalse(p.update(100,0,False,False)) # User waiting to activate.
  self.assertTrue(p.update(101,1,False,False))
  self.assertFalse(p.update(106,1,False,True)) # Keyframe in flight.
  self.assertFalse(p.update(107,1,True,False)) # Recovered, stale total cleared.
  self.assertFalse(p.update(120,1,False,False))
  self.assertTrue(p.update(121,2,False,False))
  self.assertFalse(p.update(122,2,False,False))
  self.assertTrue(p.update(125,2,False,False))
if __name__=='__main__':unittest.main()
