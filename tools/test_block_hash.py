"""The resident's ARM block hash (fast.S hash_begin) and the PC's stream_hash must agree, and must tell apart blocks
whose two 128-byte halves are swapped (0.12.x could not: menus showed stale tiles for many frames)."""
import os,random,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'build/pylib'))
from stream_parser import stream_hash
RESIDENT=ROOT/os.environ.get('GBM_RESIDENT','build/emerald-stream')
class PythonHash(unittest.TestCase):
    def test_swapped_halves_and_shifted_words_differ(self):
        a=bytes(range(128));b=bytes(range(128,256))
        self.assertNotEqual(stream_hash(a+b),stream_hash(b+a))
        rng=random.Random(1);tile=bytes(rng.getrandbits(8) for _ in range(32))
        blocks={stream_hash(bytes(tile[(i*4)%32:]+tile[:(i*4)%32])*8) for i in range(8)}
        self.assertEqual(len(blocks),8)
        # seven rows of a solid colour and one empty row against eight rows of that colour (hashed equal in 0.13 drafts)
        solid=b''*32
        self.assertNotEqual(stream_hash(solid*7+bytes(32)),stream_hash(solid*8))
        self.assertEqual(len({stream_hash(bytes([c])*32*k+bytes(256-32*k)) for c in (0x11,0x22,0xff) for k in range(9)}),25)
@unittest.skipUnless((RESIDENT/'resident.elf').is_file(),'built resident required')
class ArmHash(unittest.TestCase):
    def test_arm_and_python_agree(self):
        os.environ.setdefault('GBM_ARM_TOOLCHAIN','D:/Progettini')
        import cosim_stream
        from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR
        m=cosim_stream.Machine(RESIDENT);rng=random.Random(7)
        cases=[bytes(rng.getrandbits(8) for _ in range(256)) for _ in range(12)]+[bytes(range(128))*2,bytes(256),bytes(range(128,256))+bytes(range(128))]
        for data in cases:
            m.u.mem_write(0x06000000,data)
            m.u.reg_write(UC_ARM_REG_R0,0x06000000);m.u.reg_write(UC_ARM_REG_R1,0x03007000)
            m.u.reg_write(UC_ARM_REG_SP,0x03007f00);m.u.reg_write(UC_ARM_REG_LR,0x03007800)
            m.u.emu_start(m.symbol('hash_begin'),0x03007800,count=100000)
            self.assertEqual(struct.unpack('<2I',m.u.mem_read(0x03007000,8)),stream_hash(data))
if __name__=='__main__':unittest.main()
