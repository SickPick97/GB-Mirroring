import unittest,threading,socket,struct
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from frame_hub import FrameHub,websocket
class Tests(unittest.TestCase):
 def test_bounded_order_and_late_subscriber(self):
  h=FrameHub(3)
  for i in range(6):h.publish(i,i*2,bytes([i]))
  self.assertEqual(len(h.frames),3);self.assertEqual(h.next(0)[0],6)
  self.assertEqual(h.next(3)[0],4);self.assertEqual(h.next(4)[0],5)
  self.assertIsNone(h.next(6,.001));h.close();self.assertIsNone(h.next(0))
 def test_websocket_pixels_ping_and_close(self):
  hub=FrameHub();stop=threading.Event()
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):websocket(self,hub,stop)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  client=socket.create_connection(server.server_address,timeout=2)
  try:
   client.sendall(b'GET /stream HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n')
   stream=client.makefile('rb')
   self.assertIn(b'101',stream.readline())
   while stream.readline()!=b'\r\n':pass
   hub.publish(7,42,bytes(76800))
   self.assertEqual(stream.read(2),b'\x82\x7f')
   self.assertEqual(struct.unpack('>Q',stream.read(8))[0],76808)
   self.assertEqual(stream.read(76808),struct.pack('<II',7,42)+bytes(76800))
   client.sendall(b'\x89\x81abcd'+bytes([ord('x')^ord('a')]))
   self.assertEqual(stream.read(3),b'\x8a\x01x')
   client.sendall(b'\x88\x80abcd')
   self.assertEqual(stream.read(2),b'\x88\0');stream.close()
  finally:
   client.close();stop.set();hub.close();server.shutdown();server.server_close();thread.join(2)
if __name__=='__main__':unittest.main()
