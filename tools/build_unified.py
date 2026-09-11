"""Rebuild both normal-mode artifacts; never touches attached hardware."""
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(*args): subprocess.run(list(args),cwd=ROOT,check=True)

if __name__=='__main__':
    cmake=shutil.which('cmake') or 'C:/Program Files/CMake/bin/cmake.exe'
    run(cmake,'-S','.', '-B','build/uvc-test','-G','Ninja',
        '-DCMAKE_MAKE_PROGRAM='+str(ROOT/'tools/ninja/ninja.exe').replace('\\','/'),'-DCMAKE_BUILD_TYPE=Release')
    run(cmake,'--build','build/uvc-test','--target','gbmirroring_unified','--parallel','4')
    run(sys.executable,'tools/make_uf2.py','build/uvc-test/gbmirroring_unified.bin','dist/gbmirroring-unified-v0.6.0.uf2')
    run(sys.executable,'tools/verify_unified.py')
