"""Offline source/CT identity, numeric, label, and ASLR checks; no game access."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from build_profile import (ROOT, aa_source, assemble, ct_render_plan, ct_source,
    generate, load_plan, validate_ct_labels)
from living_weapon_start_ct import ct_compatible_plan


def rejected(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError('Modified CT input or label was accepted')


def verify():
    plan = load_plan()
    if plan['tool_version'] != '1.0.0-beta.6.1.1' or len(plan['hooks']) != 82:
        raise ValueError('Exact Beta 6.1.1 source required')
    before = deepcopy(plan)
    converted = ct_compatible_plan(plan)
    rendered, labels = ct_render_plan(converted)
    text = aa_source(plan)
    validate_ct_labels(text, labels)
    if text != aa_source(converted):
        raise AssertionError('Raw and explicitly converted CT differ')
    if f'alloc(HE_Prototype_Code,{plan["allocation_size"]:X},nioh.exe+89B424)' not in text:
        raise AssertionError('Full CT allocation missing')
    if 'error("资源寿命版不支持游戏运行中卸载' not in text:
        raise AssertionError('Live unload guard missing')
    version = json.loads((ROOT / 'version.json').read_text('utf-8'))
    source = ct_source(plan, version['display_version'])
    ct = ROOT / 'ct' / version['ct_file']
    if ct.read_text('utf-8') != source:
        raise AssertionError('Checked-in CT differs from generated source')
    doc = ET.fromstring(source)
    if doc.find('./CheatEntries/CheatEntry/AssemblerScript').text != text:
        raise AssertionError('CT XML assembler source differs')
    if (ROOT / 'launcher/Profile.generated.cs').read_text('utf-8') != generate(plan):
        raise AssertionError('Current EXE source differs')
    count = 0
    for module in (0x140000000, 0x7FF83AA00000, 0x7FFA01000000):
        for slot in (0, 1, 37, 511):
            allocation = ((module + plan['image_size'] + 0xFFFF) & ~0xFFFF) + slot * 0x10000
            raw = assemble(plan, module, allocation)
            numeric = assemble(converted, module, allocation)
            named = assemble(rendered, module, allocation)
            for a, b, c in zip(raw, numeric, named):
                for key in ('payload', 'patched'):
                    if not a[key] == b[key] == c[key]:
                        raise AssertionError('CT numeric/namespace change: ' + a['name'])
                count += 1
    for mutate in (lambda p: p.update(allocation_size=0x55000),
                   lambda p: p['hooks'][0].update(asm=p['hooks'][0]['asm'] + '\nnop'),
                   lambda p: p['hooks'][36].update(code_offset=0xD000)):
        bad = deepcopy(plan)
        mutate(bad)
        rejected(lambda: ct_compatible_plan(bad))
    rejected(lambda: validate_ct_labels(text + '\n' + labels[0] + ':\n', labels))
    rejected(lambda: validate_ct_labels(text.replace('label(' + labels[0] + ')\n', '', 1), labels))
    if plan != before:
        raise AssertionError('CT conversion mutated source input')
    forbidden = ('nioh_probe', 'runtime_probe', 'code_inspect')
    if any(name in sys.modules for name in forbidden):
        raise AssertionError('Private game dependency imported')
    for name, module in list(sys.modules.items()):
        if name.startswith(('hinoenma_', 'living_weapon_start_')):
            path = getattr(module, '__file__', '')
            if not str(path).lower().startswith(str(ROOT / 'src').lower()):
                raise AssertionError('Source import escaped package: ' + name)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(success=True, version=plan['tool_version'], game_access=False,
        hook_count=82, layout_count=12, three_way_payload_comparisons=count,
        native_patch_comparisons=count, ct_local_labels=len(labels),
        source_input_unchanged=True, negative_guards=5,
        private_dependencies_imported=False, ct_direct_gameplay_tested=False,
        profile_sha256=sha(ROOT/'profiles/steam-1.24.8.json'),
        generated_source_sha256=sha(ROOT/'launcher/Profile.generated.cs'),
        ct_sha256=sha(ct), ct_bytes=ct.stat().st_size,
        verifier_sha256=sha(Path(__file__)),
        converter_sha256=sha(ROOT/'src/living_weapon_start_ct.py'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    result = verify()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
