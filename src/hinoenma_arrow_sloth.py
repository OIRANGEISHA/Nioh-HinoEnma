"""Exact Arrowproof/Sloth native casts, with stock and effects owned by the game.

Arrowproof64367 uses common41/motion110; prepared Sloth4998 uses42/111.
The helper enters common172 and lets native queries192/194 select the route,
including the original fast-cast branch. Kind2 stock is never emulated.
"""
from copy import deepcopy
from hinoenma_special_item_actions import _definition_scope, _schedules, _once
from hinoenma_four_throwables import (
    HELPER_ASM as _PREVIOUS_HELPER, ALL_ITEM_SPECS as _PREVIOUS_ITEMS,
    HELPER_OFFSET, CARRIER_NAME, SCHEDULE_HEX as _PREVIOUS_SCHEDULES,
    EVENT_GUARDS as _PREVIOUS_GUARDS, NATIVE_SPANS as _PREVIOUS_NATIVE_SPANS,
)

ITEM_SPECS = (
    (64367,1,0,7,0x10005,(45657,0,0),0,41,110,192),
    (4998,2,15,9,5,(0,0,0),0x42B17,42,111,194),
)
ALL_ITEM_SPECS = _PREVIOUS_ITEMS + ITEM_SPECS
CHANGED_HOOKS = ('HE_InputA', 'HE_InputB', CARRIER_NAME)
SCHEDULE_HEX = {
    **_PREVIOUS_SCHEDULES,
    41: '11001800ffff13006400ffff1e006e00ffffffff0000ffffffff0000ffffffff0000ffff7a00320014008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    42: '11001100ffff1f006800ffff14000000320011273200280014005a000e0011276800ffff7a00320019008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
}
EVENT_GUARDS = {
    **_PREVIOUS_GUARDS,
    41: ((17,6,-1,21,255,255,-1), (19,-1,-1,-1,0,255,-1),
         (30,0,-1,-1,255,255,-1), (122,-1,-1,-1,255,255,-1),
         (142,-1,-1,-1,255,255,-1), (143,-1,-1,-1,255,255,-1)),
    42: ((17,6,-1,21,255,255,-1), (31,5,-1,-1,255,255,-1),
         (20,-1,-1,-1,255,18,-1), (10001,-1,-1,-1,255,0,-1),
         (122,-1,-1,-1,255,255,-1), (142,-1,-1,-1,255,255,-1),
         (143,-1,-1,-1,255,255,-1)),
}
NATIVE_SPANS = _PREVIOUS_NATIVE_SPANS + (
    (0x7380B3,0x2F), (0x738111,0x2F), (0x73AE00,4), (0x73AE08,4),
    (0x70879E,0x65), (0x763F82,0x66), (0x8F7D00,0xAD), (0x8F7E0C,0xA0),
)
HELPER_ASM = _once(_PREVIOUS_HELPER,
    _definition_scope(_PREVIOUS_ITEMS).replace('special_item_', 'dung_fan_'),
    _definition_scope(ALL_ITEM_SPECS).replace('special_item_', 'dung_fan_'))
HELPER_ASM = _once(HELPER_ASM,
    _schedules(_PREVIOUS_SCHEDULES, _PREVIOUS_GUARDS).replace('special_item_', 'dung_fan_'),
    _schedules(SCHEDULE_HEX, EVENT_GUARDS).replace('special_item_', 'dung_fan_'))


def apply_arrow_sloth(previous):
    """Pure, reversible transform of the validated four-throwable revision1."""
    if (len(previous['hooks']) != 82 or previous.get('harakiri_revision') != 1
            or previous.get('dung_fan_revision') != 1
            or previous.get('four_throwables_revision') != 1
            or previous.get('arrow_sloth_revision')):
        raise ValueError('Expected the validated82-hook four-throwable revision1 baseline')
    plan = deepcopy(previous)
    carrier = next(h for h in plan['hooks'] if h['name'] == CARRIER_NAME)
    if ((carrier['code_offset'], carrier['code_capacity']) != (0x61000, 0x8000)
            or not carrier['asm'].endswith(_PREVIOUS_HELPER)):
        raise ValueError('Expected exact previous item helper at the private tail')
    carrier['asm'] = carrier['asm'][:-len(_PREVIOUS_HELPER)] + HELPER_ASM
    for name, suffix in (('HE_InputA','a'), ('HE_InputB','b')):
        h = next(h for h in plan['hooks'] if h['name'] == name)
        anchor = f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        h['asm'] = _once(h['asm'], anchor,
            f'mov ecx, 110\ncmp dword ptr [rdx], 41\nje special_item_input_found_{suffix}\n'
            f'mov ecx, 111\ncmp dword ptr [rdx], 42\nje special_item_input_found_{suffix}\n' + anchor)
    from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    values = {key:0x140000000+rva for key,rva in plan['targets'].items()}
    values['data'] = 0x144000000 + plan['data_offset']
    for h in plan['hooks']:
        if h['name'] not in CHANGED_HOOKS:
            continue
        values['return'] = 0x140000000 + h['rva'] + h['length']
        code,_ = ks.asm(h['asm'].format(**values), addr=0x144000000+h['code_offset'])
        if len(code) > h['code_capacity']:
            raise ValueError('Arrowproof/Sloth exceeds existing code capacity: '+h['name'])
    carrier['purpose'] += '; exact Arrowproof64367 and prepared Sloth4998 native casts'
    plan.update(arrow_sloth_revision=1, arrow_sloth_item_ids=[x[0] for x in ITEM_SPECS],
        arrow_sloth_gameplay_confirmation_pending=True,
        arrow_sloth_direct_inventory_effect_hp_save_writes=False)
    return plan
