"""Keep native injuries in the common bank after a cast returns to movement.

The captured failure left Kunai for common movement 1015, then resolved a
selected common injury 89 as Boss action 89. Only the current-state eligibility
of the existing guarded injury lookup is extended. Movement inputs, damage,
stock, native queries and persistent player state are not modified.
"""
from copy import deepcopy

from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_general_jutsu import digest
from hinoenma_special_item_actions import _once
from hinoenma_item_hurt_lookup import CODE_CARRIER

PARENT_SHA256 = 'e76ed7d24977bb5d1e43afe42f2bcda48a0882d569b4b1986cebf4a237c99429'
MOVEMENT_MOTIONS = {1002:-1, 1003:20, 1004:24, 1015:26, 1016:28,
                    1017:-1, 1018:30, 1019:31, 1020:32, 1021:33}
EMPTY_SCHEDULE = bytes.fromhex('ffff0000ffff' * 16)
RECAST_OFFSET = 0x23A00


def movement_scope():
    text = ''
    for action, motion in MOVEMENT_MOTIONS.items():
        text += f'''cmp edx, {action}
jne jutsu_move_hurt_next_{action}
mov eax, {motion}
jmp jutsu_move_hurt_contract
jutsu_move_hurt_next_{action}:
'''
    text += '''jmp item_hurt_reject
jutsu_move_hurt_contract:
cmp dword ptr [r10+0x20], eax
jne item_hurt_reject
cmp dword ptr [r10+0x34], -1
jne item_hurt_reject
lea rdi, [r10+0x40]
mov ecx, 16
jutsu_move_hurt_schedule:
cmp word ptr [rdi], 0xFFFF
jne item_hurt_reject
cmp dword ptr [rdi+2], 0xFFFF0000
jne item_hurt_reject
add rdi, 6
dec ecx
jne jutsu_move_hurt_schedule
jmp item_hurt_find_route
'''
    return text


def apply_general_jutsu_recovery(previous):
    if digest(previous) != PARENT_SHA256:
        raise ValueError('Exact tested timing and consecutive-throw candidate required')
    plan = deepcopy(previous)
    hook = next(h for h in plan['hooks'] if h['name'] == CODE_CARRIER)
    head, separator, tail = hook['asm'].partition('item_recast_movement_guard:\n')
    if not separator or separator in tail or hook['code_offset'] != 0x23000:
        raise ValueError('Expected single movement-recast helper in its owned carrier')
    head = head.rstrip()
    while head.endswith('nop'):
        head = head[:-3].rstrip()
    head += '\n'
    anchor = 'jutsu_chain_hurt_next_613:\njmp item_hurt_reject\nitem_hurt_cast_found:\n'
    head = _once(head, anchor, 'jutsu_chain_hurt_next_613:\n' + movement_scope() + 'item_hurt_cast_found:\n')
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    values = {k:0x140000000+v for k,v in plan['targets'].items()}
    values.update(data=0x14400F000, **{'return':0x140000000+hook['rva']+hook['length']})
    origin = 0x144000000+hook['code_offset']
    raw = bytes(ks.asm(head.format(**values), origin)[0])
    gap = RECAST_OFFSET-hook['code_offset']-len(raw)
    if gap < 0:
        raise ValueError('Injury eligibility exceeds reserved prefix space')
    # Restore the fixed recast entry; no consumer depends on its earlier NOP landing pad.
    hook['asm'] = head + 'nop\n'*gap + separator + tail
    complete = bytes(ks.asm(hook['asm'].format(**values), origin)[0])
    if len(complete) > hook['code_capacity']:
        raise ValueError('Owned injury/recast carrier capacity exceeded')
    plan['general_jutsu_recovery_candidate'] = dict(
        revision=1, changed_hooks=[CODE_CARRIER], movement_actions=sorted(MOVEMENT_MOTIONS),
        exact_alternate_and_empty_schedule=True, selected_native_injury_required=True,
        native_queries_unchanged=True, movement_inputs_unchanged=True,
        damage_ki_stock_writes=False, persistent_state=False,
        live_confirmation_pending=True)
    return plan
