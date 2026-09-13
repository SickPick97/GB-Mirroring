"""Local integration test. ROM/save are read only and never included in reports."""
import argparse,struct,json,subprocess,shutil,time
from pathlib import Path
from mgba_headless import Core
from graphics_renderer import Renderer
from graphics_stream import GraphicsParser,graphics_from_state,encode_snapshot
ROOT=Path(__file__).resolve().parents[1]
DLL=ROOT/'runtime/mgba/mgba_libretro.dll'
def boot_test(rom,mutate=False,version='0.8.0'):
 if mutate:
  rom=bytearray(rom);rom[0xa0]^=1;rom=bytes(rom)
 c=Core(DLL,rom);c.run(3);s=c.state();b=(ROOT/('dist/gbmirroring-emerald-v'+version+'.gba')).read_bytes();s[0x21000:0x21000+len(b)]=b
 pc=0x020000e0;struct.pack_into('<I',s,0x5c,pc+4);struct.pack_into('<I',s,0x60,0xdf);struct.pack_into('<II',s,0x2f8,*struct.unpack_from('<II',b,0xe0));struct.pack_into('<I',s,0x318,pc)
 c.restore(s);c.run(10);c.run(3,1<<3);c.run(360);s=c.state();irq=struct.unpack_from('<I',s,0x20ffc)[0];c.close()
 assert (irq==0x0203cf80)!=mutate
 return True

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rom',required=True);ap.add_argument('--save',required=True);args=ap.parse_args()
 rom=Path(args.rom).read_bytes();save=Path(args.save).read_bytes();out=ROOT/'build/emerald';out.mkdir(exist_ok=True)
 report=dict(scope='Software only; no hardware USB, multiboot electrical timing, or full-game certification',boot=boot_test(rom),modified_boot_signature_rejected=boot_test(rom,True))
 c=Core(DLL,rom);c.run();c.load_save_copy(save);c.run(900)
 for _ in range(4):c.run(3,1<<3);c.run(90);c.run(3,1<<8);c.run(120)
 for _ in range(3):c.run(3,1);c.run(60)
 field=c.state();shutil.copyfile(DLL,out/'renderer-test.dll');renderer=Renderer(out/'renderer-test.dll');parser=GraphicsParser(renderer);previous=None;records=[]
 for seq in range(90):
  keys=(1<<7) if seq<30 else ((1<<3) if seq==35 else ((1<<8) if seq==50 else 0))
  c.run(6,keys);gfx=graphics_from_state(c.state());wire=encode_snapshot(seq,seq*6,gfx,previous);start=time.perf_counter();frames=parser.feed(wire)
  reference=struct.pack('<38400H',*c.rgb555());different=sum(a!=b for a,b in zip(struct.unpack('<38400H',reference),struct.unpack('<38400H',frames[0][1])))
  records.append(dict(wire_bytes=len(wire),different_pixels=different,pc_seconds=time.perf_counter()-start));previous=gfx
 renderer.close();assert all(r['different_pixels']==0 for r in records)
 report['graphics']=dict(frames=90,exact_frames=90,mean_delta_wire_bytes=sum(r['wire_bytes'] for r in records[1:])/89,mean_pc_render_seconds=sum(r['pc_seconds'] for r in records)/90,scope='Repeatable movement/menu sequence from local save; not all battles/scanline effects')
 tool=sorted(Path('C:/Program Files (x86)/Arm GNU Toolchain arm-none-eabi').glob('*/bin/arm-none-eabi-nm.exe'))[-1]
 nm=subprocess.check_output([str(tool),'-n',str(out/'resident.elf')],text=True);symbols={n:int(a,16) for a,k,n in (line.split() for line in nm.splitlines() if len(line.split())==3)}
 s=bytearray(field);p=bytearray((out/'resident.bin').read_bytes());struct.pack_into('<I',p,4,struct.unpack_from('<I',s,0x20ffc)[0]);s[0x5df80:0x60c00]=bytes(0x2c80);s[0x5df80:0x5df80+len(p)]=p;struct.pack_into('<I',s,0x20ffc,0x203cf80);c.restore(s);c.run(3,(1<<2)|(1<<10)|(1<<11));c.run(480)
 def counts():
  s=c.state();return (struct.unpack_from('<I',s,0x21000+symbols['sequence']-0x02000000)[0],struct.unpack_from('<I',s,0x1b2e0)[0])
 a=counts();c.run(600);b=counts();c.run(600,1<<7);moving=counts();c.close();assert b[0]>a[0] and b[1]>a[1]
 report['timing']=dict(emulated_frames=600,captures=b[0]-a[0],game_vblanks=b[1]-a[1],capture_fps=(b[0]-a[0])*(16777216/280896)/600,game_vblanks_per_second=(b[1]-a[1])*(16777216/280896)/600,scope='Static field in mGBA; not physical performance')
 report['moving_timing']=dict(emulated_frames=600,captures=moving[0]-b[0],capture_fps=(moving[0]-b[0])*(16777216/280896)/600,game_vblanks=moving[1]-b[1],scope='Held directional input in mGBA; VBlank counts do not prove gameplay or audio smoothness')
 (out/'integration-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
