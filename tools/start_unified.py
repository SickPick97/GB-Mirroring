"""One entry point for boot and capture; reports belong to the same session."""
import sys,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
from link_bench import Log
from sd_video_viewer import main
if __name__=='__main__':
 folder=ROOT/'dist/emerald-reports';folder.mkdir(parents=True,exist_ok=True)
 log_path=folder/('avvio-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.txt')
 with log_path.open('w',encoding='utf-8') as f:
  original=sys.stdout;sys.stdout=Log(original,f)
  try:
   from check_portable import main as check
   check()
   print('Pico: firmware UNIFIED 0.7.0. Cavo invariato. Nessun cambio UF2 durante la sessione.')
   answer=input('INVIO per multiboot 0.10.0 (GBA acceso SENZA cartuccia); R per riprendere; B per la baseline 0.8.0: ').strip().lower()
   if answer not in ('','r','b'):raise SystemExit('Scelta non riconosciuta; nessun trasferimento avviato.')
   result=main(emerald=True,unified=True,resume=answer=='r',log_path=log_path,baseline=answer=='b')
  finally:sys.stdout=original
 sys.exit(result)
