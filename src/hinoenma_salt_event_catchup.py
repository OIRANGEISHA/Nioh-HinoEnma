"""One native event catch-up for the observed owned Salt 0 -> 16 gap.

The frame-zero call arms private state. Only its next owned call with the
observed frame16/step1/R9B0 inputs receives R9B1. Native scheduling, event
creation, item use and cleanup remain native. This is an experimental Salt
event repair; received-damage compatibility remains unresolved.
"""
from copy import deepcopy

NAME = 'HE_SaltEventCatchup'
SITE = 0x718950
OFFSET = 0x1040
CAPACITY = 0x3C0
STATE_OFFSET = 0x13E80
STATE_SIZE = 0x40

ASM = '''pushfq
push rax
push r10
push r11
push r9
test rcx, rcx
je salt_catchup_restore
cmp qword ptr [rcx+0x58], rdx
jne salt_catchup_restore
test rdx, rdx
je salt_catchup_restore
cmp dword ptr [rdx], 982
jne salt_catchup_restore
cmp byte ptr [rdx+0x40], 0
je salt_catchup_restore
cmp dword ptr [rcx+0x68], 2
jne salt_catchup_restore
mov r10, qword ptr [rcx+0x80]
test r10, r10
je salt_catchup_restore
cmp qword ptr [rdx+0x38], r10
jne salt_catchup_restore
mov r10, qword ptr [rdx+0x20]
test r10, r10
je salt_catchup_restore
cmp dword ptr [r10+0x20], 120
jne salt_catchup_restore
cmp dword ptr [r10+0x40], 0x000F0011
jne salt_catchup_restore
cmp word ptr [r10+0x44], 0xFFFF
jne salt_catchup_restore
cmp dword ptr [r10+0x46], 0x0023001F
jne salt_catchup_restore
cmp word ptr [r10+0x4A], 0xFFFF
jne salt_catchup_restore
cmp dword ptr [r10+0x4C], 0x00020014
jne salt_catchup_restore
cmp word ptr [r10+0x50], 15
jne salt_catchup_restore
cmp dword ptr [rcx+0x548], 7739
jne salt_catchup_restore
mov r10, qword ptr [rcx+0x50]
test r10, r10
je salt_catchup_restore
mov r11, {player_slot}
cmp qword ptr [r11], r10
jne salt_catchup_restore
mov r11, {data}
cmp qword ptr [r11+0x10], r10
jne salt_catchup_restore
cmp dword ptr [r10+4], 0x10000
jne salt_catchup_restore
mov eax, dword ptr [r10]
cmp eax, dword ptr [r11+4]
jne salt_catchup_restore
cmp eax, 0x58E5E
je salt_catchup_role
cmp eax, 0x51BE1
jne salt_catchup_restore
salt_catchup_role:
cmp dword ptr [r10+0xEF0], 0
jne salt_catchup_restore
cmp dword ptr [r11+0x1C], 0
je salt_catchup_restore
mov rax, qword ptr [r10+0xE90]
test rax, rax
je salt_catchup_restore
cmp dword ptr [rax+0xC], 1
jne salt_catchup_restore
mov eax, dword ptr [rax]
cmp eax, dword ptr [r10]
jne salt_catchup_restore
mov rax, qword ptr [r10+0x230]
test rax, rax
je salt_catchup_restore
cmp qword ptr [rax], r10
jne salt_catchup_restore
cmp qword ptr [rax+8], rcx
jne salt_catchup_restore
mov rax, qword ptr [r10+0x240]
test rax, rax
je salt_catchup_restore
cmp qword ptr [rax], r10
jne salt_catchup_restore
cmp qword ptr [rax+0x108], r10
jne salt_catchup_restore
cmp qword ptr [rax+0x20], 0
jle salt_catchup_restore
mov rax, qword ptr [r10+0x38]
test rax, rax
je salt_catchup_restore
cmp dword ptr [rax+0x48], 2
jne salt_catchup_restore
cmp dword ptr [rax+0x50], 0
jne salt_catchup_restore
cmp r9b, 1
je salt_catchup_first
cmp r9b, 0
jne salt_catchup_disarm
cmp dword ptr [r11+0x4E80], 1
jne salt_catchup_restore
mov eax, dword ptr [r11+0x1C]
cmp dword ptr [r11+0x4E84], eax
jne salt_catchup_disarm
cmp qword ptr [r11+0x4E88], r10
jne salt_catchup_disarm
cmp qword ptr [r11+0x4E90], rcx
jne salt_catchup_disarm
cmp qword ptr [r11+0x4E98], rdx
jne salt_catchup_disarm
mov eax, 1
xor r10d, r10d
lock cmpxchg dword ptr [r11+0x4E80], r10d
jne salt_catchup_restore
movd eax, xmm2
cmp eax, 0x41800000
jne salt_catchup_restore
cmp dword ptr [rcx+0x24], 0x3F800000
jne salt_catchup_restore
mov byte ptr [rsp], 1
jmp salt_catchup_restore
salt_catchup_first:
mov dword ptr [r11+0x4E80], 0
movd eax, xmm2
test eax, eax
jne salt_catchup_restore
cmp dword ptr [rcx+0x24], 0x3F800000
jne salt_catchup_restore
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0x4E84], eax
mov qword ptr [r11+0x4E88], r10
mov qword ptr [r11+0x4E90], rcx
mov qword ptr [r11+0x4E98], rdx
mov dword ptr [r11+0x4E80], 1
jmp salt_catchup_restore
salt_catchup_disarm:
mov dword ptr [r11+0x4E80], 0
salt_catchup_restore:
pop r9
pop r11
pop r10
pop rax
popfq
call {salt_catchup_native_schedule}
jmp {return}
'''

# A rejected call on the tracked controller also breaks the observed sequence.
# Clear only the private marker; a different controller cannot consume it.
_scope, _sequence = ASM.split('cmp r9b, 1\n', 1)
_scope = _scope.replace('salt_catchup_restore', 'salt_catchup_reject')
ASM = _scope + 'cmp r9b, 1\n' + _sequence
ASM = ASM.replace('salt_catchup_disarm:\n', '''salt_catchup_reject:
mov r11, {data}
cmp dword ptr [r11+0x4E80], 1
jne salt_catchup_restore
cmp qword ptr [r11+0x4E90], rcx
jne salt_catchup_restore
salt_catchup_disarm:
''', 1)

# Reject any extra reference that a catch-up window could unexpectedly replay.
# This preserves the exact three-reference Salt schedule used by the witness.
_unused_refs = '\n'.join(
    f'cmp word ptr [r10+{0x40 + slot * 6}], 0xFFFF\njne salt_catchup_reject'
    for slot in range(3, 16)) + '\n'
ASM = ASM.replace('cmp dword ptr [rcx+0x548], 7739\n',
                  _unused_refs + 'cmp dword ptr [rcx+0x548], 7739\n', 1)


def apply_salt_event_catchup(containment, salt_source, original):
    if (containment.get('tool_version') != '0.53'
            or salt_source.get('tool_version') != '0.52'
            or len(containment.get('hooks', ())) != 49
            or len(salt_source.get('hooks', ())) != 49
            or original != bytes.fromhex('E8 FB C4 FE FF')
            or (containment.get('allocation_size'), containment.get('data_offset')) != (0x14000, 0xF000)):
        raise ValueError('Exact frozen v0.53/v0.52 and original704E50 call required')
    plan = deepcopy(containment)
    for index in (6, 7, 48):
        for field in ('name', 'rva', 'length', 'code_offset', 'original'):
            if plan['hooks'][index].get(field) != salt_source['hooks'][index].get(field):
                raise ValueError('Frozen salt branches have different native sites')
        plan['hooks'][index] = deepcopy(salt_source['hooks'][index])
    carrier = plan['hooks'][4]
    if (carrier['name'], carrier['code_offset'], carrier.get('code_capacity', 0x400)) != ('HE_Equipment', 0x1000, 0x400):
        raise ValueError('Exact Equipment unused tail required')
    carrier['code_capacity'] = 0x40
    plan['targets']['salt_catchup_native_schedule'] = 0x704E50
    plan['hooks'].append(dict(name=NAME, rva=SITE, length=5, code_offset=OFFSET,
        code_capacity=CAPACITY, original=original.hex(' ').upper(), asm=ASM))
    plan.update(tool_version='0.55-experimental', stage='unverified_salt_event_catchup',
        salt_event_catchup=True, salt_event_catchup_state_offset=STATE_OFFSET,
        salt_event_catchup_state_size=STATE_SIZE, salt_event_catchup_observed_frames=[0, 16],
        salt_event_catchup_exact_step=1, salt_event_catchup_native_argument='R9B once',
        salt_event_catchup_requires_motion_base=2, salt_event_catchup_requires_motion_bank=0,
        salt_event_catchup_gameplay_verified=False, salt_route_reenabled_for_event_test=True,
        special_items_salt_disabled_id=None, special_items_salt_gameplay_verified=False,
        special_items_salt_stuck_state_repair=False, special_items_damage_compatibility_fully_verified=False,
        distribution_ready=False, special_item_ids=list(salt_source['special_item_ids']),
        event_testing_requires_no_enemies=True)
    return plan
