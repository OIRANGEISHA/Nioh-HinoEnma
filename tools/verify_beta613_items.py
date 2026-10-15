"""Compare all release payloads with immutable, user-confirmed runtime bytes."""
import hashlib, json
from pathlib import Path
from build_profile import ROOT, assemble, load_plan, load_beta612_plan, source_plan
from hinoenma_beta613_release import validate_release
from verify_beta56 import expected_layouts

BASE_SHA='b6c5a560dd605ab114870e633e22d87e0b4a6c5dd8da8743dc71ef19f907311c'
TRIAL_SHA='e80d67a86461f3bc0a0db15ee9f27f9e570929157faa8cd8f589b08265fe4913'
SOURCE_FILES={
    'src/hinoenma_sticky_dispersal_items.py':'9d263926bcaf761244ff8b18d2b248712c0b5886d3ca1a182a9131149cc1c420',
    'src/hinoenma_dispersal_reuse.py':'3c0381c20fe98e40aa239e1d71564deb1c77a27a71f6795076080e42bdcef404',
    'src/hinoenma_nine_talismans.py':'bd82c2c7603ccd382bb09c07fc672187d55690c1b7cfa71dd8d1cf889a0ebac2',
    'src/hinoenma_soul_release.py':'c2addddcef7c66a3c57ffe32595951e4c5d5e43f18592832c48a061598c407db'}
CHANGED={'HE_InputA','HE_InputB','HE_LivingWeaponDigitNine','HE_ProjectileElementInheritance',
    'HE_PostDefeatDamage','HE_PostDefeatRestore','HE_MapVisualSpawnPrivate',
    'HE_MapVisualResourcePrivate','HE_MapVisualRestorePrivate','HE_MapNativeIdlePrivate'}
ADDED={'HE_SoulReleaseEligibility','HE_SoulReleaseFamiliarity'}
GAMEPLAY={
    'sticky-dispersal-items-trial.json':'warm_trial_items_and_four_consecutive_dispersal_casts_user_confirmed',
    'nine-talismans-trial.json':'nine_items_user_confirmed',
    'soul-release-trial.json':'warm_trial_native_projectile_and_familiarity_consumption_user_confirmed'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def verify_gameplay():
    records={name:json.loads((ROOT/'docs'/name).read_text('utf8')) for name in GAMEPLAY}
    for name,record in records.items():
        if (record['status']!=GAMEPLAY[name] or record.get('user_confirmation_pending',False)
            or record.get('cold_launch_tested',False) or record.get('release_exe_updated',False)):
            raise ValueError('Retained gameplay identity/scope differs: '+name)
    soul=records['soul-release-trial.json']
    if (soul['candidate_file_sha256']!=TRIAL_SHA or soul['source_files_sha256']!=SOURCE_FILES
        or soul['selected_weapon_familiarity']!=[999,0] or soul['prepared_uses_at_cast']!=[1,0]
        or not soul['boss_equipment_bytes_unchanged'] or not soul['native_familiarity_and_stock_consumption_retained']
        or soul['compatibility_inventory_writes'] or not soul['read_only_capture_finished']):
        raise ValueError('Native Soul Release consumption/gameplay receipt required')
    nine=records['nine-talismans-trial.json']
    if len(nine['items'])!=9 or not all(i['native_object_seen'] and i['native_commit_seen'] for i in nine['items']):
        raise ValueError('All nine earlier native effects require evidence')
    if records['sticky-dispersal-items-trial.json']['final_user_feedback']!='用了4次，正常':
        raise ValueError('Four consecutive Dispersal uses require confirmation')
    return records

def verify():
    plan=load_plan();validate_release(plan)
    if plan!=json.loads((ROOT/'profiles/steam-1.24.8.json').read_text('utf8')) or source_plan(plan)!=plan:
        raise ValueError('Source and frozen release differ')
    base=load_beta612_plan();path=ROOT/'docs/beta613-live-payload-identities.json'
    evidence=json.loads(path.read_text('utf8'))
    if (evidence['version']!=plan['tool_version'] or evidence['trial_profile_sha256']!=TRIAL_SHA
        or evidence['baseline_profile_sha256']!=BASE_SHA or sha(ROOT/'profiles/baseline-beta6.1.2.json')!=BASE_SHA
        or evidence['source_files']!=SOURCE_FILES or set(evidence['changed_hooks'])!=CHANGED
        or set(evidence['added_hooks'])!=ADDED or evidence['exact_executable_gameplay_validated']):
        raise ValueError('Exact tested trial identity required')
    for name,digest in SOURCE_FILES.items():
        if sha(ROOT/name)!=digest:raise ValueError('Tested runtime source changed: '+name)
    verify_gameplay()
    expected={(r['module'],r['allocation'],r['name']):r for r in evidence['rows']}
    if len(evidence['rows'])!=1008 or len(expected)!=1008:raise ValueError('84 hooks at 12 unique layouts required')
    seen=set();unchanged=0;native=0;added=0
    for module,allocation in sorted(expected_layouts(plan)):
        old={h['name']:h for h in assemble(base,module,allocation)};changed=set()
        for new in assemble(plan,module,allocation):
            key=module,allocation,new['name'];row=expected[key];seen.add(key)
            if (hashlib.sha256(new['payload']).hexdigest()!=row['payload_sha256']
                or hashlib.sha256(new['patched']).hexdigest()!=row['patch_sha256']):
                raise ValueError('Release differs from tested bytes: '+new['name'])
            if new['name'] in ADDED:added+=1;continue
            prior=old[new['name']]
            for field in ('name','rva','length','original','code_offset','patched'):
                if prior[field]!=new[field]:raise ValueError('Previous native entry or code start moved')
            cap=0xC00 if new['name'] in ('HE_PostDefeatRestore','HE_PostDefeatHealEvent') else prior['code_capacity']
            if new['code_capacity']!=cap:raise ValueError('Unexpected code partition change')
            if prior['payload']==new['payload']:unchanged+=1
            else:changed.add(new['name'])
            native+=1
        if changed!=CHANGED:raise ValueError('Unexpected changed payload set')
    if seen!=set(expected) or (unchanged,native,added)!=(864,984,24):raise ValueError('Incomplete payload comparison')
    if any(plan[k]!=base[k] for k in ('allocation_size','data_offset','protected_data_pages')):
        raise ValueError('Protected allocation changed')
    extra={k:v for k,v in plan['targets'].items() if k not in base['targets']}
    if extra!={'soul_damage_skip':0x7E2943,'soul_familiarity_min':0x12358A8} or any(plan['targets'][k]!=v for k,v in base['targets'].items()):
        raise ValueError('Native targets differ from tested Soul Release readers')
    result=dict(success=True,version=plan['tool_version'],game_access=False,
        warm_payload_equivalence=True,exact_executable_gameplay_validated=False,
        hook_count=84,layout_count=12,live_payload_comparisons=len(seen),
        unchanged_previous_payloads=72,unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native,added_native_patch_comparisons=added,
        changed_hooks=sorted(CHANGED),added_hooks=sorted(ADDED),source_files=SOURCE_FILES,
        baseline_profile_sha256=BASE_SHA,trial_profile_sha256=TRIAL_SHA,evidence_sha256=sha(path),
        gameplay_evidence_sha256={n:sha(ROOT/'docs'/n) for n in GAMEPLAY},
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'),verifier_sha256=sha(Path(__file__)))
    out=ROOT/'artifacts/beta613/item-equivalence.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+'\n','utf8');print(json.dumps(result));return result

if __name__=='__main__':verify()
