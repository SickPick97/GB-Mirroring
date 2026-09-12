"""Compare native rendering against the established libretro path."""
import unittest,struct,random,time,json
from pathlib import Path
from native_renderer import Renderer
from graphics_renderer import Renderer as Reference
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
 def test_sprites_windows_blending_and_mosaic(self):
  native=Renderer();old=Reference();rng=random.Random(812)
  gfx=bytearray(100608);gfx[256:]=bytes(rng.randrange(256) for _ in range(100352))
  for i in range(128):struct.pack_into('<4H',gfx,1280+i*8,0x200,0,0,0)
  try:
   for step in range(48):
    struct.pack_into('<H',gfx,0,0x7140)
    struct.pack_into('<H',gfx,8,0x1e00)
    struct.pack_into('<4H',gfx,64,0x10e0,0x20d0,0x1090,0x2080)
    struct.pack_into('<2H',gfx,72,0x3f1f,0x3f3f)
    struct.pack_into('<H',gfx,76,(step%4)*0x1111)
    struct.pack_into('<3H',gfx,80,0x3f3f|((step%4)<<6),0x0808,step%17)
    for i in range(8):
     struct.pack_into('<4H',gfx,1280+i*8,(i*17)|(0x1000 if step%2 else 0),((step*3+i*29)%240)|0x4000,i*4,0)
    self.assertEqual(native.render(gfx),old.render(gfx),'sprite/blend step %s'%step)
  finally:native.close();old.close()
 def test_modes_and_changes(self):
  native=Renderer();old=Reference();rng=random.Random(621)
  gfx=bytearray(100608)
  gfx[256:]=bytes(rng.randrange(256) for _ in range(100352))
  for i in range(128):struct.pack_into('<4H',gfx,1280+i*8,0x200,0,0,0)
  times=[]
  try:
   for mode in range(6):
    struct.pack_into('<H',gfx,0,mode|0x400)
    struct.pack_into('<H',gfx,12,0x80)
    struct.pack_into('<4h',gfx,32,256,0,0,256)
    for step in range(5):
     struct.pack_into('<H',gfx,24,step*3);gfx[256+step*2]=step*15
     expected=old.render(gfx);start=time.perf_counter();observed=native.render(gfx);times.append((time.perf_counter()-start)*1000)
     self.assertEqual(sum(a!=b for a,b in zip(expected,observed)),0,'mode %s step %s'%(mode,step))
  finally:native.close();old.close()
  print(json.dumps(dict(native_ms_mean=sum(times)/len(times),native_ms_max=max(times))))
if __name__=='__main__':unittest.main()
