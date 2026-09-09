"""Rebuild both normal-mode artifacts; never touches attached hardware."""
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(*args): subprocess.run(list(args),cwd=ROOT,check=True)

if __name__=='__main__':
    cmake=shutil.which('cmake') or 'C:/Program Files/CMake/bin/cmake.exe'
    run(sys.executable,'tools/build_link_test.py','--normal')
    run(cmake,'-S','.', '-B','build/uvc-test','-G','Ninja',
        '-DCMAKE_MAKE_PROGRAM='+str(ROOT/'tools/ninja/ninja.exe').replace('\\','/'),'-DCMAKE_BUILD_TYPE=Release')
    run(cmake,'--build','build/uvc-test','--target','gbmirroring_normal_test','--parallel','4')
    run(sys.executable,'tools/make_uf2.py','build/uvc-test/gbmirroring_normal_test.bin','dist/gbmirroring-normal-test-v0.3.2.uf2')
    run(sys.executable,'tools/verify_normal.py')
