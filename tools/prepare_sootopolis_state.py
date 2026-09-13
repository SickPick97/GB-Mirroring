"""Local test fixture at Ceneride. Changes only an in-memory copy of the save.

Uses map/structure definitions from pret/pokeemerald and layout bytes from the
user's own BPEI ROM. No modified save or ROM is written or distributed.
"""
import struct
from pathlib import Path
from mgba_headless import Core
from link_protocol import bmp
ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'PROGETTO AMICO/MGBA TEST'
    rom=(source/'Pokemon - Versione Smeraldo (Italy).gba').read_bytes()
    save=bytearray((source/'Pokemon - Versione Smeraldo (Italy).sav').read_bytes())
    assert rom[0xac:0xb0]==b'BPEI'
    assert struct.unpack_from('<6I',rom,0x3e5368)==(60,60,0x083e3740,0x083e3748,0x083dc448,0x083dc580)
    x,y=43,32
    for sector in range(28):
        off=sector*4096
        if struct.unpack_from('<H',save,off+0xff4)[0]!=1:continue
        struct.pack_into('<hh',save,off,x,y)
        save[off+4:off+12]=bytes([0,7,255,0,255,255,255,255])
        struct.pack_into('<H',save,off+0x32,8)
        # The retail SavedMapViewIsEmpty overreads this field. Supply a correct
        # 15x14 saved view instead of relying on clearing its nominal 256 words.
        for row in range(14):
            for col in range(15):
                tile=struct.unpack_from('<H',rom,0x3e3748+((y-7+row)*60+x-7+col)*2)[0]
                struct.pack_into('<H',save,off+0x34+(row*15+col)*2,tile)
        for obj in range(16):
            address=off+0xa30+obj*36
            if save[address+2]&1:
                save[address+9:address+11]=bytes([7,0])
                for delta in (12,16,20):struct.pack_into('<hh',save,address+delta,x+7,y+7)
            else:save[address]&=254
        total=sum(struct.unpack_from('<992I',save,off))&0xffffffff
        struct.pack_into('<H',save,off+0xff6,((total&65535)+(total>>16))&65535)
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',rom)
    try:
        core.run();core.load_save_copy(bytes(save));core.run(900)
        for _ in range(4):core.run(3,1<<3);core.run(90);core.run(3,1<<8);core.run(120)
        for _ in range(3):core.run(3,1);core.run(60)
        out=ROOT/'build/sootopolis';out.mkdir(parents=True,exist_ok=True)
        (out/'field.state').write_bytes(core.state());bmp(out/'field.bmp',core.rgb555())
        core.run(48,1<<7);bmp(out/'right.bmp',core.rgb555())
        core.restore((out/'field.state').read_bytes());core.run(40,1<<4);core.run(240)
        inside=out/'center';inside.mkdir(exist_ok=True)
        (inside/'field.state').write_bytes(core.state());bmp(inside/'field.bmp',core.rgb555())
    finally:core.close()

if __name__=='__main__':main()
