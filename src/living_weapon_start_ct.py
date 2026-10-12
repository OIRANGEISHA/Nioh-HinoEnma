"""Strict Cheat Engine numeric conversion of the canonical Beta5.6.1 source."""
from copy import deepcopy


def ct_compatible_plan(plan):
    from build_profile import load_plan
    from living_weapon_start_production_layout import validate_production_layout
    from menu_preview_portable_integration import frozen
    validate_production_layout(plan)
    if plan != load_plan():
        raise ValueError('Exact reconstructed Beta5.6.1 source required for CT conversion')
    result = deepcopy(plan)
    for hook in result['hooks']:
        hook['asm'] = '\n'.join(
            line if line.lstrip().startswith('.byte ') else
            frozen.SOURCE_NUMBER.sub(lambda match: hex(int(match.group(0),
                16 if match.group(0).lower().startswith('0x') else 10)), line)
            for line in hook['asm'].split('\n'))
    return result
