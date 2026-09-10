"""Protocol fault tests plus actual ARM image execution with mocked GBA registers.

Unicorn tests CPU code, not the BIOS multiboot handshake, cable timing or USB.
Install optional development dependency into third_party/test-runtime.
"""
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from link_protocol import Parser, Measurement, crc, pattern, bmp

ROOT=Path(__file__).resolve().parents[1]

def packet(seq):
    data=[0xd123,1,0x601b,0,0,0,0]+[pattern(seq,i) for i in range(7,64)]
    words=[0xb17e,0x4d47,1,1,seq&65535,seq>>16,64]+data
    return words+[crc(words[2:])]

def parse(words):
    p=Parser(); result=[]
    for w in words:
        f=p.feed(w)
        if f: result.append(f)
    return p,result

class ProtocolTests(unittest.TestCase):
    def test_usb_profile_preserves_reads_and_failures(self):
        from usb_profile import ReadProfile,difference
        class Device:
            def read(self,ep,size,timeout):
                if timeout==0:raise TimeoutError('simulated')
                return bytes(range(size))
        proxy=ReadProfile(Device());before=proxy.snapshot()
        self.assertEqual(proxy.read(0x82,64,timeout=10),bytes(range(64)))
        proxy.read(0x81,2,timeout=10)
        with self.assertRaises(TimeoutError):proxy.read(0x82,64,timeout=0)
        result=difference(before,proxy.snapshot(),2)
        self.assertEqual((result['calls'],result['bytes'],result['failures']),(1,64,1))
        self.assertEqual(result['sizes'],{'64':1})
        self.assertEqual(result['bytes_s'],32)

    def test_gba_transfer_counter_wrap(self):
        stats=Measurement(0xd123)
        for seq,count in [(0,0xfffffff0),(1,56)]:
            data=[0xd123,0,0,count&65535,count>>16,0,0]+[pattern(seq,i) for i in range(7,64)]
            stats.accept((1,seq,data))
        result=stats.result(1,0)
        self.assertEqual(result['gba_transfer_counter_delta'],72)
        self.assertEqual(result['gba_expected_transfer_delta'],72)

    def test_scan_stops_at_first_fault_and_preserves_evidence(self):
        from link_bench import scan
        calls=[]
        def fake(link,timing,seconds,challenge):
            calls.append(timing)
            return dict(timing=timing,clean=timing>=500,crc_errors=int(timing<500))
        phases=scan(None,[1000,500,250,125],20,fake)
        self.assertEqual(calls,[1000,500,250])
        self.assertEqual(len(phases),3)
        self.assertEqual(phases[-1]['crc_errors'],1)

    def test_scan_completes_clean_schedule(self):
        from link_bench import scan
        phases=scan(None,[500,250,1],20,lambda link,t,s,c:dict(timing=t,clean=True))
        self.assertEqual([x['timing'] for x in phases],[500,250,1])

    def test_crc_known_vector(self):
        import binascii
        self.assertEqual(binascii.crc_hqx(b'123456789',0xffff),0x29b1)

    def test_loss_corruption_and_resync(self):
        for change in ('delete','flip','insert'):
            broken=packet(2)
            if change=='delete': del broken[35]
            elif change=='flip': broken[35]^=1
            else: broken.insert(35,0)
            p,frames=parse(packet(1)+broken+packet(3)+packet(4))
            self.assertEqual([f[1] for f in frames],[1,3,4])
            self.assertGreater(p.bad_crc,0)

    def test_duplicates_gaps_and_echo(self):
        _,frames=parse(packet(1)+packet(1)+packet(3)+packet(4)+packet(5))
        m=Measurement(0xd123)
        for f in frames: m.accept(f)
        r=m.result(10,0)
        self.assertFalse(r['clean'])
        self.assertEqual(r['duplicates'],1)
        self.assertEqual(r['missing_packets'],1)
        self.assertEqual(r['challenge_echoes'],5)

    def test_clean_and_wrong_challenge(self):
        _,frames=parse(sum([packet(i) for i in range(8)],[]))
        for challenge,expected in [(0xd123,True),(0xd124,False)]:
            m=Measurement(challenge)
            for f in frames: m.accept(f)
            self.assertEqual(m.result(10,0)['clean'],expected)

    def test_bmp_size_and_colors(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.bmp'
            bmp(path,[0x001f]*38400)
            b=path.read_bytes()
            self.assertEqual(len(b),115254)
            self.assertEqual(b[54:57],b'\0\0\xff')
            self.assertEqual(struct.unpack_from('<ii',b,18),(240,160))
            with self.assertRaises(ValueError): bmp(path,[0])

class ArmImageTests(unittest.TestCase):
    def test_multiboot_sender_with_built_image(self):
        sys.dont_write_bytecode=True
        sys.path.insert(0,str(ROOT/'vendor/celio_transport'))
        from mb_multi import Multiboot, SlaveSimulato, LinkSimulato
        rom=(ROOT/'dist/gbmirroring-link-test-v0.2.0.gba').read_bytes()
        slave=SlaveSimulato(rom)
        result=Multiboot(LinkSimulato(slave),verbose=False,timing_fast=3700,
                         timing_wait=129630,max_attempts=1).run(rom)
        self.assertEqual(result['byte'],len(rom))
        self.assertEqual(slave.verifica(),[])

    def test_compiled_rom_packets_and_vram_capture(self):
        sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
        from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
        from unicorn.arm_const import UC_ARM_REG_PC
        uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        for address,size in [(0x02000000,0x40000),(0x03000000,0x8000),
                             (0x04000000,0x1000),(0x06000000,0x18000)]:
            uc.mem_map(address,size)
        rom=(ROOT/'dist/gbmirroring-link-test-v0.2.0.gba').read_bytes()
        uc.mem_write(0x02000000,rom)
        uc.mem_write(0x04000130,struct.pack('<H',0x03fe))
        outgoing=[]
        state={'ready':False,'capture':False}
        target=72*(2+600+2)

        def read_hook(machine,access,address,size,value,user):
            if address!=0x04000202: return
            if len(outgoing)>=target:
                machine.emu_stop(); return
            self.assertTrue(state['ready'])
            command=0xd123
            if len(outgoing)==144 and not state['capture']:
                command=0xc001
                state['capture']=True
                state['vram']=bytes(machine.mem_read(0x06000000,76800))
            machine.mem_write(0x04000120,struct.pack('<H',command))
            machine.mem_write(0x04000202,b'\x80\0')

        def write_hook(machine,access,address,size,value,user):
            if address==0x04000128:
                self.assertEqual(value,0x6003)
                state['ready']=True
            elif address==0x0400012a:
                outgoing.append(value)

        uc.hook_add(UC_HOOK_MEM_READ,read_hook,begin=0x04000202,end=0x04000203)
        uc.hook_add(UC_HOOK_MEM_WRITE,write_hook,begin=0x04000128,end=0x0400012b)
        uc.emu_start(0x020000c0,0,count=30000000)
        self.assertEqual(len(outgoing),target,f'CPU stopped at {uc.reg_read(UC_ARM_REG_PC):08x}')
        parser,frames=parse(outgoing)
        self.assertEqual(parser.bad_crc,0)
        self.assertEqual(len(frames),604)
        diagnostics=[f for f in frames if f[0]==1]
        self.assertEqual([f[1] for f in diagnostics],[0,1,2,3])
        for _,seq,data in diagnostics:
            self.assertEqual(data[1],1)
            for i in range(7,64): self.assertEqual(data[i],pattern(seq,i))
        self.assertEqual(diagnostics[1][2][0],0xd123)
        shots=[f for f in frames if f[0]==2]
        self.assertEqual([f[1] for f in shots],list(range(600)))
        actual=struct.pack('<38400H',*[v for f in shots for v in f[2]])
        self.assertEqual(actual,state['vram'])
        # Generated directly from bytes emitted by the compiled ARM program.
        preview=ROOT/'build/link-test/emulated-vram.bmp'
        bmp(preview,list(struct.unpack('<38400H',actual)))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (ROOT/'dist/verifica-link-software.json').write_text(json.dumps(dict(
        passed=result.wasSuccessful(),tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),
        scope='Protocol fault injection and compiled ARM execution with mocked IO; no physical timing or BIOS test'
    ),indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
