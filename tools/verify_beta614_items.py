"""Check the release against the exact installed trial, including limited gameplay evidence."""
import hashlib
import json
from pathlib import Path
from build_profile import ROOT, assemble, load_plan, load_beta613_plan, source_plan
from hinoenma_beta614_release import validate_release, TRIAL_CANONICAL_SHA256
from verify_beta56 import expected_layouts
from verify_beta613_items import verify_gameplay as prior_gameplay

BASE_SHA = '7204b9bd34a16e75b2b72b3101c47a599f0ef22a94ae2dd4eefc8bb2018957c5'
TRIAL_SHA = '2dd5fb23d33cd060749bf733c70ffa3b6d0c3a1bdcabe9b4bb1e3dc9ce9df870'
SOURCE_FILES = {
    'src/hinoenma_general_jutsu.py': '19a887c48469e88b78d9e33dac0b4bd663e7df1befd236a189d7baeeeab72831',
    'src/hinoenma_general_jutsu_data.py': '8ded1af84f3eed338e0e1d3e65641a03ef3c8ac91c9c1a2b525fac7798b7975b',
    'src/hinoenma_general_jutsu_timing.py': 'de517500aade48d58e6986802709cf17e686a5b6c670f9255f564c405e8a3cf6',
    'src/hinoenma_general_jutsu_recovery.py': 'c308bdf31a784e54ee5c363786a11318e25cbb41f4c14782cca8b3070808ca32',
}
CHANGED = {'HE_InputA', 'HE_InputB', 'HE_LivingWeaponDigitNine', 'HE_MapNativeIdlePrivate',
    'HE_MapPreviewCameraDistancePrivate', 'HE_MapPreviewCameraHeightPrivate',
    'HE_MapVisualResourcePrivate', 'HE_MapVisualRestorePrivate', 'HE_PostDefeatHealScript',
    'HE_SaltEventCatchup'}
ADDED = set()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_gameplay():
    records = prior_gameplay()
    record = json.loads((ROOT/'docs/general-jutsu-trial.json').read_text('utf8'))
    confirmed = record['gameplay_confirmation']
    injuries = confirmed['observed_cast_injuries']
    if (record['status'] != 'kunai-confirmed-special-cases-audited' or record['revision'] != 3
            or record['candidate_sha256'] != TRIAL_SHA or confirmed['candidate_sha256'] != TRIAL_SHA
            or confirmed['user_result'] != '正常' or not confirmed['user_confirmed_projectile_repeat_and_recovery']
            or not confirmed['recording_finished'] or confirmed['verified_hooks'] != 84
            or confirmed['common_injury_resolved_as_boss'] or len(injuries) != 2
            or {(r['previous_action'], r['injury_action'], r['injury_bank']) for r in injuries}
                != {(986, 91, 2), (612, 107, 2)}
            or record['native_action_categories'] != 13 or record['captured_definition_count'] != 132):
        raise ValueError('Exact sampled Kunai gameplay receipt required')
    records['general-jutsu-trial.json'] = record
    return records


def verify():
    plan = load_plan()
    validate_release(plan)
    if plan != json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf8')) or source_plan(plan) != plan:
        raise ValueError('Source and frozen release differ')
    base = load_beta613_plan()
    path = ROOT/'docs/beta614-live-payload-identities.json'
    evidence = json.loads(path.read_text('utf8'))
    records = verify_gameplay()
    if (evidence['version'] != plan['tool_version'] or evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['trial_canonical_sha256'] != TRIAL_CANONICAL_SHA256
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT/'profiles/baseline-beta6.1.3.json') != BASE_SHA
            or evidence['source_files'] != SOURCE_FILES or set(evidence['changed_hooks']) != CHANGED
            or evidence['added_hooks'] or evidence['exact_executable_gameplay_validated']
            or evidence['all_jutsu_gameplay_validated'] or not evidence['sampled_kunai_gameplay_validated']
            or evidence['confirmation'] != records['general-jutsu-trial.json']['gameplay_confirmation']):
        raise ValueError('Exact trial identity and limited confirmation required')
    for name, digest in SOURCE_FILES.items():
        if sha(ROOT/name) != digest:
            raise ValueError('Tested runtime source changed: ' + name)
    expected = {(r['module'], r['allocation'], r['name']): r for r in evidence['rows']}
    if len(evidence['rows']) != 1008 or len(expected) != 1008:
        raise ValueError('84 hooks at 12 unique layouts required')
    seen = set()
    unchanged = native = 0
    for module, allocation in sorted(expected_layouts(plan)):
        old = {h['name']: h for h in assemble(base, module, allocation)}
        changed = set()
        for new in assemble(plan, module, allocation):
            key = module, allocation, new['name']
            row = expected[key]
            seen.add(key)
            if (hashlib.sha256(new['payload']).hexdigest() != row['payload_sha256']
                    or hashlib.sha256(new['patched']).hexdigest() != row['patch_sha256']):
                raise ValueError('Release differs from tested bytes: ' + new['name'])
            prior = old[new['name']]
            for field in ('name', 'rva', 'length', 'original', 'code_offset', 'code_capacity', 'patched'):
                if prior[field] != new[field]:
                    raise ValueError('Previous native entry or code partition changed: ' + new['name'])
            if prior['payload'] == new['payload']:
                unchanged += 1
            else:
                changed.add(new['name'])
            native += 1
        if changed != CHANGED:
            raise ValueError('Unexpected changed payload set')
    if seen != set(expected) or (unchanged, native) != (888, 1008):
        raise ValueError('Incomplete payload comparison')
    if any(plan[k] != base[k] for k in ('allocation_size', 'data_offset', 'protected_data_pages', 'targets')):
        raise ValueError('Allocation or native targets changed')
    result = dict(success=True, version=plan['tool_version'], game_access=False,
        warm_payload_equivalence=True, exact_executable_gameplay_validated=False,
        sampled_kunai_gameplay_validated=True, all_jutsu_gameplay_validated=False,
        hook_count=84, layout_count=12, live_payload_comparisons=len(seen),
        unchanged_previous_payloads=74, unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native, added_native_patch_comparisons=0,
        changed_hooks=sorted(CHANGED), added_hooks=[], source_files=SOURCE_FILES,
        baseline_profile_sha256=BASE_SHA, trial_profile_sha256=TRIAL_SHA, evidence_sha256=sha(path),
        gameplay_evidence_sha256={n: sha(ROOT/'docs'/n) for n in records},
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'), verifier_sha256=sha(Path(__file__)))
    out = ROOT/'artifacts/beta614/item-equivalence.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', 'utf8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
