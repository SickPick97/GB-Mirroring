"""Readable summary and single-file bundle of a capture session (frames.jsonl + report + console)."""
import io,json,zipfile,platform,datetime
from pathlib import Path
def load_frames(path):
 rows=[]
 try:
  with Path(path).open(encoding='utf-8') as f:
   for line in f:
    try:rows.append(json.loads(line))
    except ValueError:pass  # a line cut by a flush in progress
 except OSError:pass
 return rows
def summarize(rows,report=None):
 """Numbers that matter for tick cost, skipped ticks and scene loads; no image content."""
 gba=[r.get('gba',{}) for r in rows if r.get('gba')]
 out=dict(ticks=len(gba))
 if not gba:return out
 peaks=[g.get('peak_work_scanlines',0) for g in gba];words=[g.get('previous_words',0) for g in gba]
 pending=[g.get('pending_blocks',0) for g in gba]
 def pct(v,p):s=sorted(v);return s[min(len(s)-1,int(len(s)*p))]
 out.update(seconds=round(rows[-1].get('seconds',0)-rows[0].get('seconds',0),1),
  version=gba[-1].get('version'),
  tick_lines=dict(p50=pct(peaks,.5),p95=pct(peaks,.95),p99=pct(peaks,.99),max=max(peaks),over_100=sum(1 for p in peaks if p>100),over_150=sum(1 for p in peaks if p>150)),
  words=dict(mean=round(sum(words)/len(words),1),max=max(words)),
  pending=dict(max=max(pending),ticks_over_40=sum(1 for p in pending if p>40)),
  forced_releases=sum(1 for g in gba if g.get('incomplete')),keyframes=sum(1 for g in gba if g.get('keyframe')),
  raster_dma_ticks=sum(1 for g in gba if g.get('raster_dma_active')),
  unknown_scene_ticks=sum(1 for g in gba if g.get('unknown_scene')),
  ticks_with_hblank_or_vcount_irq=sum(1 for g in gba if g.get('interrupt_enable',0)&6),
  interrupt_enable_seen=sorted({g.get('interrupt_enable',0) for g in gba}),
  callback_ids_seen=sorted({g.get('callback_id',0) for g in gba}),
  ticks_after_skips=sum(1 for g in gba if g.get('skipped_ticks')),
  cadence_changes=sum(1 for a,b in zip(gba,gba[1:]) if a.get('cadence')!=b.get('cadence')))
 frames=[g.get('game_frame',0) for g in gba]
 gaps=[b-a for a,b in zip(frames,frames[1:])]
 out['game_frame_gaps']=dict(of_2=sum(1 for g in gaps if g==2),of_3_to_5=sum(1 for g in gaps if 3<=g<=5),of_6_or_more=sum(1 for g in gaps if g>=6),largest=max(gaps,default=0))
 seqs=[r.get('sequence',0) for r in rows]
 out['sequence_jumps']=sum(1 for a,b in zip(seqs,seqs[1:]) if b-a!=1)
 codecs={}
 for g in gba:
  for k,v in (g.get('block_codecs') or {}).items():codecs[k]=codecs.get(k,0)+v
 out['record_types']=codecs
 # runs of very long ticks: the pattern that delays the game's own VBlank
 longest=run=0
 for p in peaks:
  run=run+1 if p>150 else 0;longest=max(longest,run)
 out['longest_run_of_ticks_over_150_lines']=longest
 if report:
  keep=('valid_frames','sequence_gaps','bit_resyncs','crc_errors','discarded_bytes','usb_queue_peak_lag_ms','browser','render_peak_ms','status','error','elapsed_seconds')
  out['pc']={k:report[k] for k in keep if k in report}
 return out
def bundle(folder,rows_path,report,console_path=None,raw_tail=b'',last_bmp=None,resident='',notes=''):
 """Return zip bytes with everything needed to diagnose a session."""
 rows=load_frames(rows_path);summary=summarize(rows,report)
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.writestr('LEGGIMI.txt','GBMirroring - log della sessione\n\nUn solo file con tutto: riepilogo.json (numeri chiave), rapporto.json (stato del PC), frames.jsonl (un record per tick),\nconsole.txt (uscita del programma di avvio), usb-tail.bin (ultimi byte grezzi), ultimo-frame.bmp.\nNon contiene ROM, salvataggi o credenziali. Cartella sessione: %s\nGenerato: %s\nNote: %s\n'%(Path(folder).name,datetime.datetime.now().isoformat(timespec='seconds'),notes))
  z.writestr('riepilogo.json',json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
  z.writestr('rapporto.json',json.dumps(report,indent=2,ensure_ascii=False)+'\n')
  z.writestr('sistema.json',json.dumps(dict(python=platform.python_version(),os=platform.platform(),residente=resident),indent=2)+'\n')
  try:z.write(rows_path,'frames.jsonl')
  except OSError:pass
  for name in ('multiboot.json',):
   try:z.write(Path(folder)/name,name)
   except OSError:pass
  if console_path:
   try:z.write(console_path,'console.txt')
   except OSError:pass
  if raw_tail:z.writestr('usb-tail.bin',bytes(raw_tail))
  if last_bmp:z.writestr('ultimo-frame.bmp',last_bmp)
 return buf.getvalue(),summary
