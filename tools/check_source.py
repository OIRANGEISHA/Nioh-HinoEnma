"""Check portable source regeneration and CT labels without game files.

These checks exercise the public source chain and assembly layout only.
They do not reproduce the private native-CPU or gameplay verification.
"""
from __future__ import annotations

from copy import deepcopy
import json
import sys

from build_profile import (
    ROOT, assemble, aa_source, ct_render_plan, load_plan, source_plan,
    legacy_plans, validate_ct_labels, validate_layout,
)


def rejects(callback, message: str) -> None:
    try:
        callback()
    except ValueError:
        return
    raise AssertionError(message)


def main() -> None:
    frozen = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
    original = deepcopy(frozen)
    plan = load_plan()
    if len(plan['hooks']) != 70 or source_plan(frozen)['tool_version'] != '1.0.0-beta.5.3':
        raise AssertionError('Expected the complete current source chain')
    if frozen != original:
        raise AssertionError('Source reconstruction changed its frozen input')
    forbidden_imports = ('nioh_probe', 'runtime_probe', 'code_inspect')
    if any(name in sys.modules for name in forbidden_imports) or any(
            name.startswith('verify_hinoenma_') for name in sys.modules):
        raise AssertionError('Public source reconstruction imported a private dependency')
    for name, module in list(sys.modules.items()):
        if name.startswith('hinoenma_'):
            path = getattr(module, '__file__', None)
            if path is None or not str(path).lower().startswith(str(ROOT / 'src').lower()):
                raise AssertionError('Hino-Enma source escaped the public tree: ' + name)
    rendered, labels = ct_render_plan(plan)
    if len(labels) < 275 or len(labels) != len(set(labels)):
        raise AssertionError('Current CT local-label inventory is incomplete or duplicated')
    text = aa_source(plan)
    if f'alloc(HE_Prototype_Code,{plan["allocation_size"]:X},nioh.exe+89B424)' not in text:
        raise AssertionError('CT allocation differs from the complete source layout')
    validate_ct_labels(text, labels)
    comparisons = 0
    layouts = 0
    for module in (0x140000000, 0x7FF600000000, 0x180000000):
        for slot in (0, 1, 37, 511):
            allocation = module + 0x4000000 + slot * 0x10000
            before = assemble(plan, module, allocation)
            after = assemble(rendered, module, allocation)
            for left, right in zip(before, after):
                if left['payload'] != right['payload'] or left['patched'] != right['patched']:
                    raise AssertionError('CT namespace changed assembled code: ' + left['name'])
                comparisons += 1
            layouts += 1
    invalid = deepcopy(frozen)
    invalid['hooks'][0]['length'] += 1
    rejects(lambda: source_plan(invalid), 'Changed entry signature was accepted')
    rejects(lambda: validate_ct_labels(text + '\n' + labels[0] + ':\n', labels),
            'Duplicate CT definition was accepted')
    missing = text.replace('label(' + labels[0] + ')\n', '', 1)
    rejects(lambda: validate_ct_labels(missing, labels), 'Missing CT declaration was accepted')
    for offset in (0xF000, 0x13000, 0x1F000, 0x24000, 0x29000, 0x2C000):
        invalid = deepcopy(plan)
        invalid['hooks'][-1]['code_offset'] = offset
        rejects(lambda: validate_layout(invalid), 'Code capacity in protected data was accepted')
    previous = legacy_plans(frozen)
    if [(len(item['hooks']), item['allocation_size']) for item in previous] != [
            (55, 0x19000), (59, 0x1B000), (60, 0x20000)]:
        raise AssertionError('Historical complete allocation identities differ')
    if frozen != original:
        raise AssertionError('Legacy reconstruction changed its frozen input')
    print(json.dumps(dict(success=True, game_access=False,
        private_dependencies_imported=False, hook_count=len(plan['hooks']), ct_local_labels=len(labels),
        source_input_unchanged=True, layout_count=layouts,
        ct_namespace_payload_comparisons=comparisons, negative_guards=6,
        historical_hook_counts=[len(item['hooks']) for item in previous],
        protected_data_pages=[0xF000, 0x13000, 0x1F000, 0x24000, 0x29000, 0x2C000])))


if __name__ == '__main__':
    main()
