"""Emulator-only Main callback counter, private in-memory ROM instrumentation.

The recovered ROM/save are never modified. Does not certify hardware audio.
"""
import json,struct
from pathlib import Path
from mgba_headless import Core
from verify_firmware import elf_symbols
ROOT=Path(__file__).resolve().parents[1]

def main():
    rom=(ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
    assert len(rom)==0x1000000
    # Wrap the field callback1, preserving registers and tail-calling it. Count Main iterations,
    # independent of the VBlank IRQ counter. Code exists only in emulator memory.
    rom+=struct.pack('<10I',0xe92d400f,0xe59f0014,0xe5901000,0xe2811001,0xe5801000,0xe8bd400f,0xe59fc004,0xe12fff1c,0x0203fd00,0x08085e19)
    field=(ROOT/'build/motion/field.state').read_bytes();results=[]
    for candidate in (None,'emerald-cache'):
        state=bytearray(field)
        assert struct.unpack_from('<I',state,0x1b2c0)[0]==0x08085e19
        if candidate:
            folder=ROOT/'build'/candidate;sy=elf_symbols((folder/'resident.elf').read_bytes())
            blob=bytearray((folder/'resident.bin').read_bytes())
            struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0])
            state[0x5df80:0x60c00]=bytes(0x2c80);state[0x5df80:0x5df80+len(blob)]=blob
            struct.pack_into('<I',state,0x20ffc,0x203cf80)
            struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1)
        struct.pack_into('<I',state,0x1b2c0,0x09000000);struct.pack_into('<I',state,0x60d00,0)
        core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom)
        try:
            core.run();core.restore(state);core.run(480)
            before=struct.unpack_from('<I',core.state(),0x60d00)[0]
            for frame in range(1200):core.run(1,1<<(7 if frame%240<120 else 6))
            after=core.state();assert struct.unpack_from('<I',after,0x1b2c0)[0]==0x09000000
            iterations=struct.unpack_from('<I',after,0x60d00)[0]-before
            results.append(dict(variant=candidate or 'unmodified_game',emulated_frames=1200,main_iterations=iterations,main_fps=iterations*16777216/280896/1200))
        finally:core.close()
    report=dict(scope='Local mGBA directional-input test with Main callback instrumentation; not hardware or audio certification',results=results)
    (ROOT/'build/motion/gameplay.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
