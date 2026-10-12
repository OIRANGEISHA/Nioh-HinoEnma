"""Prove the immutable Beta5.2 basis and the scoped current revisions.

This verifier uses only included UTF-8 source/profile files. It never opens
the game, loads proprietary files or requires a Git checkout.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from build_profile import ROOT, assemble, load_plan, relocation_specs

BASELINE_COMMIT = 'b5a4d9811efa64042587a9b01c71712cc9283a8c'
BASELINE_SHA256 = '41f543e4a7b032000baa21eadc94d3b14f7f181d84a298b858986a1199aafbf3'
BASELINE_BLOB = '4d3efc5d57146fc323ec8e7fbbfbd049eaa1033e'
RELEASED_542_SHA256 = '566e21cac4835023f4d573c8a7b02467e929a315f3d643ce01b2f4adaa2540c4'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_plans(original: dict, current: dict) -> dict:
    from hinoenma_abyss_runtime import VERSION, apply_abyss, validate_layout
    abyss = current.get('tool_version') == VERSION
    if len(original['hooks']) != 60 or len(current['hooks']) != (82 if abyss else 81):
        raise ValueError('Exact published60 and version-scoped current hook count required')
    for key in ('disk_sha256', 'image_size', 'pe_timestamp_hex', 'data_offset'):
        if original[key] != current[key]:
            raise ValueError('Original executable/core identity changed: '+key)
    expected_allocation = {'1.0.0-beta.5.4.1':0x43000, '1.0.0-beta.5.4.2':0x51000,
                           VERSION:0x55000}.get(current['tool_version'])
    if original['allocation_size'] != 0x20000 or current['allocation_size'] != expected_allocation:
        raise ValueError('Exact baseline/current allocation layout required')
    if any(current['targets'].get(key) != value for key,value in original['targets'].items()):
        raise ValueError('A published native target changed')
    basis = current
    changed = []
    if abyss:
        validate_layout(current)
        released_path = ROOT/'profiles/legacy-beta5.4.2.json'
        if digest(released_path) != RELEASED_542_SHA256:
            raise ValueError('Immutable released Beta5.4.2 basis changed')
        basis = json.loads(released_path.read_text('utf-8'))
        reconstructed = apply_abyss(basis)
        if current['hooks'] != reconstructed['hooks'] or current['targets'] != reconstructed['targets']:
            raise ValueError('Current changes differ from the complete scoped source reconstruction')
        changed = [i for i in range(60) if current['hooks'][i] != original['hooks'][i]]
        if changed != [1,8,9,39]:
            raise ValueError('Unexpected changes to the original60 current bodies')
        identity = ('name','rva','length','original','code_offset','code_capacity')
        if any(any(current['hooks'][i][key] != original['hooks'][i][key] for key in identity)
               for i in range(60)):
            raise ValueError('Published native entry or code-slot identity changed')
    if basis['hooks'][:60] != original['hooks']:
        raise ValueError('A published baseline hook source/signature/slot changed')
    # The frozen profile supplies old metadata for old inline data decoding.
    # For Abyss, this proves the historical60 basis, not60 unchanged current bodies.
    current60 = deepcopy(original)
    current60['hooks'] = deepcopy(basis['hooks'][:60])
    current60['targets'] = deepcopy(basis['targets'])
    before, after = relocation_specs(original), relocation_specs(current60)
    if before != after:
        raise ValueError('Published templates or fixup specifications changed')
    layouts = [(module, ((module+original['image_size']+0xFFFF)&~0xFFFF)+slot*0x10000)
        for module in (0x140000000,0x7FF83AA00000,0x7FFA01000000)
        for slot in (0,1,37,511)]
    count = 0
    for module,allocation in layouts:
        native = assemble(original,module,allocation)
        local = assemble(current60,module,allocation)
        if len(native) != 60 or len(local) != 60:
            raise ValueError('Incomplete original60 assembly')
        for left,right in zip(native,local):
            if (left['name'] != right['name'] or left['payload'] != right['payload']
                    or left['patched'] != right['patched']):
                raise ValueError('Published relocated payload/patch changed: '+left['name'])
            count += 1
    return dict(success=True,game_access=False,hook_count=60,template_comparisons=60,
        fixup_comparisons=60,layout_count=len(layouts),payload_comparisons=count,
        patch_comparisons=count, historical_basis_verified=True,
        current_changed_original_indices=changed, unchanged_current_original_hooks=60-len(changed),
        current_scoped_reconstruction_verified=abyss)


def verify(report: Path | None = None) -> dict:
    baseline = ROOT/'profiles/baseline-beta5.2.json'
    if digest(baseline) != BASELINE_SHA256:
        raise ValueError('Included published baseline differs from its immutable Git blob')
    result = verify_plans(json.loads(baseline.read_text('utf-8')),load_plan())
    result.update(baseline_commit=BASELINE_COMMIT,baseline_git_blob=BASELINE_BLOB,
        baseline_profile_sha256=digest(baseline),
        profile_sha256=digest(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=digest(ROOT/'launcher/Profile.generated.cs'),
        verifier_sha256=digest(Path(__file__)))
    if report is not None:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.report),indent=2))
