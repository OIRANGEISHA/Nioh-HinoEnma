"""Run the frozen portable70 and Beta5.3.1 proofs without game inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import unittest

from test_menu_preview_portable_integration import PortableTests,LAYOUTS,ROOT
from test_menu_preview_reload_portable import ReloadTests

SOURCE_SHA='44012d3a4bb44f578bb1eae128afaaa8eee8a11b0c595a9289501744d9b66e85'
TEST_SHA='40b416b758749de4e03d07a3a696e4fb4691f2c33653255244231601c537fa00'
RELOAD_FILES={
    'tools/menu_preview_reload_portable.py':'fb133e8a9503a3b1ba22d21188864e7272ee636aa1d4485c2ac25cc810f2c3c8',
    'tools/menu_preview_reload_sources.py':'57762edc987334b52cc6533888e61a6ed99ec77e52154b38cf0665528958c275',
    'tools/menu_preview_aura_source.py':'9e7d75241be7a1cb3631adec46f98c352360f081573cde6787df6696629c46c3',
    'tools/test_menu_preview_reload_portable.py':'db86a147c4a0647a1a1ecdd0ba7d32df977a23e52dbf3d8bf84026389de1be71'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(report=None):
    source=ROOT/'tools/menu_preview_portable_integration.py'
    test=ROOT/'tools/test_menu_preview_portable_integration.py'
    if digest(source)!=SOURCE_SHA or digest(test)!=TEST_SHA:
        raise ValueError('Frozen portable source/test hashes changed')
    if any(digest(ROOT/name)!=value for name,value in RELOAD_FILES.items()):
        raise ValueError('Reviewed portable reload source/test hashes changed')
    PortableTests.comparisons=PortableTests.cpu_comparisons=0
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(PortableTests))
    if (not result.wasSuccessful() or result.testsRun!=25 or PortableTests.comparisons!=2490
            or PortableTests.cpu_comparisons!=10005 or len(LAYOUTS)!=12):
        raise ValueError('Complete frozen portable70 proof required: '+stream.getvalue())
    ReloadTests.byte_comparisons=ReloadTests.cpu_comparisons=0
    current=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReloadTests))
    if (not current.wasSuccessful() or current.testsRun!=16 or ReloadTests.byte_comparisons!=1790
            or ReloadTests.cpu_comparisons!=5875):
        raise ValueError('Complete portable71 reload proof required: '+stream.getvalue())
    receipt=dict(success=True,game_access=False,tests_run=result.testsRun+current.testsRun,
        byte_comparisons=PortableTests.comparisons+ReloadTests.byte_comparisons,
        cpu_comparisons=PortableTests.cpu_comparisons+ReloadTests.cpu_comparisons,
        legacy_tests=25,reload_tests=16,reload_source_files=RELOAD_FILES,
        aslr_layouts=len(LAYOUTS),source_sha256=digest(source),test_sha256=digest(test),
        profile_sha256=digest(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=digest(ROOT/'launcher/Profile.generated.cs'),
        verifier_sha256=digest(Path(__file__)))
    if report is not None:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.report),indent=2))
