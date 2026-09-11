"""Use mGBA display engine with our idle homebrew, never the cartridge ROM."""
import struct
from pathlib import Path
from mgba_headless import Core
ROOT=Path(__file__).resolve().parents[1]
class Renderer:
 def __init__(self,dll=None):
  self.core=Core(dll or ROOT/'runtime/mgba/mgba_libretro.dll',(ROOT/'dist/gbmirroring-sd-video-v0.4.1.gba').read_bytes())
  self.core.run(3);self.template=self.core.state()
 def render(self,graphics):
  if len(graphics)!=100608:raise ValueError('Incomplete graphics cache')
  state=bytearray(self.template);state[0x400:0x460]=graphics[:96];state[0x800:0x19000]=graphics[256:]
  self.core.restore(state);self.core.run(2)
  return struct.pack('<38400H',*self.core.rgb555())
 def close(self):self.core.close()
