"""The resident's real control slot (ARM code in an emulator) against the instruction-level model of the Pico's PIO
program, stepped by the resident's own cycle count: the verdict reaches the resident intact, a known block gets its
hash back, and the bus is never driven from both ends. Software only: cable and electrical timing are not modelled."""
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
@unittest.skipUnless((RESIDENT/'resident.elf').is_file(),'built resident required')
class Slot(unittest.TestCase):
    def run_slot(self,fifo,announced,ann_seq=100,valid=1):
        os.environ.setdefault('GBM_ARM_TOOLCHAIN','D:/Progettini')
        import cosim_stream,test_control
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR
        m=cosim_stream.Machine(RESIDENT);u=m.u
        m.pio=test_control.Machine(fifo)
        masks=[0]*13
        for b in announced:
            masks[b>>5]|=1<<(b&31);u.mem_write(m.symbol('hashes')+4*b,struct.pack('<I',(0x1000+b)^1))
        u.mem_write(m.symbol('announced'),struct.pack('<13I',*masks));u.mem_write(m.symbol('ann_seq'),struct.pack('<H',ann_seq))
        m.word(m.symbol('valid'),valid);m.word(m.symbol('feedback'),0)
        u.reg_write(UC_ARM_REG_R0,1234);u.reg_write(UC_ARM_REG_SP,0x03007f00);u.reg_write(UC_ARM_REG_LR,0x03007800)
        u.emu_start(m.symbol('control_slot')|1,0x03007800,count=4000000)
        m._pio_advance()
        left=set(b for b in range(416) if struct.unpack_from('<13I',u.mem_read(m.symbol('announced'),52))[b>>5]>>(b&31)&1)
        hashes={b:struct.unpack('<I',u.mem_read(m.symbol('hashes')+4*b,4))[0] for b in announced}
        return m,left,hashes
    def test_verdict_restores_known_blocks_only(self):
        announced=[9,10,40,41,200,392];known=[10,41,392,300]
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(100,known)),announced)
        self.assertEqual(left,{9,40,200})
        for b in announced:self.assertEqual(hashes[b],(0x1000+b)^(0 if b in known else 1))
        self.assertEqual(m.read32(m.symbol('feedback')),1);self.assertEqual(m.read32(m.symbol('valid')),1)
        self.assertEqual(m.contention,0);self.assertEqual(m.pio.direction,0);self.assertEqual(m.pio.stalled,0)
        self.assertLess(m.cycles/1232,40,'slot takes too many scanlines')
    def test_verdict_older_than_the_last_announcement_is_ignored(self):
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(99,[9,10])),[9,10],ann_seq=100)
        self.assertEqual(left,{9,10});self.assertEqual(m.contention,0)
        # sequence numbers wrap: 3 is newer than 65530
        m,left,hashes=self.run_slot(pio_words(448,False,verdict(3,[9,10])),[9,10],ann_seq=65530)
        self.assertEqual(left,set())
    def test_damaged_or_missing_verdict_is_ignored(self):
        m,left,_=self.run_slot(pio_words(448,False,verdict(100,[9,10],spoil=True)),[9,10])
        self.assertEqual(left,{9,10})
        m,left,_=self.run_slot(pio_words(448,False,[0xffff]*28),[9,10])
        self.assertEqual(left,{9,10});self.assertEqual(m.read32(m.symbol('feedback')),1)
    def test_resync_request_still_arrives(self):
        m,left,_=self.run_slot(pio_words(448,True,verdict(100,[9])),[9,10])
        self.assertEqual(m.read32(m.symbol('valid')),0);self.assertEqual(m.contention,0)
    def test_no_pico_answer_leaves_everything_alone(self):
        """Nothing drives SD (Pico 0.7 after its two bits, or no Pico): pulled high, check fails."""
        import test_control
        class Silent(test_control.Machine):
            def step(self,clock):pass
        os.environ.setdefault('GBM_ARM_TOOLCHAIN','D:/Progettini')
        m,left,_=self.run_slot([],[9,10]);self.assertEqual(left,{9,10})
if __name__=='__main__':unittest.main()
