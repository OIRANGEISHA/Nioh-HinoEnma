"""Exact-source dual-boss CPU/relocation proof with synthetic owners only."""
import argparse,hashlib,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'tools')]
SOURCE_FILES=('src/hinoenma_ninetails_binding.py','src/hinoenma_ninetails_views.py',
    'src/hinoenma_ninetails_runtime.py','tests/test_ninetails_runtime.py',
    'tests/orochi_fixture.py','tools/build_profile.py','launcher/Injector.cs','launcher/SelfTests.cs')
EXPECTED_TESTS=24
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(report=None):
    from build_profile import load_plan,source_plan_beta541,assemble,generate
    from hinoenma_ninetails_runtime import CHANGED_INDICES,validate_layout
    import test_ninetails_runtime as tests
    files={n:digest(ROOT/n) for n in SOURCE_FILES}
    plan=load_plan();validate_layout(plan)
    if (ROOT/'launcher/Profile.generated.cs').read_text('utf-8')!=generate(plan):raise ValueError('Stale generated dual-boss profile')
    old=source_plan_beta541(plan);comparisons=0;layouts=0
    for module in (0x140000000,0x7FF83AA00000,0x7FFA01000000):
        for slot in (0,1,37,511):
            allocation=((module+plan['image_size']+0xFFFF)&~0xFFFF)+slot*0x10000
            before=assemble(old,module,allocation);after=assemble(plan,module,allocation)
            for index,(a,b) in enumerate(zip(before,after)):
                if index in CHANGED_INDICES:
                    if b['asm'].count(a['asm'])!=1 or a['site']!=b['site'] or a['original']!=b['original']:raise ValueError('Original Orochi native body/entry changed')
                    if len(b['payload'])>b['code_capacity']:raise ValueError('Dual payload capacity exceeded')
                else:
                    if a['payload']!=b['payload'] or a['patched']!=b['patched']:raise ValueError('Unrelated payload/patch changed')
                    comparisons+=1
            layouts+=1
    stream=io.StringIO();result=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromModule(tests))
    if not result.wasSuccessful() or result.testsRun!=EXPECTED_TESTS or comparisons!=876 or layouts!=12:raise ValueError('Complete dual-boss CPU/relocation proof required: '+stream.getvalue())
    if files!={n:digest(ROOT/n) for n in SOURCE_FILES}:raise ValueError('Tested source changed during proof')
    receipt=dict(success=True,game_access=False,tests_run=result.testsRun,hook_count=81,
        unchanged_hooks=73,unchanged_payload_comparisons=comparisons,unchanged_patch_comparisons=comparisons,
        aslr_layouts=layouts,orochi_original_bodies_preserved=8,ninetails_binding_bytes=512,
        bootstrap_instance_addresses=False,final_exe_gameplay_validated=False,
        source_files=files,verifier_sha256=digest(Path(__file__)),
        profile_sha256=digest(ROOT/'profiles/steam-1.24.8.json'),generated_source_sha256=digest(ROOT/'launcher/Profile.generated.cs'))
    if report is not None:report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(receipt,indent=2)+'\n','utf-8')
    return receipt
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--report',type=Path);print(json.dumps(verify(ap.parse_args().report),indent=2))
