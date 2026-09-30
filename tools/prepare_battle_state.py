"""Local fixture: the frames just before a wild battle starts in tall grass (needs build/motion/field.state).

Walks at random from the field fixture until the game leaves the field VBlank callback for the battle transition, then
keeps the state four steps earlier plus the keys of those steps, so the transition can be replayed with any resident.
"""
from pathlib import Path
import random,struct,sys
from mgba_headless import Core
ROOT=Path(__file__).resolve().parents[1]
FIELD_CALLBACKS=(0,0x080863a5,0x8136dfd)
def main(seeds=(9,5,6,7,8)):
    source=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
    field=ROOT/'build/motion/field.state'
    if not field.is_file():raise SystemExit('Run tools/prepare_motion_state.py first')
    keys_of=[1<<4,1<<5,1<<6,1<<7]
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',source.read_bytes())
    try:
        for seed in seeds:
            core.run();core.restore(bytearray(field.read_bytes()));rng=random.Random(seed);core.run(160,keys_of[1]);history=[]
            for step in range(3000):
                key=rng.choice(keys_of);state=core.state();core.run(16,key)
                history=(history+[(state,key)])[-4:]
                if struct.unpack_from('<I',core.state(),0x1b2cc)[0] not in FIELD_CALLBACKS:
                    out=ROOT/'build/motion';(out/'pre_battle.state').write_bytes(history[0][0]);(out/'pre_battle.keys').write_text(','.join(str(k) for _,k in history))
                    print('Battle fixture ready (seed %d, step %d).'%(seed,step));return
        raise SystemExit('No wild battle found; try other seeds')
    finally:core.close()
if __name__=='__main__':main()
