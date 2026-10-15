"""Compare the complete local release with the immutable running-game trial."""
import hashlib
import json
from pathlib import Path

from build_profile import ROOT, assemble, load_plan, load_beta611_plan, source_plan
from hinoenma_beta612_release import validate_release
from verify_beta56 import expected_layouts

TRIAL_SHA = '10de9812cc866951b6868145ff2c9942d5e2694f7214db9945911072c25d2a92'
BASE_SHA = '0b9941751ce724b531795613c3f6a3d3e7c3ec973dd6d06445aa1bcaaaf24d05'
SOURCE_NAME = 'src/hinoenma_elemental_resistance_items.py'
SOURCE_SHA = '6dd05586bcb02f7ca2d3c85ed75ba234d7a34c50cd0d96d2739f57051a7fdf51'
CHANGED = {'HE_LivingWeaponDigitNine'}


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    plan = load_plan()
    frozen = json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf-8'))
    if plan != frozen or source_plan(frozen) != plan:
        raise ValueError('Frozen release and source reconstruction differ')
    validate_release(plan)
    baseline = load_beta611_plan()
    path = ROOT/'docs/beta612-live-payload-identities.json'
    evidence = json.loads(path.read_text('utf-8'))
    if (evidence['version'] != plan['tool_version']
            or evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT/'profiles/baseline-beta6.1.1.json') != BASE_SHA
            or evidence['exact_executable_gameplay_validated'] is not False
            or evidence['source_files'] != {SOURCE_NAME: SOURCE_SHA}
            or set(evidence['changed_hooks']) != CHANGED):
        raise ValueError('Exact tested resistance-trial identity required')
    for name, digest in evidence['source_files'].items():
        if sha(ROOT/name) != digest: raise ValueError('Tested source changed: '+name)
    gameplay = json.loads((ROOT/'docs/elemental-resistance-items-trial.json').read_text('utf-8'))
    if (gameplay['candidate_sha256'] != TRIAL_SHA or gameplay['source_sha256'] != SOURCE_SHA
            or not gameplay['all_five_native_aggregate_changes_observed']
            or gameplay['user_confirmation_pending']
            or len(gameplay['sampled_injury_evidence']) != 3
            or not gameplay['quantity_decrement_not_an_acceptance_requirement']
            or gameplay['all_five_individually_interrupted']):
        raise ValueError('Original gameplay confirmation and coverage boundary required')
    expected = {(r['module'],r['allocation'],r['name']):r for r in evidence['rows']}
    if len(evidence['rows']) != 984 or len(expected) != 984:
        raise ValueError('All 82 nonduplicate hooks at 12 layouts required')
    seen, unchanged, native = set(), 0, 0
    geometry = ('name','rva','length','original','code_offset','code_capacity','patched')
    for module, allocation in sorted(expected_layouts(plan)):
        changed = set()
        for old,new in zip(assemble(baseline,module,allocation), assemble(plan,module,allocation)):
            key = module, allocation, new['name']
            row = expected[key]
            if (hashlib.sha256(new['payload']).hexdigest() != row['payload_sha256']
                    or hashlib.sha256(new['patched']).hexdigest() != row['patch_sha256']):
                raise ValueError('Release differs from tested payload: '+new['name'])
            if any(old[k] != new[k] for k in geometry):
                raise ValueError('Native site or allocation geometry changed')
            if old['payload'] == new['payload']: unchanged += 1
            else: changed.add(new['name'])
            seen.add(key); native += 1
        if changed != CHANGED: raise ValueError('Unexpected repaired payload set')
    if seen != set(expected) or unchanged != 972 or native != 984:
        raise ValueError('Incomplete equivalence')
    if any(plan[k] != baseline[k] for k in ('allocation_size','data_offset','protected_data_pages','targets')):
        raise ValueError('Protected allocation or native targets changed')
    result = dict(success=True,version=plan['tool_version'],game_access=False,
        warm_payload_equivalence=True,exact_executable_gameplay_validated=False,
        hook_count=82,layout_count=12,live_payload_comparisons=len(seen),
        unchanged_previous_payloads=81,unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native,changed_hooks=sorted(CHANGED),
        source_files=evidence['source_files'],baseline_profile_sha256=BASE_SHA,
        trial_profile_sha256=TRIAL_SHA,evidence_sha256=sha(path),
        gameplay_evidence_sha256=sha(ROOT/'docs/elemental-resistance-items-trial.json'),
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'),
        verifier_sha256=sha(Path(__file__)))
    output = ROOT/'artifacts/beta612/item-equivalence.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
    return result


if __name__ == '__main__': verify()
