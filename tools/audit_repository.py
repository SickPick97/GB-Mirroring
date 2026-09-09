"""Audit the staged file list and create a relocatable test copy."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
GIT=['git','-c','safe.directory='+str(ROOT).replace('\\','/')]

def main():
    names=subprocess.check_output(GIT+['ls-files','-z'],cwd=ROOT).decode().split('\0')
    names=[n for n in names if n]
    violations=[]
    for name in names:
        p=Path(name)
        if name.startswith(('PROGETTO AMICO/','analisi/','build/','downloads/','packages/')):
            violations.append(name)
        if p.suffix.lower() in ('.sav','.srm','.ss0','.ss1'):
            violations.append(name)
        if p.suffix.lower()=='.gba' and not name.startswith('dist/gbmirroring-'):
            violations.append(name)
        if p.suffix.lower() in ('.md','.py','.ps1','.json','.yml','.yaml','.txt'):
            text=(ROOT/name).read_text(encoding='utf-8-sig',errors='replace')
            if re.search(r'(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)',text):
                violations.append(name+' (credential pattern)')
    if violations: raise RuntimeError('Review files before commit: '+', '.join(violations))
    print('Audit OK:',len(names),'tracked files; no game files or credential patterns found.')

if __name__=='__main__':main()
