"""Compare Beta 6 with immutable hashes of the user-tested item payloads.

Public hash evidence contains no process snapshot or game assets. All checks
are offline; equivalence does not claim a fresh-process test of the new EXE.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from build_profile import ROOT, assemble, load_plan, load_beta563_plan, source_plan
from hinoenma_beta6_release import validate_release

TRIAL_SHA = '39f799894e3884ff3ec048efa96c77ce55f828466cf44a034046fa94462c7f20'
BASE_SHA = '7bfd8636d28db7e67196c201979b4d2522fd8e6133c637e698c3b554efb54695'
CHANGED = {'HE_Consumables', 'HE_HimorogiFragment', 'HE_InherentDirectElement',
           'HE_InputA', 'HE_InputB', 'HE_LadderCommonLookup', 'HE_LivingWeaponDigitNine'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    plan = load_plan()
    frozen = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
    if plan != frozen or source_plan(frozen) != plan:
        raise ValueError('Frozen Beta 6 and complete source reconstruction differ')
    validate_release(plan)
    baseline = load_beta563_plan()
    evidence_path = ROOT / 'docs/beta6-live-payload-identities.json'
    evidence = json.loads(evidence_path.read_text('utf-8'))
    if (evidence['trial_profile_sha256'] != TRIAL_SHA
            or evidence['baseline_profile_sha256'] != BASE_SHA
            or sha(ROOT / 'profiles/baseline-beta5.6.3.json') != BASE_SHA
            or evidence['exact_executable_gameplay_validated'] is not False
            or set(evidence['changed_hooks']) != CHANGED):
        raise ValueError('Expected the exact user-confirmed item trial identity')
    for name, digest in evidence['source_files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Live-tested item source changed: ' + name)
    expected = {(row['module'], row['allocation'], row['name']): row for row in evidence['rows']}
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
    if len(evidence['rows']) != 984 or seen != set(expected) or unchanged != 900:
        raise ValueError('Incomplete warm-payload equivalence')
    if any(plan[k] != baseline[k] for k in ('targets', 'allocation_size', 'data_offset', 'protected_data_pages')):
        raise ValueError('Native targets or protected data geometry changed')
    result = dict(success=True, version=plan['tool_version'], game_access=False,
        warm_payload_equivalence=True, exact_executable_gameplay_validated=False,
        hook_count=82, layout_count=12, live_payload_comparisons=len(seen),
        unchanged_previous_payloads=75, unchanged_payload_comparisons=unchanged,
        unchanged_native_patch_comparisons=native, changed_hooks=sorted(CHANGED),
        source_files=evidence['source_files'], baseline_profile_sha256=BASE_SHA,
        trial_profile_sha256=TRIAL_SHA, evidence_sha256=sha(evidence_path),
        profile_sha256=sha(ROOT / 'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT / 'launcher/Profile.generated.cs'),
        verifier_sha256=sha(Path(__file__)))
    path = ROOT / 'artifacts/beta6-item-equivalence.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + '\n', 'utf-8')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    verify()
