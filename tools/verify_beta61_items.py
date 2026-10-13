"""Compare Beta 6.1 with immutable hashes of the user-tested item payloads.

Public hash evidence contains no process snapshot or game assets. All checks
are offline; equivalence does not claim a fresh-process test of the new EXE.
"""
import hashlib
import json
from pathlib import Path

from build_profile import ROOT, assemble, load_plan, load_beta6_plan, source_plan
from hinoenma_beta61_release import validate_release

TRIAL_SHA = 'a8687a3dbec3fe6245f0f62e70e10d818af690bf8ffa57c6e6329534a89c1e75'
BASE_SHA = '7f8e4fa3dc9144ebd8d65ab06826fb447a8691c341abab904223c33e13e38f86'
SOURCE_NAME = 'src/hinoenma_wind_weakness_dragon.py'
SOURCE_SHA = 'f4546def16fadca6d7a270c57cf2873658e8c5e406d70df48f10d324f91cd7cc'
CHANGED = {'HE_InputA', 'HE_InputB', 'HE_LivingWeaponDigitNine'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    plan = load_plan()
    frozen = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
    if plan != frozen or source_plan(frozen) != plan:
        raise ValueError('Frozen Beta 6.1 and complete source reconstruction differ')
    validate_release(plan)
    baseline = load_beta6_plan()
    evidence_path = ROOT / 'docs/beta61-live-payload-identities.json'
    evidence = json.loads(evidence_path.read_text('utf-8'))
    if (evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT / 'profiles/baseline-beta6.json') != BASE_SHA
            or evidence['exact_executable_gameplay_validated'] is not False
            or evidence['source_files'].get(SOURCE_NAME) != SOURCE_SHA
            or set(evidence['changed_hooks']) != CHANGED):
        raise ValueError('Expected the exact user-confirmed item trial identity')
    for name, digest in evidence['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Live-tested item source changed: ' + name)
    expected = {(row['module'], row['allocation'], row['name']): row for row in evidence['rows']}
    if len(plan['hooks']) != 82 or len(baseline['hooks']) != 82 or len(expected) != 984:
        raise ValueError('Exact complete, nonduplicate 82-hook proof required')
    seen, unchanged, native = set(), 0, 0
    geometry = ('name', 'rva', 'length', 'original', 'code_offset', 'code_capacity', 'patched')
    for module in (0x140000000, 0x7FF83AA00000, 0x7FFA01000000):
        for slot in (0, 1, 37, 511):
            allocation = ((module + plan['image_size'] + 0xFFFF) & ~0xFFFF) + slot * 0x10000
            changed = set()
            for old, new in zip(assemble(baseline, module, allocation), assemble(plan, module, allocation)):
                key = module, allocation, new['name']
                row = expected[key]
                if (hashlib.sha256(new['payload']).hexdigest() != row['payload_sha256']
                        or hashlib.sha256(new['patched']).hexdigest() != row['patch_sha256']):
                    raise ValueError('Release differs from user-tested payload: ' + new['name'])
                if any(old[k] != new[k] for k in geometry):
                    raise ValueError('Native site or allocation geometry changed: ' + new['name'])
                if old['payload'] == new['payload']:
                    unchanged += 1
                else:
                    changed.add(new['name'])
                native += 1
                seen.add(key)
            if changed != CHANGED:
                raise ValueError('Unexpected item repair hook set')
    if len(evidence['rows']) != 984 or seen != set(expected) or unchanged != 948:
        raise ValueError('Incomplete warm-payload equivalence')
    if any(plan[k] != baseline[k] for k in ('targets', 'allocation_size', 'data_offset', 'protected_data_pages')):
        raise ValueError('Native targets or protected data geometry changed')
    result = dict(success=True, version=plan['tool_version'], game_access=False,
        warm_payload_equivalence=True, exact_executable_gameplay_validated=False,
        hook_count=82, layout_count=12, live_payload_comparisons=len(seen),
        unchanged_previous_payloads=79, unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native, changed_hooks=sorted(CHANGED),
        source_files=evidence['source_files'], baseline_profile_sha256=BASE_SHA,
        trial_profile_sha256=TRIAL_SHA, evidence_sha256=sha(evidence_path),
        profile_sha256=sha(ROOT / 'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT / 'launcher/Profile.generated.cs'),
        verifier_sha256=sha(Path(__file__)))
    path = ROOT / 'artifacts/beta61-item-equivalence.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
