"""Rebuild both normal-mode artifacts; never touches attached hardware."""
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(*args): subprocess.run(list(args),cwd=ROOT,check=True)

if __name__=='__main__':
    run(sys.executable,'tools/build_sd_gba.py')
    cmake=shutil.which('cmake') or 'C:/Program Files/CMake/bin/cmake.exe'
    run(cmake,'-S','.', '-B','build/uvc-test','-G','Ninja',
        '-DCMAKE_MAKE_PROGRAM='+str(ROOT/'tools/ninja/ninja.exe').replace('\\','/'),'-DCMAKE_BUILD_TYPE=Release')
    run(cmake,'--build','build/uvc-test','--target','gbmirroring_sd_video','--parallel','4')
    run(sys.executable,'tools/make_uf2.py','build/uvc-test/gbmirroring_sd_video.bin','dist/gbmirroring-sd-video-v0.4.0.uf2')
    run(sys.executable,'tools/verify_sd_pico.py')
