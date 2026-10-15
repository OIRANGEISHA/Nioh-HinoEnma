"""Compare all release payloads with the immutable user-tested trial hashes."""
import hashlib
import json
from pathlib import Path

from build_profile import ROOT, assemble, load_plan, load_beta61_plan, source_plan
from hinoenma_beta611_release import validate_release
from verify_beta56 import expected_layouts

TRIAL_SHA = '6b34a51a5f6c2ba6623d68b6ec968f590f51113e0c6a148a78cf0de5ea2f1315'
BASE_SHA = '9726a12e900b91eda692cf9721c56c131b3933ed5512d5aa6e096c8a09f435dd'
SOURCE_NAME = 'src/hinoenma_guardian_sludge_items.py'
SOURCE_SHA = '5fef9a589bbbbe72b5c4ac90f43829d5b7bcb9677d1a0fce77d2b78b3d860d1f'
CHANGED = {'HE_LivingWeaponDigitNine', 'HE_LadderCommonLookup',
    'HE_ProjectileElementInheritance', 'HE_SameTemplateUnloadResources',
    'HE_SaltEventCatchup', 'HE_MapVisualSpawnPrivate',
    'HE_MapVisualResourcePrivate', 'HE_MapVisualRestorePrivate'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    plan = load_plan()
    frozen = json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf-8'))
    if plan != frozen or source_plan(frozen) != plan:
        raise ValueError('Frozen release and source reconstruction differ')
    validate_release(plan)
    baseline = load_beta61_plan()
    path = ROOT/'docs/beta611-live-payload-identities.json'
    evidence = json.loads(path.read_text('utf-8'))
    if (evidence['version'] != plan['tool_version']
            or evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT/'profiles/baseline-beta6.1.json') != BASE_SHA
            or evidence['exact_executable_gameplay_validated'] is not False
            or evidence['source_files'].get(SOURCE_NAME) != SOURCE_SHA
            or len(evidence['source_files']) != 4
            or set(evidence['changed_hooks']) != CHANGED):
        raise ValueError('Exact tested four-repair identity required')
    for name, digest in evidence['source_files'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Tested source changed: ' + name)
    expected = {(r['module'],r['allocation'],r['name']):r for r in evidence['rows']}
    if len(evidence['rows']) != 984 or len(expected) != 984:
        raise ValueError('All 82 nonduplicate hooks at 12 layouts required')
    seen, unchanged, native = set(), 0, 0
    geometry = ('name','rva','length','original','code_offset','code_capacity','patched')
    for module, allocation in sorted(expected_layouts(plan)):
        changed = set()
        for old, new in zip(assemble(baseline,module,allocation),assemble(plan,module,allocation)):
            key = module, allocation, new['name']
            row = expected[key]
            if (hashlib.sha256(new['payload']).hexdigest() != row['payload_sha256']
                    or hashlib.sha256(new['patched']).hexdigest() != row['patch_sha256']):
                raise ValueError('Release differs from tested payload: ' + new['name'])
            if any(old[k] != new[k] for k in geometry):
                raise ValueError('Native site or allocation geometry changed')
            if old['payload'] == new['payload']:
                unchanged += 1
            else:
                changed.add(new['name'])
            seen.add(key)
            native += 1
        if changed != CHANGED:
            raise ValueError('Unexpected repaired payload set')
    if seen != set(expected) or unchanged != 888 or native != 984:
        raise ValueError('Incomplete equivalence')
    if any(plan[k] != baseline[k] for k in ('allocation_size','data_offset','protected_data_pages')):
        raise ValueError('Protected allocation changed')
    salt = next(h for h in baseline['hooks'] if h['name']=='HE_SaltEventCatchup')
    if plan['targets'] != dict(baseline['targets'],spell_schedule_return=salt['rva']+salt['length']):
        raise ValueError('Unexpected native target beyond the existing return alias')
    result = dict(success=True,version=plan['tool_version'],game_access=False,
        warm_payload_equivalence=True,exact_executable_gameplay_validated=False,
        hook_count=82,layout_count=12,live_payload_comparisons=len(seen),
        unchanged_previous_payloads=74,unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native,changed_hooks=sorted(CHANGED),
        source_files=evidence['source_files'],baseline_profile_sha256=BASE_SHA,
        trial_profile_sha256=TRIAL_SHA,evidence_sha256=sha(path),
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'),
        verifier_sha256=sha(Path(__file__)))
    output = ROOT/'artifacts/beta611/item-equivalence.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
