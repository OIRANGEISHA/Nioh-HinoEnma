"""Three exact native item actions, without direct inventory/effect writes.

The two dung balls use common165/motion103; Tengu's Fan uses1225/150.
Native common172 selects the action and its scheduled events own objects,
attacks and consumption. Historical special-item payloads stay identical.
"""
from copy import deepcopy
from hinoenma_special_item_actions import (
    HELPER_ASM as _PREVIOUS_HELPER, _definition_scope, _schedules, _once,
    SCHEDULE_HEX as _OLD_SCHEDULES, EVENT_GUARDS as _OLD_GUARDS,
)

HELPER_OFFSET = 0x65000
CARRIER_NAME = 'HE_LivingWeaponDigitNine'
CHANGED_HOOKS = ('HE_InputA', 'HE_InputB', 'HE_HimorogiFragment', CARRIER_NAME)
ITEM_SPECS = (
    (32016,1,0,4,0x10005,(0,0,0),0xCFEB0,165,103,100),
    (6518,1,0,4,0x10005,(0,0,0),0x9909E,165,103,100),
    (44220,1,0,29,0x10005,(0,0,0),0x11193,1225,150,436),
)
SCHEDULE_HEX = {
    165: _OLD_SCHEDULES[165],
    1225: 'a6000000ffff1e007800ffffa7004a00ffff13004a00010014000200ffff5a002d00ffff11274100ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
}
EVENT_GUARDS = {
    165: _OLD_GUARDS[165],
    1225: ((19,-1,-1,-1,0,255,-1),(20,-1,-1,-1,255,18,-1),
           (30,0,-1,-1,255,255,-1),(90,-1,-1,-1,255,7,-1),
           (166,2,991726,22,255,255,-1),(167,1,70035,0,255,255,-1),
           (10001,-1,-1,-1,255,0,-1)),
}
NATIVE_SPANS = ((0x706070,0x4B),(0x73FA45,0xCC),(0x917500,0xBC),
                (0x7324E0,0x81),(0x738026,0x2F),(0x7384BD,0x2F),
                (0x73AC90,4),(0x73B1D0,4),(0x708C3B,0x7B),
                (0x70A522,0x88),(0x6DFED0,0x45))

HELPER_ASM = _once(_PREVIOUS_HELPER, _definition_scope(), _definition_scope(ITEM_SPECS))
HELPER_ASM = _once(HELPER_ASM, _schedules(), _schedules(SCHEDULE_HEX, EVENT_GUARDS))
# Both initial validation and post-lookup validation reject an open dialog.
if HELPER_ASM.count('cmp qword ptr [rdi+0x728], 0\n') != 2:
    raise ValueError('Expected initial and final queue validation')
HELPER_ASM = HELPER_ASM.replace('cmp qword ptr [rdi+0x728], 0\n',
    'cmp byte ptr [rdi+0x570], 0\njne special_item_restore\n'
    'cmp qword ptr [rdi+0x728], 0\n')
HELPER_ASM = HELPER_ASM.replace('special_item_', 'dung_fan_')


def apply_dung_fan(previous):
    """Pure trial transform on the existing82-hook Harakiri revision1 plan."""
    if (len(previous['hooks']) != 82 or previous.get('harakiri_revision') != 1
            or previous.get('dung_fan_revision')):
        raise ValueError('Expected82-hook Harakiri revision1 baseline')
    plan=deepcopy(previous)
    carrier=next(h for h in plan['hooks'] if h['name']==CARRIER_NAME)
    fragment=next(h for h in plan['hooks'] if h['name']=='HE_HimorogiFragment')
    if (carrier['code_offset'],carrier['code_capacity'])!=(0x61000,0x8000):
        raise ValueError('Unexpected existing private carrier layout')
    for name,suffix in (('HE_InputA','a'),('HE_InputB','b')):
        h=next(h for h in plan['hooks'] if h['name']==name)
        anchor=f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        h['asm']=_once(h['asm'],anchor,
            f'mov ecx, 150\ncmp dword ptr [rdx], 1225\nje special_item_input_found_{suffix}\n'+anchor)
    anchor='call {data} + 0x2A00\n'
    fragment['asm']=_once(fragment['asm'],anchor,
        anchor+'call {data} + '+hex(HELPER_OFFSET-plan['data_offset'])+'\n')
    from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    values={key:0x140000000+rva for key,rva in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'],
        **{'return':0x140000000+carrier['rva']+carrier['length']})
    old,_=ks.asm(carrier['asm'].format(**values),addr=0x144000000+carrier['code_offset'])
    new,_=ks.asm(HELPER_ASM.format(**values),addr=0x144000000+HELPER_OFFSET)
    padding=HELPER_OFFSET-carrier['code_offset']-len(old)
    if padding<0 or HELPER_OFFSET+len(new)>carrier['code_offset']+carrier['code_capacity']:
        raise ValueError('Owned code tail occupied or helper exceeds capacity')
    carrier['asm']+='\n'+'nop\n'*padding+HELPER_ASM
    carrier['purpose']+='; dormant tail holds exact dung-ball and Tengu-fan action entry'
    plan.update(dung_fan_revision=1,dung_fan_item_ids=[x[0] for x in ITEM_SPECS],
        dung_fan_helper_offset=HELPER_OFFSET,dung_fan_gameplay_confirmation_pending=True,
        dung_fan_direct_inventory_effect_hp_save_writes=False)
    return plan
