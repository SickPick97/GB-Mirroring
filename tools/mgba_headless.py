"""Development-only libretro harness; all cartridge/save data stays in memory."""
import ctypes as C,struct
from pathlib import Path
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
class Game(C.Structure):
 _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class Core:
 def __init__(self,dll,rom):
  self.lib=C.CDLL(str(Path(dll).resolve()));self.frame=None;self.pixel_format=0;self.keys=0
  def env(cmd,p):
   if cmd==10:self.pixel_format=C.cast(p,C.POINTER(C.c_uint))[0];return self.pixel_format in (0,1,2)
   if cmd==3:C.cast(p,C.POINTER(C.c_bool))[0]=True;return True
   if cmd==17:C.cast(p,C.POINTER(C.c_bool))[0]=False;return True
   return False
  def video(p,w,h,pitch):
   if p:self.frame=(w,h,pitch,C.string_at(p,pitch*h))
  self.callbacks=[ENV(env),VIDEO(video),AUDIO(lambda l,r:None),BATCH(lambda p,n:n),POLL(lambda:None),INPUT(lambda port,device,index,key: int(bool(self.keys&(1<<key))) if port==0 and key<16 else 0)]
  for name,cb in zip(('environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'),self.callbacks):
   fn=getattr(self.lib,'retro_set_'+name);fn.argtypes=[type(cb)];fn(cb)
  self.lib.retro_init()
  self.rom=C.create_string_buffer(rom);g=Game(None,C.cast(self.rom,C.c_void_p),len(rom),None)
  self.lib.retro_load_game.argtypes=[C.POINTER(Game)];self.lib.retro_load_game.restype=C.c_bool
  if not self.lib.retro_load_game(C.byref(g)):raise RuntimeError('Cannot load local ROM')
  self.lib.retro_serialize_size.restype=C.c_size_t
  self.lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_serialize.restype=C.c_bool
  self.lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];self.lib.retro_unserialize.restype=C.c_bool
 def load_save_copy(self,data):
  self.lib.retro_get_memory_size.argtypes=[C.c_uint];self.lib.retro_get_memory_size.restype=C.c_size_t
  self.lib.retro_get_memory_data.argtypes=[C.c_uint];self.lib.retro_get_memory_data.restype=C.c_void_p
  n=self.lib.retro_get_memory_size(0);ptr=self.lib.retro_get_memory_data(0)
  if not ptr or len(data)<n:raise ValueError('Save size mismatch')
  C.memmove(ptr,data,n)
  self.lib.retro_reset()
 def run(self,n=1,keys=0):
  self.keys=keys
  for _ in range(n):self.lib.retro_run()
 def state(self):
  n=self.lib.retro_serialize_size();b=C.create_string_buffer(n)
  if not self.lib.retro_serialize(b,n):raise RuntimeError('Serialize failed')
  return bytearray(b.raw)
 def restore(self,state):
  b=C.create_string_buffer(bytes(state))
  if not self.lib.retro_unserialize(b,len(state)):raise RuntimeError('Restore failed')
 def rgb555(self):
  w,h,pitch,raw=self.frame;out=[]
  for y in range(h):
   if self.pixel_format==1:
    for x in range(w):v=struct.unpack_from('<I',raw,y*pitch+x*4)[0];out.append(((v>>19)&31)|((v>>6)&992)|((v<<7)&31744))
   else:
    for x in range(w):
     v=struct.unpack_from('<H',raw,y*pitch+x*2)[0]
     out.append(((v>>11)&31)|((v>>1)&992)|((v&31)<<10) if self.pixel_format==2 else ((v>>10)&31)|(v&992)|((v&31)<<10))
  return out
 def close(self):self.lib.retro_unload_game();self.lib.retro_deinit()
