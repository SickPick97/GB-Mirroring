"""Reconstruct the supplied legacy Celio application, offline; never touches USB."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = ROOT / 'vendor/celio_legacy_source'
    metadata = json.loads((source / 'provenance.json').read_text())
    for name, expected in metadata['files'].items():
        assert hashlib.sha256((source / name).read_bytes()).hexdigest() == expected, name
    assert hashlib.sha256((ROOT / metadata['binary']).read_bytes()).hexdigest() == metadata['binary_sha256']
    destination = ROOT / 'build/legacy-celio'
    if destination.exists():
        raise SystemExit('Output already exists: build/legacy-celio. Preserve or move it before retrying.')
    with zipfile.ZipFile(source / 'upstream.zip') as archive:
        for member in archive.infolist():
            parts = Path(member.filename).parts[1:]
            if not parts:
                continue
            target = destination.joinpath(*parts).resolve()
            if destination.resolve() not in target.parents:
                raise ValueError('Unsafe archive path')
            if not member.is_dir():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    git = ['git', '-c', 'safe.directory=' + ROOT.as_posix(), 'apply',
           '--directory=build/legacy-celio']
    patch = str(source / 'modifications.patch')
    subprocess.run(git + ['--check', patch], cwd=ROOT, check=True)
    subprocess.run(git + [patch], cwd=ROOT, check=True)
    subprocess.run(git + ['--reverse', '--check', patch], cwd=ROOT, check=True)
    print('Verified: binary and source hashes; 11-file patch applied and reverse-checked. No firmware build or USB access.')

if __name__ == '__main__':
    main()
