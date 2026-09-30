"""Direct mGBA graphics engine; no CPU execution or commercial ROM on PC."""
import ctypes as C
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Renderer:
 def __init__(self,dll=None):
  self.lib=C.CDLL(str(dll or ROOT/'runtime/native/gbm_renderer.dll'))
  self.lib.gbm_create.restype=C.c_void_p
  self.lib.gbm_destroy.argtypes=[C.c_void_p]
  self.lib.gbm_render.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_void_p]
  # per-line register values (scanline effects); older DLLs without it render the effect as a still frame
  self.lines=getattr(self.lib,'gbm_render_lines',None)
  if self.lines:self.lines.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.c_uint,C.c_void_p,C.c_void_p]
  self.context=self.lib.gbm_create()
  if not self.context:raise MemoryError('Renderer allocation')
  self.output=C.create_string_buffer(76800)
 def render(self,graphics,raster=None):
  """raster: [register offset, value for line 0, ..., value for line 159] or None."""
  if raster and self.lines:
   values=(C.c_uint16*160)(*raster[1:161])
   if not self.lines(self.context,bytes(graphics),len(graphics),raster[0],values,self.output):raise ValueError('Invalid graphics state')
   return self.output.raw
  if not self.lib.gbm_render(self.context,bytes(graphics),len(graphics),self.output):raise ValueError('Invalid graphics state')
  return self.output.raw
 def close(self):
  if self.context:self.lib.gbm_destroy(self.context);self.context=None
