"""Actual GBA ARM execution and decoder fault tests; no electrical validation."""
import sys,struct,zlib,binascii,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from sd_video_protocol import Parser

def raw_packet(seq=0):
 pixels=bytes(76800);crc=zlib.crc32(pixels)
 h=[0xb47e,0x5647,0x400,0,seq,0,38400,38400,crc&65535,crc>>16,0,0x5aa5]
 h[10]=binascii.crc_hqx(struct.pack('<8H',*h[2:10]),65535)
 return struct.pack('<12H',*h)+pixels
class Tests(unittest.TestCase):
 def test_viewer_http_pipeline_without_hardware(self):self.exercise_viewer(False)
 def test_emerald_viewer_http_pipeline_without_hardware(self):self.exercise_viewer(True)
 def exercise_viewer(self,emerald):
  import tempfile,threading,time,json,urllib.request
  from unittest.mock import patch
  import sd_video_viewer as viewer
  errors=[];saved=[]
  class FakeSerial:
   def __init__(self,port):
    from graphics_stream import encode_snapshot,SIZE
    self.chunks=[b'READY SD VIDEO 0.4.0\n']+([encode_snapshot(0,6,bytes(SIZE)),encode_snapshot(1,12,bytes(SIZE),bytes(SIZE))] if emerald else [raw_packet(),raw_packet(1)]);self.writes=[]
   def read(self):
    time.sleep(.01)
    return self.chunks.pop(0) if self.chunks else b''
   def write(self,data):self.writes.append(data);saved.append(data)
   def close(self):pass
  def browser(url):
   def check():
    try:
     until=time.monotonic()+5
     while time.monotonic()<until:
      stats=json.load(urllib.request.urlopen(url+'/stats',timeout=2))
      if stats['valid_frames']>=2:break
      time.sleep(.03)
     assert stats['valid_frames']==2
     response=urllib.request.urlopen(url+'/frame',timeout=2)
     assert response.read()==bytes(76800)
     assert b'canvas' in urllib.request.urlopen(url,timeout=2).read()
     urllib.request.urlopen(urllib.request.Request(url+'/stop',data=b'',method='POST'),timeout=2).read()
    except Exception as exc:errors.append(exc)
   thread=threading.Thread(target=check,daemon=True);thread.start();return True
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'tools').mkdir();(root/'tools/sd_video_viewer.html').write_bytes((ROOT/'tools/sd_video_viewer.html').read_bytes())
   (root/'tools/emerald_viewer.html').write_bytes((ROOT/'tools/emerald_viewer.html').read_bytes())
   result=type('Result',(),{'stdout':'GBMirroring (COM99)'})()
   with patch.object(viewer,'ROOT',root),patch.object(viewer,'Serial',FakeSerial),patch.object(viewer.subprocess,'run',return_value=result),patch.object(viewer.webbrowser,'open',side_effect=browser):
    self.assertEqual(viewer.main(emerald),0)
   self.assertEqual(errors,[])
   report=json.loads(next(root.glob('dist/'+('emerald-reports' if emerald else 'sd-video-reports')+'/*/rapporto.json')).read_text())
   self.assertEqual(report['valid_frames'],2);self.assertEqual(report['crc_errors'],0)
   self.assertTrue(list(root.glob('dist/'+('emerald-reports' if emerald else 'sd-video-reports')+'/*/ultimo-frame.bmp')))
  self.assertEqual(saved,[b'START\n',b'STOP\n'])
 def test_actual_gba_gpio_frames(self):
  from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
  uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,size in [(0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x06000000,0x18000)]:uc.mem_map(a,size)
  uc.mem_write(0x02000000,(ROOT/'dist/gbmirroring-sd-video-v0.4.2.gba').read_bytes())
  parser=Parser()
  state=dict(key=0,clock=0,value=0,bits=0,words=[],frames=0,tick=0,codec=[])
  def read(m,access,address,size,value,user):
   if address==0x04000130:
    if state['key']<3:mask=1 if state['key']==1 else 0;state['key']+=1
    else:mask=2 if state['frames']==1 else (0x201 if state['frames']==2 else 0)
    m.mem_write(address,struct.pack('<H',1023^mask))
   elif address==0x04000100:
    state['tick']=(state['tick']+1000)&65535;m.mem_write(address,struct.pack('<H',state['tick']))
  def write(m,access,address,size,value,user):
   if address!=0x04000134:return
   if value&0x30:
    self.assertEqual(value&0xfffc,0x8030) # only SC and SD driven
   if value&1 and not state['clock']:
    state['value']=((state['value']<<1)|((value>>1)&1))&65535;state['bits']+=1
    if state['bits']==16:
     state['words'].append(state['value']);state['bits']=0
     w=state['words']
     if len(w)>=12 and len(w)==24+w[6]:
      decoded=parser.feed(struct.pack('<'+'H'*len(w),*w))
      self.assertEqual(len(decoded),1)
      seq,pixels,wire,codec,metadata=decoded[0]
      self.assertEqual(metadata['version'],'0.4.2');self.assertEqual(metadata['scene'],0 if state['frames']==0 else 1);self.assertEqual(metadata['sender'],'baseline' if state['frames']==2 else 'fast');self.assertEqual(seq,state['frames']);self.assertEqual(pixels,bytes(m.mem_read(0x06000000,76800)))
      state['codec'].append(codec);state['frames']+=1;state['words']=[]
      if state['frames']==3:m.emu_stop()
   state['clock']=value&1
  uc.hook_add(UC_HOOK_MEM_READ,read,begin=0x04000100,end=0x04000131)
  uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000134,end=0x04000135)
  uc.emu_start(0x020000c0,0,count=150000000)
  self.assertEqual(state['frames'],3);self.assertEqual(state['codec'],[3,3,3])
 def test_delta_loss_crc_and_keyframe_recovery(self):
  def packet(seq,codec=2):
   # Zero pixels or zero XOR delta: two RLE runs.
   payload=struct.pack('<4H',0xffff,0,0x8000|5633,0)
   crc=zlib.crc32(bytes(76800))
   h=[0xb47e,0x5647,0x401,codec,seq,0,4,38400,crc&65535,crc>>16,0,0x5aa5]+[0]*12
   h[10]=binascii.crc_hqx(struct.pack('<20H',*(h[2:10]+h[12:])),65535)
   return struct.pack('<24H',*h)+payload
  p=Parser();self.assertEqual(p.feed(packet(1)),[]);self.assertEqual(p.delta_misses,1)
  self.assertEqual(len(p.feed(packet(10,1)+packet(11))),2)
  broken=bytearray(packet(12));broken[-1]^=1
  self.assertEqual(p.feed(broken+packet(13)),[]);self.assertEqual(p.bad_frames,1)
  self.assertEqual(len(p.feed(packet(20,1)+packet(21))),2)
  bad_header=bytearray(packet(22));bad_header[26]^=1
  self.assertEqual(p.feed(bad_header),[]);self.assertGreater(p.bad_headers,0)
 def test_block_codec_bounds(self):
  from sd_video_protocol import decode_blocks
  body=b''.join(struct.pack('<4H',i,0x8002,0x8100,0) for i in range(150))
  self.assertEqual(decode_blocks(body,None,True),bytes(76800))
  self.assertEqual(decode_blocks(b'',bytes(76800),False),bytes(76800))
  for malformed in (body[:-8],body+body[:8],struct.pack('<4H',0,0x8002,0x8200,0)):
   with self.assertRaises(ValueError):decode_blocks(malformed,None,True)
 def test_fragmented_and_recovery(self):
  p=Parser();data=b'noise'+raw_packet();frames=[]
  for i in range(0,len(data),37):frames+=p.feed(data[i:i+37])
  self.assertEqual(len(frames),1);self.assertEqual(p.discarded,5)
 def test_bad_payload_dropped_then_recovers(self):
  data=bytearray(raw_packet());data[-1]^=1;p=Parser()
  frames=p.feed(data+raw_packet(1));self.assertEqual(len(frames),1);self.assertEqual(frames[0][0],1);self.assertEqual(p.bad_frames,1)
 def test_bad_header_and_truncation(self):
  data=bytearray(raw_packet());data[12]^=1;p=Parser()
  self.assertEqual(len(p.feed(data+raw_packet(1))),1)
  self.assertGreater(p.bad_headers,0);self.assertEqual(Parser().feed(raw_packet()[:-1]),[])
 def test_malicious_rle_zero_count(self):
  data=bytearray(raw_packet());h=list(struct.unpack('<12H',data[:24]));h[3]=1;h[6]=1;h[10]=binascii.crc_hqx(struct.pack('<8H',*h[2:10]),65535)
  p=Parser();self.assertEqual(p.feed(struct.pack('<12H',*h)+bytes(2)),[]);self.assertEqual(p.bad_frames,1)
if __name__=='__main__':
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 import json
 (ROOT/'dist/verifica-sd-software-v0.4.2.json').write_text(json.dumps(dict(passed=r.wasSuccessful(),tests=r.testsRun,scope='Actual GBA GPIO output and VRAM reconstruction in ARM emulation; corrupted stream tests. No real pin timing, Windows USB or achieved FPS claim.'),indent=2)+'\n')
 sys.exit(not r.wasSuccessful())
