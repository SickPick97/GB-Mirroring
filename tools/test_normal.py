"""Execute both normal-mode sender phases and independently check every packet."""
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'third_party/test-runtime'))
from normal_report import build_report

def pattern(seq,i):
    if i<8: return [0,0xffffffff,0xaaaaaaaa,0x55555555,0x80000000,1,65535,0xffff0000][i]
    x=(seq^(0x9e3779b9*(i+1)))&0xffffffff
    x^=(x<<13)&0xffffffff;x^=x>>17;x^=(x<<5)&0xffffffff
    return x

class NormalTests(unittest.TestCase):
    def test_actual_arm_sender_both_rates(self):
        from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
        uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        for a,s in [(0x02000000,0x40000),(0x03000000,0x8000),(0x04000000,0x1000),(0x06000000,0x18000)]:uc.mem_map(a,s)
        uc.mem_write(0x02000000,(ROOT/'dist/gbmirroring-normal-test-v0.3.0.gba').read_bytes())
        state=dict(ends=0,key=0,words=[],data=0,screen=[],modes=set(),begins=0)
        def read(machine,access,address,size,value,user):
            if address==0x04000128:
                value=struct.unpack('<H',machine.mem_read(address,2))[0]&~0x80
                machine.mem_write(address,struct.pack('<H',value))
            elif address==0x04000130:
                if state['ends']==2:machine.emu_stop();return
                mask=1 if state['ends']==0 else 2
                step=state['key']%3;state['key']+=1
                machine.mem_write(address,struct.pack('<H',0x3ff^mask if step==1 else 0x3ff))
        def write(machine,access,address,size,value,user):
            if address!=0x04000128 or not value&0x80:return
            state['modes'].add(value)
            state['words'].append(struct.unpack('<I',machine.mem_read(0x04000120,4))[0])
            if len(state['words'])!=264:return
            w=state['words'];state['words']=[]
            self.assertEqual(w[:3],[0x334d4247,0xc35aa53c,3])
            self.assertEqual(w[6],256)
            self.assertEqual(w[-1],zlib.crc32(struct.pack('<261I',*w[2:-1])))
            self.assertEqual(w[4],262144 if state['ends']==0 else 2097152)
            if w[3]==1:
                self.assertEqual(w[7],1024);state['begins']+=1
                state['vram']=bytes(machine.mem_read(0x06000000,76800))
            elif w[3]==2:
                self.assertEqual(w[5],state['data']%1024)
                self.assertEqual(w[7:-1],[pattern(w[5],i) for i in range(256)])
                state['data']+=1
            elif w[3]==3:
                self.assertEqual(w[5],len(state['screen']))
                state['screen'].append(struct.pack('<256I',*w[7:-1]))
            elif w[3]==4:
                self.assertEqual(w[5],1024)
                self.assertEqual(b''.join(state['screen']),state['vram'])
                state['screen']=[];state['ends']+=1
        uc.hook_add(UC_HOOK_MEM_READ,read,begin=0x04000128,end=0x04000131)
        uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=0x04000128,end=0x04000129)
        uc.emu_start(0x020000c0,0,count=200000000)
        self.assertEqual(state['ends'],2)
        self.assertEqual(state['data'],2048)
        self.assertEqual(state['begins'],2)
        self.assertEqual(state['modes'],{0x1089,0x108b})

    def test_pio_encoded_sampling(self):
        # Execute the three actual PIO instruction encodings against ideal edges.
        import re
        source=(ROOT/'firmware/normal-test/rx_program.h').read_text()
        code=[int(x,16) for x in re.search(r'normal_rx_instructions\[\]=\{([^}]+)',source)[1].split(',')]
        self.assertEqual(code,[0x2000,0x2080,0x4001])
        expected=[0,0xffffffff,0x12345678,0x80000001,0xa55aa55a]
        samples=[]
        for word in expected:
            for bit in range(31,-1,-1):
                samples.extend([(0,(word>>bit)&1)]*5+[(1,(word>>bit)&1)]*5)
        pc=0;isr=0;bits=0;received=[]
        for clock,data in samples:
            instruction=code[pc]
            if instruction>>13==1:
                if clock!=((instruction>>7)&1):continue
            else:
                isr=((isr<<1)|data)&0xffffffff;bits+=1
                if bits==32:received.append(isr);bits=0
            pc=(pc+1)%3
        self.assertEqual(received,expected)

    def report_fixture(self,folder,missing=False,bad_crc=False):
        (folder/'host.json').write_text(json.dumps(dict(completed=True)))
        lines=[]
        pixels=bytes(76800)
        for rate in (262144,2097152):
            lines.append(dict(event='result',rate=rate,clean=True,elapsed_us=1000000,
                payload_bytes=1048576,screen_blocks=75,screen_crc32=zlib.crc32(pixels)^(1 if bad_crc else 0)))
            for block in range(299 if missing else 300):
                lines.append(dict(event='image',rate=rate,block=block,hex=bytes(256).hex()))
            lines.append(dict(event='phase_done'))
        (folder/'usb.jsonl').write_text('\n'.join(json.dumps(l) for l in lines))

    def test_complete_report(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);self.report_fixture(folder)
            r=build_report(folder)
            self.assertEqual(r['status'],'PASS')
            self.assertEqual(len(list(folder.glob('*.bmp'))),2)

    def test_incomplete_or_corrupt_image_is_not_saved(self):
        for missing,bad_crc in [(True,False),(False,True)]:
            with tempfile.TemporaryDirectory() as d:
                folder=Path(d);self.report_fixture(folder,missing,bad_crc)
                self.assertNotEqual(build_report(folder)['status'],'PASS')
                self.assertEqual(list(folder.glob('*.bmp')),[])

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NormalTests))
    (ROOT/'dist/verifica-normal-software.json').write_text(json.dumps(dict(passed=result.wasSuccessful(),
        tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),
        scope='Actual GBA ARM code with mocked IO, ideal PIO edges, report faults; no electrical or USB hardware test'),indent=2)+'\n')
    sys.exit(not result.wasSuccessful())
