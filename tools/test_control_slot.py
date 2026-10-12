"""The resident's real control slot (ARM code in an emulator) against the instruction-level model of the Pico's PIO
program, stepped by the resident's own cycle count: the verdict reaches the resident intact, a block the PC holds gets
its hash back, and the bus is never driven from both ends. Software only: cable and electrical timing are not
modelled."""
import os,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
def verdict(ack,blocks,spoil=False):
    masks=[0]*13
    for b in blocks:masks[b>>5]|=1<<(b&31)
    words=[ack&0xffff]
    for m in masks:words+=[m&0xffff,m>>16]
    check=0x5aa5
    for w in words:check^=w
    return words+[check^(1 if spoil else 0)]
def pio_words(count,resync,words16):
    return [(count-1)|(0x20000 if resync else 0)]+[words16[2*i]|words16[2*i+1]<<16 for i in range(14)]
def mask(blocks):
    masks=[0]*13
    for b in blocks:masks[b>>5]|=1<<(b&31)
    return struct.pack('<13I',*masks)
def blocks_of(data):
    masks=struct.unpack('<13I',data);return set(b for b in range(416) if masks[b>>5]>>(b&31)&1)
@unittest.skipUnless((RESIDENT/'resident.elf').is_file(),'built resident required')
class Slot(unittest.TestCase):
    def run_slot(self,fifo,announced,recent=(),slot_seq=100,sequence=140,valid=1,ok=1,pal_old=0):
        os.environ.setdefault('GBM_ARM_TOOLCHAIN','D:/Progettini')
        import cosim_stream,test_control
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR
        m=cosim_stream.Machine(RESIDENT);u=m.u
        m.pio=test_control.Machine(fifo)
        for b in announced:u.mem_write(m.symbol('hashes')+4*b,struct.pack('<I',(0x1000+b)^1))
        u.mem_write(m.symbol('announced'),mask(announced));u.mem_write(m.symbol('recent'),mask(recent))
        u.mem_write(m.symbol('slot_seq'),struct.pack('<H',slot_seq));m.word(m.symbol('sequence'),sequence)
        m.word(m.symbol('valid'),valid);m.word(m.symbol('feedback'),0);m.word(m.symbol('verdict_ok'),ok);m.word(m.symbol('pal_old'),pal_old);m.word(m.symbol('pal_raw'),0)
        u.reg_write(UC_ARM_REG_R0,1234);u.reg_write(UC_ARM_REG_SP,0x03007f00);u.reg_write(UC_ARM_REG_LR,0x03007800)
        u.emu_start(m.symbol('control_slot')|1,0x03007800,count=4000000)
        m._pio_advance()
        self.assertEqual(m.contention,0);self.assertEqual(m.pio.direction,0)
        left=blocks_of(u.mem_read(m.symbol('announced'),52))
        hashes={b:struct.unpack('<I',u.mem_read(m.symbol('hashes')+4*b,4))[0] for b in announced}
        return m,left,hashes
    def test_verdict_judges_the_blocks_announced_before_the_previous_slot(self):
        """Held by the PC: real hash back (never sent). Not held: hash stays flipped (sent next). Announced since the
        previous slot: still waiting."""
        announced=[9,10,40,41,200,392];recent=[41,200];known=[10,41,392,300]
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(100,known)),announced,recent)
        self.assertEqual(left,{41,200});self.assertEqual(blocks_of(m.u.mem_read(m.symbol('recent'),52)),set())
        for b in announced:self.assertEqual(hashes[b],(0x1000+b)^(0 if b in (10,392) else 1),b)
        self.assertEqual(m.read32(m.symbol('feedback')),1);self.assertEqual(m.read32(m.symbol('valid')),1)
        self.assertEqual(struct.unpack('<H',m.u.mem_read(m.symbol('slot_seq'),2))[0],140)
        self.assertEqual(m.pio.stalled,0);self.assertLess(m.cycles/1232,40,'slot takes too many scanlines')
    def test_verdict_made_before_the_previous_slot_waits(self):
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(99,[9,10])),[9,10],slot_seq=100)
        self.assertEqual(left,{9,10});self.assertEqual(hashes[9],0x1009^1);self.assertEqual(m.read32(m.symbol('verdict_ok')),1)
        # sequence numbers wrap: 3 is newer than 65530
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(3,[9,10])),[9,10],slot_seq=65530)
        self.assertEqual(left,set());self.assertEqual(hashes[9],0x1009)
    def test_fade_the_pc_cannot_follow_goes_back_to_plain_palette_blocks(self):
        """A palette block announced before the previous slot and still not held by the PC: the fade is given up
        (pal_raw). One announced since the previous slot is not judged yet; one the PC holds keeps the fade."""
        m,left,_=self.run_slot(pio_words(448,False,verdict(100,[1])),[1,2],recent=[1,2],pal_old=0b0110)
        self.assertEqual(m.read32(m.symbol('pal_raw')),1);self.assertEqual(m.read32(m.symbol('pal_old')),0b0110)
        m,left,_=self.run_slot(pio_words(448,False,verdict(100,[])),[1,2],recent=[1,2],pal_old=0)
        self.assertEqual(m.read32(m.symbol('pal_raw')),0);self.assertEqual(left,{1,2})
        m,left,_=self.run_slot(pio_words(448,False,verdict(100,[1,2])),[1,2],recent=[1,2],pal_old=0b0110)
        self.assertEqual(m.read32(m.symbol('pal_raw')),0)
    def test_one_slot_without_verdict_is_forgiven(self):
        """After a good verdict (three lives) a damaged or missing one changes nothing: the blocks keep waiting and
        the next slot asks again. The third in a row gives up."""
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(100,[9],spoil=True)),[9,10],recent=[10],ok=3)
        self.assertEqual(left,{9,10});self.assertEqual(blocks_of(m.u.mem_read(m.symbol('recent'),52)),{10})
        self.assertEqual(hashes[9],0x1009^1);self.assertEqual(m.read32(m.symbol('verdict_ok')),2)
        self.assertEqual(struct.unpack('<H',m.u.mem_read(m.symbol('slot_seq'),2))[0],100)
        m,left,_=self.run_slot([],[9,10],ok=2);self.assertEqual(left,{9,10});self.assertEqual(m.read32(m.symbol('verdict_ok')),1)
        m,left,_=self.run_slot([],[9,10],ok=1);self.assertEqual(left,set());self.assertEqual(m.read32(m.symbol('verdict_ok')),0)
    def test_good_verdict_restores_the_three_lives(self):
        m,left,_=self.run_slot(pio_words(448,False,verdict(100,[])),[9],ok=1);self.assertEqual(m.read32(m.symbol('verdict_ok')),3)
    def test_damaged_or_missing_verdict_stops_announcing(self):
        for words in (verdict(100,[9,10],spoil=True),[0xffff]*28):
            m,left,hashes=self.run_slot(pio_words(448,False,words),[9,10])
            self.assertEqual(left,set());self.assertEqual(hashes[9],0x1009^1);self.assertEqual(m.read32(m.symbol('verdict_ok')),0)
            self.assertEqual(m.read32(m.symbol('feedback')),1)
    def test_resync_request_still_arrives(self):
        m,left,_=self.run_slot(pio_words(448,True,verdict(100,[9])),[9,10])
        self.assertEqual(m.read32(m.symbol('valid')),0)
    def test_no_pico_answer_stops_announcing(self):
        """Nothing drives SD (Pico 0.7 after its two bits, or no Pico): pulled high, the check fails."""
        m,left,_=self.run_slot([],[9,10]);self.assertEqual(left,set());self.assertEqual(m.read32(m.symbol('verdict_ok')),0)
if __name__=='__main__':unittest.main()
