"""Verify release payload equivalence to the recorded live Growth750 trial."""
from copy import deepcopy
import hashlib
import json
from build_profile import ROOT, assemble, load_plan, source_plan, source_plan_beta562
from hinoenma_growth750_release import validate_release

BASE_SHA = '25a113a885867f922308eb75c8b87cf3b5088274496121318197ab69225e3f7b'
SOURCE_SHA = '33d1d635b6d0783c390bac32e26a418904bf1ecb043968bebd7f52966635ee01'
TRIAL_SHA = 'c1c7ac7f98a49953362c234fbd5b71d145a4fb5dcab3c1bbc7c87479432a9c90'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    baseline_file = ROOT / 'profiles/legacy-beta5.6.2.json'
    if sha(baseline_file) != BASE_SHA or sha(ROOT / 'src/hinoenma_growth750.py') != SOURCE_SHA:
        raise ValueError('Exact baseline and live-confirmed growth source required')
    plan = load_plan()
    frozen = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
    rebuilt = source_plan(frozen)
    if plan != rebuilt or frozen != plan:
        raise ValueError('Frozen release and pure source reconstruction differ')
    validate_release(plan)
    evidence = json.loads((ROOT / 'docs/growth750-live-payload-identities.json').read_text('utf-8'))
    if (evidence['trial_profile_sha256'] != TRIAL_SHA or evidence['source_sha256'] != SOURCE_SHA
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or evidence['new_executable_gameplay_tested'] is not False):
        raise ValueError('Expected exact recorded warm-test identity')
    baseline = source_plan_beta562(json.loads(baseline_file.read_text('utf-8')))
    expected = {(r['module'], r['allocation'], r['name']): r for r in evidence['rows']}
    seen, unchanged, patch_count, attribute_sizes = set(), 0, 0, set()
    for module in (0x140000000, 0x7FF83AA00000, 0x7FFA01000000):
        for slot in (0, 1, 37, 511):
            allocation = ((module + plan['image_size'] + 0xFFFF) & ~0xFFFF) + slot * 0x10000
            old, new = assemble(baseline, module, allocation), assemble(plan, module, allocation)
            changed = []
            for a, b in zip(old, new):
                key = module, allocation, b['name']
                row = expected[key]
                if (hashlib.sha256(b['payload']).hexdigest() != row['payload_sha256']
                        or hashlib.sha256(b['patched']).hexdigest() != row['patch_sha256']):
                    raise ValueError('Runtime bytes differ from live trial: ' + b['name'])
                if a['payload'] != b['payload']:
                    changed.append(b['name'])
                    attribute_sizes.add(len(b['payload']))
                else:
                    unchanged += 1
                if any(a[k] != b[k] for k in ('name', 'rva', 'length', 'original', 'code_offset', 'code_capacity', 'patched')):
                    raise ValueError('Native hook or allocation geometry changed')
                patch_count += 1
                seen.add(key)
            if changed != ['HE_AttributeOverlay']:
                raise ValueError('Unexpected changed payload set')
    if len(evidence['rows']) != 984 or seen != set(expected) or unchanged != 972 or attribute_sizes != {3188}:
        raise ValueError('Incomplete live equivalence checks')
    negative = 0
    for changes in ({'growth750_release_revision': 0}, {'growth750_revision': 0},
                    {'growth750_trial': True}, {'growth750_flat_attack_separate': False},
                    {'growth750_extra_multipliers': dict(first_level=400, hp=[2, 1], attack=[6, 5])}):
        bad = deepcopy(plan)
        bad.update(changes)
        try:
            validate_release(bad)
        except ValueError:
            negative += 1
        else:
            raise ValueError('Changed policy accepted')
    result = dict(success=True, version=plan['tool_version'], game_access=False,
        exact_executable_gameplay_validated=False, warm_payload_equivalence=True,
        hook_count=82, layout_count=12, live_payload_comparisons=len(seen),
        unchanged_previous_payloads=81, unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=patch_count, negative_policy_guards=negative,
        changed_hook='HE_AttributeOverlay', attribute_payload_bytes=3188,
        source_sha256=SOURCE_SHA, baseline_profile_sha256=BASE_SHA,
        trial_profile_sha256=TRIAL_SHA, profile_sha256=sha(ROOT / 'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT / 'launcher/Profile.generated.cs'),
        verifier_sha256=sha(ROOT / 'tools/verify_beta563_growth.py'))
    path = ROOT / 'artifacts/growth750-equivalence.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
