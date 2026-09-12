"""Run existing ARM protocol/codec checks on the isolated budget candidate."""
import shutil,tempfile,unittest
from pathlib import Path
import test_emerald,test_graphics_lz
ROOT=Path(__file__).resolve().parents[1]

def main():
    with tempfile.TemporaryDirectory(prefix='gbm-candidate-') as directory:
        root=Path(directory);target=root/'build/emerald';target.mkdir(parents=True)
        for name in ('resident.elf','resident.bin'):
            shutil.copyfile(ROOT/'build/emerald-next'/name,target/name)
        originals=(test_emerald.ROOT,test_graphics_lz.ROOT)
        try:
            test_emerald.ROOT=root;test_graphics_lz.ROOT=root
            suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m)
                                     for m in (test_emerald,test_graphics_lz))
            result=unittest.TextTestRunner(verbosity=2).run(suite)
        finally:test_emerald.ROOT,test_graphics_lz.ROOT=originals
    return not result.wasSuccessful()

if __name__=='__main__':raise SystemExit(main())
