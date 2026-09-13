"""Recreate the local Emerald emulator fixture without modifying the ROM/save."""
from pathlib import Path
import struct
from mgba_headless import Core
from link_protocol import bmp
ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'PROGETTO AMICO/MGBA TEST'
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',(source/'Pokemon - Versione Smeraldo (Italy).gba').read_bytes())
    try:
        core.run();core.load_save_copy((source/'Pokemon - Versione Smeraldo (Italy).sav').read_bytes());core.run(900)
        for _ in range(4):core.run(3,1<<3);core.run(90);core.run(3,1<<8);core.run(120)
        for _ in range(3):core.run(3,1);core.run(60)
        state=core.state()
        if struct.unpack_from('<I',state,0x1b2cc)[0]!=0x080863a5:
            raise RuntimeError('Fixture did not reach the overworld; inspect the recovered save')
        out=ROOT/'build/motion';out.mkdir(parents=True,exist_ok=True)
        (out/'field.state').write_bytes(state);bmp(out/'field.bmp',core.rgb555())
        print('Local fixture ready. Inspect build/motion/field.bmp before interpreting movement measurements.')
    finally:core.close()

if __name__=='__main__':main()
