"""Portable Orochi binding/resource/geometry proof; never access a game process."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in ('src', 'tests', 'tools'):
    sys.path.insert(0, str(ROOT / directory))

SOURCE_FILES = (
    'src/hinoenma_orochi_trial.py', 'src/hinoenma_orochi_candidate_v2.py',
    'src/hinoenma_orochi_candidate_v3.py', 'src/hinoenma_orochi_trace_v4.py',
    'src/hinoenma_orochi_candidate_v5.py', 'src/hinoenma_orochi_ray_guard.py',
    'src/hinoenma_orochi_ray_guard_v2.py', 'src/hinoenma_orochi_runtime.py',
    'src/hinoenma_orochi_binding.py', 'src/hinoenma_orochi_weapon_guard.py',
    'tests/orochi_fixture.py',
    'tests/test_orochi_execution.py', 'tools/build_profile.py', 'launcher/Native.cs',
    'profiles/legacy-beta5.4.json')
FROZEN = {
    SOURCE_FILES[0]: '5d566f42183d42a042ed6f313124a89e5627eb99d4bac871a228665fa02673ad',
    SOURCE_FILES[1]: 'e073ac02eb4bd560a375a9cd9a1973abe5bd953ab0334cce3a9978fe85b4017e',
    SOURCE_FILES[2]: 'da0fdc7db4b799e0ea61ee4f675bece5c87873066fc2852fd623c1745d7aaee9',
    SOURCE_FILES[3]: '7a52d8607b61685465c820c5d8c8db26bc967ae6e19a78a403690df353819d4a',
    SOURCE_FILES[4]: '24faa34d07350d41a54a63adf7724c6ef7eb464e69401e4977858f97a7b88120',
    SOURCE_FILES[5]: '319f812b968110ea646a012437f2cd2ffcda2c5d8f68ec9cbe5926cd238c7f45',
    SOURCE_FILES[6]: '4a7c3d0096409b587bd8992022a95e0aacdea16aa52a554ed90b1d4a5eee1e5e'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(report=None):
    from build_profile import generate, load_plan
    from hinoenma_orochi_runtime import NATIVE_SPANS
    from build_profile import validate_layout
    from test_orochi_execution import Tests

    source_files = {name: digest(ROOT / name) for name in SOURCE_FILES}
    if any(source_files[name] != value for name, value in FROZEN.items()):
        raise ValueError('Confirmed scene trial source changed')
    plan = load_plan()
    validate_layout(plan)
    if (ROOT / 'launcher/Profile.generated.cs').read_text('utf-8') != generate(plan):
        raise ValueError('Generated execution profile is stale')
    if any(token in hook['asm'] for hook in plan['hooks'][71:]
           for token in ('{orochi_data}', '{production_data}', '{execution_data}')):
        raise ValueError('Scene-bound private address survived integration')
    if (plan.get('orochi_bootstrap_instance_addresses') is not False
            or plan.get('orochi_fresh_exe_gameplay_validated') is not False
            or plan.get('ninetails_execution_validated') is not False):
        raise ValueError('Execution verification scope differs')
    native = (ROOT / 'launcher/Native.cs').read_text('utf-8')
    region = native.split('ExecutionNativeFrames = new MemorySpan[] {', 1)[1].split('};', 1)[0]
    frames = [(int(a, 16), int(b, 16)) for a, b in
              re.findall(r'new MemorySpan\((0x[0-9A-Fa-f]+),(0x[0-9A-Fa-f]+)\)', region)]
    if frames != [(start, start+length) for start, length in NATIVE_SPANS]:
        raise ValueError('Complete execution native frame guards differ')
    Tests.previous_payload_comparisons = Tests.previous_patch_comparisons = Tests.aslr_layouts = 0
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    if (not result.wasSuccessful() or result.testsRun != 34 or Tests.aslr_layouts != 12
            or Tests.previous_payload_comparisons != 852 or Tests.previous_patch_comparisons != 852):
        raise ValueError('Complete portable execution proof required: '+stream.getvalue())
    receipt = dict(success=True, game_access=False, tests_run=result.testsRun,
        hook_count=81, execution_hook_count=10, previous_hooks_preserved=71,
        previous_payload_comparisons=Tests.previous_payload_comparisons,
        previous_patch_comparisons=Tests.previous_patch_comparisons, aslr_layouts=Tests.aslr_layouts,
        native_frame_guards=len(frames), bootstrap_instance_addresses=False,
        native_calls='explicit synthetic Win64 stubs', fixture='synthetic owners/resources only',
        final_exe_gameplay_validated=False, ninetails_execution_validated=False,
        source_files=source_files, verifier_sha256=digest(Path(__file__)),
        profile_sha256=digest(ROOT / 'profiles/steam-1.24.8.json'),
        generated_source_sha256=digest(ROOT / 'launcher/Profile.generated.cs'))
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8', newline='\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.report), indent=2))
