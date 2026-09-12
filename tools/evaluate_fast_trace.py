"""Read-only development trace: pixel equality and resource stream lower bounds.
Local commercial ROM/state are never copied into the resulting report.
"""
import argparse,json,struct,time,hashlib,statistics
from pathlib import Path
from mgba_headless import Core
from graphics_stream import graphics_from_state
from native_renderer import Renderer
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rom',required=True);ap.add_argument('--state',required=True);args=ap.parse_args()
 from graphics_renderer import Renderer as Legacy
 c=Core(ROOT/'runtime/mgba/mgba_libretro.dll',Path(args.rom).read_bytes());c.run(1);c.restore(Path(args.state).read_bytes());r=Renderer();old=Legacy(ROOT/'build/emerald/renderer-test.dll');previous=None;known=set();times=[];records=[];different=0;legacy_diff=0;legacy_samples=0
 try:
  for frame in range(900):
   keys=(1<<7) if frame<300 else ((1<<3) if frame==320 else ((1<<8) if frame==500 else 0))
   c.run(1,keys);gfx=graphics_from_state(c.state());start=time.perf_counter();pixels=r.render(gfx);times.append((time.perf_counter()-start)*1000)
   expected=struct.pack('<38400H',*c.rgb555());different+=pixels!=expected
   if frame%30==0:
    legacy_samples+=1;legacy=old.render(gfx);legacy_diff+=legacy!=pixels
    if legacy!=pixels and legacy_diff==1:
     from link_protocol import bmp
     bmp(ROOT/'build/native-mismatch.bmp',struct.unpack('<38400H',pixels));bmp(ROOT/'build/legacy-mismatch.bmp',struct.unpack('<38400H',legacy));(ROOT/'build/mismatch-graphics.bin').write_bytes(gfx)
   changed=miss=hot=0
   if previous:
    hot=sum(gfx[i:i+2]!=previous[i:i+2] for i in range(0,2304,2))
    for pos in range(2304,len(gfx),256):
     if gfx[pos:pos+256]==previous[pos:pos+256]:continue
     changed+=1;key=hashlib.sha256(gfx[pos:pos+256]).digest()
     if key not in known:miss+=1;known.add(key)
   else:
    known.update(hashlib.sha256(gfx[pos:pos+256]).digest() for pos in range(2304,len(gfx),256))
   records.append(dict(frame=frame,changed_blocks=changed,new_blocks=miss,hot_words_changed=hot,estimate_bytes=16+hot*4+changed*10+miss*256));previous=gfx
 finally:r.close();old.close();c.close()
 report=dict(scope='Emulated coherent snapshots every frame. Resource estimate is not implemented transport or hardware FPS.',frames=len(records),pixel_mismatch_frames=different,legacy_samples=legacy_samples,legacy_mismatch_frames=legacy_diff,native_ms_median=statistics.median(times),native_ms_p95=sorted(times)[int(len(times)*.95)],estimated_bytes_per_second=statistics.mean(x['estimate_bytes'] for x in records[1:])*59.7275,records=records)
 (ROOT/'build/fast-trace.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2));return int(different!=0)
if __name__=='__main__':raise SystemExit(main())
