"""Entering and leaving a building with the resident really running inside the emulated game (mGBA, nothing on the
Link port) must not slow the game down or change where it ends up.

After a door the game spends about thirty frames polling for the wireless adapter instead of waiting for VBlank; from
0.16.0 the resident sends in that time too. Here the whole game runs with the resident injected, so its interrupts,
the game's own serial and timer interrupts and the time taken are those of the emulated console: the building must be
reached and left in the same number of frames, within a small margin, as by the game alone, and show the same picture.
Needs the local cartridge image and the field fixture; skipped otherwise. Emulator only: cable and Pico are absent.
"""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
ROM=ROOT/'PROGETTO AMICO/MGBA TEST/Pokemon - Versione Smeraldo (Italy).gba'
FIELD=ROOT/'build/motion/field.state';RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
UP,DOWN=1<<4,1<<5
def key(f):return UP if 60<=f<230 else DOWN if 500<=f<640 else 0
def play(resident,frames=900):
    from mgba_headless import Core
    state=bytearray(FIELD.read_bytes())
    if resident:
        from verify_firmware import elf_symbols
        sy=elf_symbols((RESIDENT/'resident.elf').read_bytes());blob=bytearray((RESIDENT/'resident.bin').read_bytes())
        struct.pack_into('<I',blob,4,struct.unpack_from('<I',state,0x20ffc)[0]);state[0x5df80:0x5df80+len(blob)]=blob
        struct.pack_into('<I',state,0x20ffc,0x203cf80);struct.pack_into('<I',state,0x21000+sy['enabled'][0]-0x2000000,1)
    core=Core(ROOT/'runtime/mgba/mgba_libretro.dll',ROM.read_bytes());changes=[];last=None;probe=[]
    try:
        core.run();core.restore(state)
        for f in range(frames):
            core.run(1,key(f));st=core.state()
            # the game's VBlank callback (gMain, IWRAM 0x030022cc): it changes at every step of a scene change
            callback=struct.unpack_from('<I',st,0x19000+0x22cc)[0]
            if callback!=last:changes.append((f,callback));last=callback
            # timer 3 running at 1024 cycles a step: the game is inside its wireless-adapter probe
            if struct.unpack_from('<H',st,0x400+0x10e)[0]==0x83:probe.append(f)
    finally:core.close()
    return dict(changes=changes,probe=probe)
@unittest.skipUnless(ROM.is_file() and FIELD.is_file() and (RESIDENT/'resident.elf').is_file(),'cartridge, field fixture and built resident required')
def steps(changes):
    """Scene steps of the game itself: the resident's own hook in the callback slot (an EWRAM address) is not one,
    and neither is the moment in which the game takes its callback away and puts the same one back (end of the
    adapter probe): alone it falls inside one frame, with the resident it may straddle the end of a frame."""
    real=[(f,c) for f,c in changes if c>>24!=2];out=[]
    for i,(f,c) in enumerate(real):
        if c==0 and out and i+1<len(real) and real[i+1][1]==out[-1][1] and real[i+1][0]-f<=2:continue
        if not out or out[-1][1]!=c:out.append((f,c))
    return out
class SceneEntry(unittest.TestCase):
    def test_building_is_entered_and_left_as_fast_as_by_the_game_alone(self):
        import subprocess,json
        # one emulator core per process
        run=lambda r:json.loads(subprocess.run([sys.executable,__file__,'--play',str(int(r))],capture_output=True,text=True,check=True).stdout)
        a=run(False);w=run(True);alone=steps(a['changes']);with_resident=steps(w['changes'])
        self.assertGreaterEqual(len(alone),9,'the scripted walk did not enter and leave the building')
        self.assertEqual([c for f,c in with_resident],[c for f,c in alone],'the game went through different scenes with the resident')
        # the first entry is the scene the fixture starts in; a frame or two of difference is the resident's ticks
        for (f,c),(g,_) in list(zip(alone,with_resident))[1:]:self.assertLessEqual(abs(g-f),3,'scene step %08x at frame %d alone, %d with the resident'%(c,f,g))
        # the probe after the door (about 35 frames in which the resident sends in the game's waits) lasts the same
        self.assertGreater(len(a['probe']),20,'no wireless-adapter probe seen: the fixture does not exercise it')
        self.assertLessEqual(abs(w['probe'][-1]-a['probe'][-1]),1,'the probe ends at frame %d alone, %d with the resident'%(a['probe'][-1],w['probe'][-1]))
        self.assertLessEqual(abs(len(w['probe'])-len(a['probe'])),2)
if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[1]=='--play':
        import json;print(json.dumps(play(bool(int(sys.argv[2])))))
    else:unittest.main()
