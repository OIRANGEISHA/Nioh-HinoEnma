"""Build the level750 candidate without changing the public release artifacts."""
from pathlib import Path
import argparse
import hashlib
import json

from build_profile import load_plan, assemble
from hinoenma_growth750 import apply_growth750, HOOK_NAME


def build(output):
    from build_profile import ROOT, source_plan_beta562
    previous = source_plan_beta562(json.loads((ROOT / 'profiles/legacy-beta5.6.2.json').read_text('utf-8')))
    plan = apply_growth750(previous)
    sizes = []
    for base, allocation in ((0x140000000, 0x144000000),
                              (0x7FF600000000, 0x7FF604000000),
                              (0x180000000, 0x176000000)):
        old, new = assemble(previous, base, allocation), assemble(plan, base, allocation)
        changed = [a['name'] for a, b in zip(old, new) if a['payload'] != b['payload']]
        if changed != [HOOK_NAME]:
            raise ValueError('Only the attribute payload may change')
        if any(a['patched'] != b['patched'] for a, b in zip(old, new)):
            raise ValueError('Native entry patches must not change')
        hook = next(h for h in new if h['name'] == HOOK_NAME)
        sizes.append(len(hook['payload']))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return dict(path=str(output), sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                hook_count=len(plan['hooks']), changed_hooks=changed,
                payload_sizes=sizes, capacity=hook['code_capacity'],
                release_artifacts_unchanged=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(json.dumps(build(parser.parse_args().output)))
