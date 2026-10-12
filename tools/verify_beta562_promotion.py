"""Verify all runtime bytes against the independently exported cold-tested EXE."""
import argparse
import hashlib
import json
from pathlib import Path
from build_profile import ROOT, assemble, load_plan


def digest(rows):
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda row: row['name']):
        for value in (row['name'].encode(), row['payload'], row['patched']):
            h.update(len(value).to_bytes(8, 'little'))
            h.update(value)
    return h.hexdigest()


def verify():
    basis = json.loads((ROOT/'docs/beta562-tested-payloads.json').read_text('utf-8'))
    plan = load_plan()
    if (plan['tool_version'] != '1.0.0-beta.5.6.2' or len(plan['hooks']) != 82
            or basis['tested_executable_sha256'] != '004f0000b0411218ee6dd94f39a5b69c189f6bd48fde875db135dea693dd5b7f'
            or basis['tested_profile_sha256'] != '6ac7bc436bb3870682b0e399d451cfd26501d51f44ba7343c67f117070918773'):
        raise ValueError('Exact tested basis and release scope required')
    expected = {(m, ((m+plan['image_size']+0xFFFF)&~0xFFFF)+s*0x10000)
                for m in (0x140000000,0x7FF83AA00000,0x7FFA01000000) for s in (0,1,37,511)}
    if len(basis['layouts']) != 12 or {(r['module'],r['allocation']) for r in basis['layouts']} != expected:
        raise ValueError('Complete relocation inventory required')
    for row in basis['layouts']:
        hooks = assemble(plan,row['module'],row['allocation'])
        if len(hooks) != 82 or digest(hooks) != row['sha256']:
            raise ValueError('Runtime bytes differ from cold-tested binary')
    return dict(version=plan['tool_version'],success=True,game_access=False,
        tested_executable_sha256=basis['tested_executable_sha256'],
        tested_profile_sha256=basis['tested_profile_sha256'],
        release_profile_sha256=hashlib.sha256((ROOT/'profiles/steam-1.24.8.json').read_bytes()).hexdigest(),
        payload_comparisons=984,native_patch_comparisons=984,layout_count=12,
        runtime_payloads_identical=True,exact_release_executable_gameplay_tested=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'artifacts/promotion-verification.json')
    args=parser.parse_args()
    result=verify()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))
