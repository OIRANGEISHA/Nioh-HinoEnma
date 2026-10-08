"""Supply the missing native guardian-return component on the Boss player.

760CE7..760DC9 constructs this C0-byte object only for William. Its generic
actor update/destructor already process the paired actor2C0/2C8 pointers.
Death-grave and shrine return requests silently skip77FB20 when2C0 isNULL;
they can remove the grave while leaving the persistent lost flag set.

Construct the same object once on the verified live player's input thread.
Do not request a mode, clear the lost flag, alter guardian selection or gauge,
or synthesize a grave. Subsequent ordinary return requests must drive the
native spawn, animation, lost-flag clearing and stat refresh themselves.
"""
from copy import deepcopy

from hinoenma_guardian_spirit import GUARDIAN_START_ASM


# Keep the reviewed same-pool constructor and failed-alignment cleanup from
# v0.31. Its validation/mode5 section is deliberately absent: this helper only
# ensures an object exists and never initiates an appearance or an attack.
_CONSTRUCT = GUARDIAN_START_ASM.split('living_weapon_guardian_validate:\n', 1)[0]
_CONSTRUCT = _CONSTRUCT.replace(
    'jne living_weapon_guardian_validate\n', 'jne living_weapon_guardian_done\n')
_TAIL = GUARDIAN_START_ASM.split('living_weapon_guardian_free_unaligned:\n', 1)[1]
GUARDIAN_RECOVERY_ENSURE_ASM = (
    _CONSTRUCT + 'jmp living_weapon_guardian_done\n'
    + 'living_weapon_guardian_free_unaligned:\n' + _TAIL
).replace('living_weapon_guardian_', 'guardian_recovery_').replace(
    'guardian_recovery_start:', 'guardian_recovery_ensure:')


ENSURE_CALL = '''cmp word ptr [r10+0x04], 0
jne living_weapon_block_input
mov eax, dword ptr [r10]
cmp eax, dword ptr [r11+0x04]
jne living_weapon_block_input
mov rcx, qword ptr [r10+0xE90]
cmp eax, dword ptr [rcx]
jne living_weapon_block_input
cmp qword ptr [rdx+0x18], 0
jle living_weapon_block_input
cmp qword ptr [rdx+0x20], 0
jle living_weapon_block_input
mov rcx, qword ptr [r10+0x230]
test rcx, rcx
je living_weapon_block_input
cmp r10, qword ptr [rcx]
jne living_weapon_block_input
cmp rsi, qword ptr [rcx+8]
jne living_weapon_block_input
cmp qword ptr [r10+0x2C0], 0
jne guardian_recovery_frame_ready
cmp qword ptr [r10+0x2C8], 0
jne guardian_recovery_frame_ready
mov rcx, r10
call guardian_recovery_ensure
mov r11, {data}
mov r10, qword ptr [r11+0x10]
mov rdx, qword ptr [r10+0x240]
guardian_recovery_frame_ready:
'''


def apply_guardian_recovery(previous):
    if previous.get('tool_version') != '0.40' or len(previous['hooks']) != 45:
        raise ValueError('Guardian-return component requires complete v0.40')
    plan = deepcopy(previous)
    hook = next(h for h in plan['hooks'] if h['name'] == 'HE_LivingWeaponDigitNine')
    marker = '''cmp r10, qword ptr [rdx+0x108]
jne living_weapon_block_input
mov eax, dword ptr [r11+0x1C]
'''
    if hook['asm'].count(marker) != 1 or hook['code_offset'] != 0xD000:
        raise ValueError('Unexpected verified player-frame hook')
    hook['asm'] = hook['asm'].replace(marker, marker.rsplit('mov eax', 1)[0]
                                    + ENSURE_CALL + 'mov eax, dword ptr [r11+0x1C]\n')
    hook['asm'] += GUARDIAN_RECOVERY_ENSURE_ASM
    hook['purpose'] += ('; construct missing native guardian-return component once on '
        'the verified live input thread; preserve ordinary death/grave/shrine requests, '
        'persistent lost state, selected guardian, charge, return animation and cleanup')
    plan.update(tool_version='0.41', guardian_recovery_component_revision=1,
                stage='native_guardian_return_component',
                guardian_recovery_gameplay_confirmation_pending=True)
    return plan
