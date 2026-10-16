"""Compare all release payloads with the preserved confirmed live candidate."""
import hashlib
import json
from pathlib import Path
from build_profile import ROOT, assemble, load_plan, load_beta614_plan, source_plan
from hinoenma_beta62_release import validate_release, TRIAL_CANONICAL_SHA256
from verify_beta56 import expected_layouts
from verify_beta614_items import verify_gameplay as prior_gameplay

BASE_SHA = '68ed92a4bcc6ebde3903cf678449a961a048dcd4bb4ab1d3d147ff06985fd439'
TRIAL_SHA = '01d758fca58eda125e8e8e3bf43d2e87757852382658ce834777eeb95f015b60'
SOURCE_FILES = {
    'src/hinoenma_soul_purge.py': '727d111e7fae23a2895420d4b7da304a68404a9b2a79818f6af4f2fa6407e7ba',
    'src/hinoenma_kodama_transform.py': '2eaa5cc14673fb806b5f7bb11001425168513c2fc5fa564660015ce50b350a90',
    'src/hinoenma_kodama_transform_data.py': '33dfeef839bb222ebc14bb553e9e35452bf38c1cbb44f3fefeffb77fa842f67d',
}
CHANGED = {'HE_InputA', 'HE_InputB', 'HE_LivingWeaponDigitNine',
    'HE_MapPreviewCameraHeightPrivate', 'HE_MapVisualReadyPrivate', 'HE_MapVisualRestorePrivate',
    'HE_OrochiStalledInvalidRayExit', 'HE_OrochiZeroLengthRay', 'HE_SoulReleaseEligibility'}
ADDED = {'HE_SoulPurgeAttackFamiliarity', 'HE_SoulPurgeLuckFamiliarity'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_gameplay():
    records = prior_gameplay()
    for name in ('soul-purge-trial.json', 'kodama-transform-trial.json'):
        records[name] = json.loads((ROOT/'docs'/name).read_text('utf8'))
    soul = records['soul-purge-trial.json']
    kodama = records['kodama-transform-trial.json']
    actual = soul['runtime_verified']
    if (not all(soul['user_confirmed'].values()) or actual['minimum_familiarity'] != 300
            or actual['selected_weapon_familiarity_before'] != 999
            or actual['selected_weapon_familiarity_after_effect_ends'] != 0
            or actual['other_equipped_weapon_familiarity_unchanged'] != 999
            or not actual['consume_on_native_buff_removal']
            or not actual['active_buff_recast_restriction_preserved']):
        raise ValueError('Confirmed native Soul Purge cost/buff evidence required')
    actual = kodama['runtime_verified']
    if (kodama['candidate_sha256'] != TRIAL_SHA or kodama['user_feedback'] != '正常'
            or kodama['installed_hooks'] != 86 or actual['recorded_transformation_cycles'] != 1
            or (actual['item_quantity_before'], actual['item_quantity_after']) != (3, 2)
            or not all(actual[k] for k in ('native_visual_attached', 'native_visual_cleanup_on_exit',
                                          'request_cleared', 'returned_to_hino_idle'))
            or actual['injury_routing'] != 'offline CPU validation; not separately observed in this live run'):
        raise ValueError('Confirmed Kodama cycle with explicit injury-validation boundary required')
    return records


def verify():
    plan = load_plan()
    validate_release(plan)
    if plan != json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf8')) or source_plan(plan) != plan:
        raise ValueError('Source and frozen release differ')
    base = load_beta614_plan()
    path = ROOT/'docs/beta62-live-payload-identities.json'
    evidence = json.loads(path.read_text('utf8'))
    records = verify_gameplay()
    if (evidence['version'] != plan['tool_version'] or evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['trial_canonical_sha256'] != TRIAL_CANONICAL_SHA256
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT/'profiles/baseline-beta6.1.4.json') != BASE_SHA
            or evidence['source_files'] != SOURCE_FILES or set(evidence['changed_hooks']) != CHANGED
            or set(evidence['added_hooks']) != ADDED or evidence['exact_executable_gameplay_validated']
            or evidence['kodama_live_injury_validated'] or not evidence['runtime_gameplay_validated']
            or evidence['capacity_changes'] != [dict(name='HE_PostDefeatHealEvent', before=3072, after=1024)]):
        raise ValueError('Exact confirmed trial identity and scope required')
    for name, value in SOURCE_FILES.items():
        if sha(ROOT/name) != value:
            raise ValueError('Tested runtime source changed: ' + name)
    for name, value in evidence['gameplay_evidence_sha256'].items():
        if sha(ROOT/'docs'/name) != value:
            raise ValueError('Original gameplay evidence changed: ' + name)
    expected = {(r['module'], r['allocation'], r['name']): r for r in evidence['rows']}
    if len(evidence['rows']) != 1032 or len(expected) != 1032:
        raise ValueError('86 hooks at twelve unique layouts required')
    seen = set()
    unchanged = native = added_count = 0
    for module, allocation in sorted(expected_layouts(plan)):
        old = {h['name']: h for h in assemble(base, module, allocation)}
        changed, added = set(), set()
        for new in assemble(plan, module, allocation):
            key = module, allocation, new['name']; row = expected[key]; seen.add(key)
            if (hashlib.sha256(new['payload']).hexdigest() != row['payload_sha256']
                    or hashlib.sha256(new['patched']).hexdigest() != row['patch_sha256']):
                raise ValueError('Release differs from installed bytes: ' + new['name'])
            if new['name'] not in old:
                added.add(new['name']); added_count += 1; continue
            prior = old[new['name']]
            for field in ('name', 'rva', 'length', 'original', 'code_offset', 'patched'):
                if prior[field] != new[field]:
                    raise ValueError('Previous native entry changed: ' + new['name'])
            if new['code_capacity'] != (1024 if new['name'] == 'HE_PostDefeatHealEvent' else prior['code_capacity']):
                raise ValueError('Unexpected code slot change')
            if prior['payload'] == new['payload']: unchanged += 1
            else: changed.add(new['name'])
            native += 1
        if changed != CHANGED or added != ADDED:
            raise ValueError('Unexpected changed/added payload set')
    if seen != set(expected) or (unchanged, native, added_count) != (900, 1008, 24):
        raise ValueError('Incomplete payload comparison')
    if any(plan[k] != base[k] for k in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets')):
        raise ValueError('Allocation or native targets changed')
    result = dict(success=True, version=plan['tool_version'], game_access=False,
        warm_payload_equivalence=True, exact_executable_gameplay_validated=False,
        runtime_gameplay_validated=True, kodama_live_injury_validated=False,
        hook_count=86, layout_count=12, live_payload_comparisons=len(seen),
        unchanged_previous_payloads=75, unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native, added_native_patch_comparisons=added_count,
        changed_hooks=sorted(CHANGED), added_hooks=sorted(ADDED), source_files=SOURCE_FILES,
        baseline_profile_sha256=BASE_SHA, trial_profile_sha256=TRIAL_SHA, evidence_sha256=sha(path),
        gameplay_evidence_sha256={n: sha(ROOT/'docs'/n) for n in records},
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'), verifier_sha256=sha(Path(__file__)))
    out = ROOT/'artifacts/beta62/item-equivalence.json'; out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n', 'utf8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
