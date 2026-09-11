"""Build current GBA sender and test it; Pico 0.4.0 is unchanged."""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 for script in ('build_sd_gba.py','test_sd_video.py'):
  subprocess.run([sys.executable,str(ROOT/'tools'/script)],cwd=ROOT,check=True)
