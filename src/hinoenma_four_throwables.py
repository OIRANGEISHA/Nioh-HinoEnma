"""Exact ordinary bomb/oil/stone additions to the validated throw helper.

All four definitions select native category4 -> query100 -> common165,
motion103. The existing event engine owns throw, impact and consumption.
This adds definitions only; input handling and other gameplay hooks stay
byte-identical. Kind2 prepared ninjutsu items are intentionally excluded.
"""
from copy import deepcopy
from hinoenma_special_item_actions import _definition_scope, _once
from hinoenma_dung_fan import (
    HELPER_ASM as _PREVIOUS_HELPER, ITEM_SPECS as _PREVIOUS_ITEMS,
    HELPER_OFFSET, CARRIER_NAME, NATIVE_SPANS, SCHEDULE_HEX, EVENT_GUARDS,
)

ITEM_SPECS = (
    (63258,1,14,4,0x10005,(0,0,0),0x6CA47,165,103,100),
    (46857,1,0,4,0x10005,(0,0,0),0xA542B,165,103,100),
    (40896,1,14,4,0x10005,(0,0,0),0xCEFF,165,103,100),
    (4600,1,0,4,0x10005,(0,0,0),0x95249,165,103,100),
)
ALL_ITEM_SPECS = _PREVIOUS_ITEMS + ITEM_SPECS
CHANGED_HOOKS = (CARRIER_NAME,)
HELPER_ASM = _once(_PREVIOUS_HELPER,
    _definition_scope(_PREVIOUS_ITEMS).replace('special_item_', 'dung_fan_'),
    _definition_scope(ALL_ITEM_SPECS).replace('special_item_', 'dung_fan_'))


def apply_four_throwables(previous):
    if (len(previous['hooks']) != 82 or previous.get('harakiri_revision') != 1
            or previous.get('dung_fan_revision') != 1 or previous.get('four_throwables_revision')):
        raise ValueError('Expected the validated82-hook dung/fan revision1 baseline')
    plan=deepcopy(previous)
    carrier=next(h for h in plan['hooks'] if h['name']==CARRIER_NAME)
    if ((carrier['code_offset'],carrier['code_capacity'])!=(0x61000,0x8000)
            or not carrier['asm'].endswith(_PREVIOUS_HELPER)):
        raise ValueError('Expected exact previous throw helper at the private tail')
    carrier['asm']=carrier['asm'][:-len(_PREVIOUS_HELPER)]+HELPER_ASM
    from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
    values={k:0x140000000+rva for k,rva in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'],
        **{'return':0x140000000+carrier['rva']+carrier['length']})
    code,_=Ks(KS_ARCH_X86,KS_MODE_64).asm(carrier['asm'].format(**values),addr=0x144000000+carrier['code_offset'])
    if len(code)>carrier['code_capacity']:
        raise ValueError('Expanded throw helper exceeds the existing private slot')
    carrier['purpose']+='; exact ordinary Horoku-dama, Burning Oil Jar, Kayaku-dama and Stone definitions'
    plan.update(four_throwables_revision=1,four_throwables_item_ids=[x[0] for x in ITEM_SPECS],
        four_throwables_gameplay_confirmation_pending=True,
        four_throwables_direct_inventory_effect_hp_save_writes=False)
    return plan
