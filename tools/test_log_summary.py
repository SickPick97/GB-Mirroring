import sys,json,zipfile,io,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import log_summary
def row(i,peak=30,pending=0,frame=None,**gba):
 g=dict(peak_work_scanlines=peak,previous_words=40,pending_blocks=pending,game_frame=i if frame is None else frame,block_codecs={'5':1,'10':2},cadence=1,incomplete=False,keyframe=False,raster_dma_active=False)
 g.update(gba);return dict(seconds=i/60,sequence=i,gba=g)
class Tests(unittest.TestCase):
 def test_summary_counts_long_ticks_and_gaps(self):
  rows=[row(i) for i in range(20)]
  for i in range(5,9):rows[i]['gba']['peak_work_scanlines']=210
  rows[12]['gba']['game_frame']=40;rows[13]['gba']['game_frame']=41
  rows[3]['gba']['incomplete']=True;rows[4]['gba']['unknown_scene']=True
  s=log_summary.summarize(rows,dict(valid_frames=20,secret='no'))
  self.assertEqual(s['ticks'],20);self.assertEqual(s['tick_lines']['over_150'],4);self.assertEqual(s['longest_run_of_ticks_over_150_lines'],4)
  self.assertEqual(s['forced_releases'],1);self.assertEqual(s['unknown_scene_ticks'],1);self.assertGreaterEqual(s['game_frame_gaps']['of_6_or_more'],1)
  self.assertEqual(s['record_types'],{'5':20,'10':40});self.assertEqual(s['pc'],dict(valid_frames=20))
 def test_bundle_is_one_zip_with_every_log(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);(d/'frames.jsonl').write_text(''.join(json.dumps(row(i))+'\n' for i in range(5))+'{"cut',encoding='utf-8')
   (d/'multiboot.json').write_text('{}');(d/'console.txt').write_text('avvio\n')
   data,summary=log_summary.bundle(d,d/'frames.jsonl',dict(status='X'),d/'console.txt',b'\x01\x02',b'BM')
   z=zipfile.ZipFile(io.BytesIO(data));names=set(z.namelist())
   self.assertTrue({'LEGGIMI.txt','riepilogo.json','rapporto.json','frames.jsonl','console.txt','usb-tail.bin','ultimo-frame.bmp','multiboot.json','sistema.json'}<=names)
   self.assertEqual(summary['ticks'],5);self.assertEqual(json.loads(z.read('riepilogo.json'))['ticks'],5)
 def test_empty_session_still_bundles(self):
  with tempfile.TemporaryDirectory() as d:
   data,summary=log_summary.bundle(d,Path(d)/'missing.jsonl',{})
   self.assertEqual(summary,dict(ticks=0));self.assertIn('LEGGIMI.txt',zipfile.ZipFile(io.BytesIO(data)).namelist())
if __name__=='__main__':unittest.main()
