"""Experimental owned Salt rear-hurt bank selection; no damage-state writes.

Only native selected transition5170 -> 224 arms an independent epoch token.
The selected Common224/151 motionless entries retain their native queries.
Rear106..109 uses exact Common30102/30108 clips, while front91/92, missing
3001 -> native0 and all unrelated paths keep the original lookup. This is
an offline candidate, not evidence of successful received-damage gameplay.
"""
from copy import deepcopy

HOOK_INDICES = (34, 39)
HELPER_OFFSET = 0xBCC0
HELPER_CAPACITY = 0x740
PREFIX_LENGTH = 0x4A3
RESOURCE_OFFSET = 0xEE00
AUX_OFFSET = 0xECD0
AUX_CAPACITY = 0x130
TOKEN_CHECK_OFFSET = AUX_OFFSET
SALT_CHECK_OFFSET = AUX_OFFSET+0x5D
TOKEN_OFFSET = 0x13F00
TOKEN_SIZE = 0x40
LOOKUP_PADDING = 346
DISPATCHER_LENGTH = 36
NATIVE_SIGNATURE_SPANS = (('salt_hurt_pending_apply_order', 7435176, 56),
 ('salt_hurt_injury_scan_apply', 7397088, 641),
 ('salt_hurt_transition_apply', 7408144, 3971),
 ('salt_hurt_common_expand', 7412160, 885),
 ('salt_hurt_qualification_lookup', 7476880, 216),
 ('salt_hurt_qualification_predicate_a', 7475221, 47),
 ('salt_hurt_qualification_predicate_b', 7475273, 80),
 ('salt_hurt_qualification_predicate_c', 7475358, 48),
 ('salt_hurt_common_predicate', 7474512, 325),
 ('salt_hurt_query52', 7565398, 16),
 ('salt_hurt_query53', 7565220, 120),
 ('salt_hurt_descriptor_classes', 7566660, 306),
 ('salt_hurt_query52_63_table', 7580624, 48),
 ('salt_hurt_angle_sentinel', 22579868, 4),
 ('salt_hurt_quarterpi', 22579420, 4),
 ('salt_hurt_abs_mask', 22584784, 16),
 ('salt_hurt_rear_threshold', 18500548, 4),
 ('salt_hurt_query_dispatch', 7564464, 96),
 ('salt_hurt_query_false', 7572212, 8),
 ('salt_hurt_query_return', 7580337, 79),
 ('salt_hurt_query433', 7579422, 101),
 ('salt_hurt_query433_table', 7582148, 4),
 ('salt_hurt_query_true', 7580311, 5))

AUX_TOKEN_ASM = '''salt_hurt_token_check:
cmp dword ptr [r15], 1
je salt_hurt_token_active
mov rax, qword ptr [r15]
or rax, qword ptr [r15+8]
or rax, qword ptr [r15+0x10]
or rax, qword ptr [r15+0x18]
or rax, qword ptr [r15+0x20]
or rax, qword ptr [r15+0x28]
or rax, qword ptr [r15+0x30]
or rax, qword ptr [r15+0x38]
jne salt_hurt_token_invalid
xor eax, eax
ret
salt_hurt_token_active:
mov eax, dword ptr [r15-0x4EE4]
cmp dword ptr [r15+4], eax
jne salt_hurt_token_invalid
cmp qword ptr [r15+8], r12
jne salt_hurt_token_invalid
cmp qword ptr [r15+0x10], r13
jne salt_hurt_token_invalid
mov rax, qword ptr [r15+0x28]
or rax, qword ptr [r15+0x30]
or rax, qword ptr [r15+0x38]
jne salt_hurt_token_invalid
mov eax, 1
ret
salt_hurt_token_invalid:
mov eax, -1
ret
'''

AUX_SALT_ASM = '''salt_hurt_salt_check:
xor eax, eax
cmp dword ptr [r10+0x20], 120
jne salt_hurt_salt_invalid
cmp dword ptr [r10+0x40], 0x000F0011
jne salt_hurt_salt_invalid
cmp word ptr [r10+0x44], 0xFFFF
jne salt_hurt_salt_invalid
cmp dword ptr [r10+0x46], 0x0023001F
jne salt_hurt_salt_invalid
cmp word ptr [r10+0x4A], 0xFFFF
jne salt_hurt_salt_invalid
cmp dword ptr [r10+0x4C], 0x00020014
jne salt_hurt_salt_invalid
cmp word ptr [r10+0x50], 15
jne salt_hurt_salt_invalid
''' + '\n'.join(f'cmp word ptr [r10+{0x40+i*6}], 0xFFFF\njne salt_hurt_salt_invalid'
               for i in range(3,16)) + '''
inc eax
ret
salt_hurt_salt_invalid:
ret
'''

# Native lookup has already saved flags and all its working GPRs. This call
# returns zero for original dispatch or a record for its existing return path.
DISPATCHER_ASM = '''mov r11, {data}
lea rax, [r11-0x3340]
sub rsp, 0x20
call rax
add rsp, 0x20
test rax, rax
jne ladder_lookup_return
'''

ASM = '''salt_hurt_helper:
push rcx
push rdx
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
sub rsp, 0xC8
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0xB8]
xor eax, eax
mov qword ptr [rsp+0x98], rax
mov dword ptr [rsp+0xB4], eax
mov rax, qword ptr [rsp+0x198]
mov r10, {salt_hurt_qualification_return}
cmp rax, r10
je salt_hurt_caller
mov r10, {salt_hurt_first_return}
cmp rax, r10
je salt_hurt_progress
mov r10, {salt_hurt_next_return}
cmp rax, r10
jne salt_hurt_restore
salt_hurt_progress:
mov dword ptr [rsp+0xB4], 1
salt_hurt_caller:
mov r15, {data}
add r15, 0x4F00
mov r12, qword ptr [r15-0x4EF0]
test r12, r12
je salt_hurt_clear
mov rax, {player_slot}
cmp qword ptr [rax], r12
jne salt_hurt_clear
mov rax, qword ptr [r12+0x230]
test rax, rax
je salt_hurt_clear
mov r13, qword ptr [rax+8]
test r13, r13
je salt_hurt_clear
lea r10, [r13+0x70]
cmp rcx, r10
jne salt_hurt_restore
cmp qword ptr [rax], r12
jne salt_hurt_clear
cmp qword ptr [r13+0x50], r12
jne salt_hurt_clear
cmp dword ptr [r12+4], 0x10000
jne salt_hurt_clear
mov eax, dword ptr [r12]
cmp eax, dword ptr [r15-0x4EFC]
jne salt_hurt_clear
cmp eax, 0x58E5E
je salt_hurt_role
cmp eax, 0x51BE1
jne salt_hurt_clear
salt_hurt_role:
cmp dword ptr [r12+0xEF0], 0
jne salt_hurt_clear
mov rax, qword ptr [r12+0xE90]
test rax, rax
je salt_hurt_clear
cmp dword ptr [rax+0xC], 1
jne salt_hurt_clear
mov edx, dword ptr [r12]
cmp dword ptr [rax], edx
jne salt_hurt_clear
mov rax, qword ptr [r12+0x240]
test rax, rax
je salt_hurt_clear
cmp qword ptr [rax], r12
jne salt_hurt_clear
cmp qword ptr [rax+0x108], r12
jne salt_hurt_clear
cmp qword ptr [rax+0x20], 0
jle salt_hurt_clear
mov eax, dword ptr [r15-0x4EE4]
test eax, eax
je salt_hurt_clear
call {data} - 0x330
cmp eax, -1
je salt_hurt_clear
cmp eax, 1
je salt_hurt_target
salt_hurt_unarmed:
cmp dword ptr [rsp+0xB4], 0
je salt_hurt_restore
cmp ebx, 224
jne salt_hurt_clear
salt_hurt_target:
mov r14, qword ptr [r13+0x80]
test r14, r14
je salt_hurt_clear
cmp dword ptr [r15], 1
jne salt_hurt_current
cmp qword ptr [r15+0x20], r14
jne salt_hurt_clear
salt_hurt_current:
mov rax, qword ptr [r13+0x58]
test rax, rax
je salt_hurt_clear
cmp qword ptr [rax+0x38], r14
jne salt_hurt_clear
cmp byte ptr [rax+0x40], 0
je salt_hurt_clear
mov qword ptr [rsp+0x88], rax
mov r10, qword ptr [rax+0x20]
test r10, r10
je salt_hurt_clear
mov eax, dword ptr [rax]
cmp eax, 982
jne salt_hurt_not_salt
call {data} - 0x2D3
test eax, eax
je salt_hurt_clear
cmp dword ptr [r13+0x68], 2
jne salt_hurt_clear
cmp dword ptr [r15], 1
jne salt_hurt_dispatch
mov rax, qword ptr [rsp+0x88]
cmp qword ptr [r15+0x18], rax
jne salt_hurt_clear
jmp salt_hurt_dispatch
salt_hurt_not_salt:
cmp dword ptr [r15], 1
jne salt_hurt_clear
cmp eax, 224
je salt_hurt_current_motionless
cmp eax, 151
je salt_hurt_current_motionless
sub eax, 106
cmp eax, 3
ja salt_hurt_clear
shr eax, 1
imul eax, eax, 6
add eax, 30102
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
jmp salt_hurt_dispatch
salt_hurt_current_motionless:
cmp dword ptr [r10+0x20], -1
jne salt_hurt_clear
salt_hurt_dispatch:
mov dword ptr [rsp+0xA8], 5170
mov dword ptr [rsp+0xAC], 982
cmp ebx, 224
jne salt_hurt_dispatch_active
mov rax, qword ptr [rsp+0x88]
cmp dword ptr [rax], 982
jne salt_hurt_clear
test byte ptr [r13+0x40], 2
je salt_hurt_clear
cmp dword ptr [r13+0x2C8], 48
ja salt_hurt_clear
jmp salt_hurt_records
salt_hurt_dispatch_active:
cmp dword ptr [r15], 1
jne salt_hurt_clear
mov dword ptr [rsp+0xA8], 7935
mov dword ptr [rsp+0xAC], 224
cmp ebx, 151
je salt_hurt_records
mov dword ptr [rsp+0xA8], 2593
mov dword ptr [rsp+0xAC], 151
mov eax, ebx
sub eax, 106
cmp eax, 3
ja salt_hurt_clear
mov rax, qword ptr [rsp+0x88]
mov eax, dword ptr [rax]
sub eax, 106
cmp eax, 3
ja salt_hurt_records
add eax, 106
mov dword ptr [rsp+0xAC], eax
mov dword ptr [rsp+0xA8], -1
salt_hurt_records:
mov ecx, dword ptr [r14+0x130]
test ecx, ecx
je salt_hurt_clear
cmp ecx, 0x1000
ja salt_hurt_clear
mov r10, qword ptr [r14+0x128]
test r10, r10
je salt_hurt_clear
xor edx, edx
mov dword ptr [rsp+0xB0], edx
mov qword ptr [rsp+0x90], rdx
mov qword ptr [rsp+0xA0], rdx
salt_hurt_record_loop:
mov rax, qword ptr [r10+rdx*8]
test rax, rax
je salt_hurt_record_next
cmp rax, qword ptr [rsp+0x88]
jne salt_hurt_record_id
inc dword ptr [rsp+0xB0]
salt_hurt_record_id:
cmp byte ptr [rax+0x40], 0
je salt_hurt_record_next
cmp qword ptr [rax+0x38], r14
jne salt_hurt_record_next
mov r11d, dword ptr [rax]
cmp r11d, 982
jne salt_hurt_record_source
cmp qword ptr [rsp+0x90], 0
jne salt_hurt_clear
mov qword ptr [rsp+0x90], rax
salt_hurt_record_source:
cmp r11d, dword ptr [rsp+0xAC]
jne salt_hurt_record_target
cmp qword ptr [rsp+0xA0], 0
jne salt_hurt_clear
mov qword ptr [rsp+0xA0], rax
salt_hurt_record_target:
cmp r11d, ebx
jne salt_hurt_record_next
cmp qword ptr [rsp+0x98], 0
jne salt_hurt_clear
mov qword ptr [rsp+0x98], rax
salt_hurt_record_next:
inc edx
cmp edx, ecx
jb salt_hurt_record_loop
cmp dword ptr [rsp+0xB0], 1
jne salt_hurt_clear
mov rax, qword ptr [rsp+0x90]
test rax, rax
je salt_hurt_clear
mov r10, qword ptr [rax+0x20]
test r10, r10
je salt_hurt_clear
cmp dword ptr [r10+0x20], 120
jne salt_hurt_clear
cmp dword ptr [r15], 1
jne salt_hurt_selected
cmp qword ptr [r15+0x18], rax
jne salt_hurt_clear
salt_hurt_selected:
mov rax, qword ptr [rsp+0xA0]
test rax, rax
je salt_hurt_clear
mov r10, qword ptr [r14+0x50]
test r10, r10
je salt_hurt_clear
cmp qword ptr [rax+0x78], r10
jne salt_hurt_clear
movzx ecx, word ptr [r14+0x5A]
cmp cx, word ptr [r14+0x58]
ja salt_hurt_clear
movzx edx, word ptr [rax+0x80]
movzx r8d, word ptr [rax+0x82]
add r8d, edx
cmp r8d, ecx
ja salt_hurt_clear
mov edx, dword ptr [rsp+0xA8]
cmp edx, -1
jne salt_hurt_selected_index
movzx edx, word ptr [rax+0x80]
salt_hurt_selected_index:
cmp edx, ecx
jae salt_hurt_clear
mov r9, qword ptr [r13+0x90]
test r9, r9
je salt_hurt_clear
salt_hurt_selected_loop:
cmp edx, ecx
jae salt_hurt_clear
cmp qword ptr [r10+rdx*8], r9
je salt_hurt_selected_found
cmp ebx, 106
jb salt_hurt_clear
cmp ebx, 109
ja salt_hurt_clear
inc edx
cmp dword ptr [rsp+0xA8], -1
je salt_hurt_selected_current
cmp edx, 2599
jb salt_hurt_selected_loop
jmp salt_hurt_clear
salt_hurt_selected_current:
cmp edx, r8d
jb salt_hurt_selected_loop
jmp salt_hurt_clear
salt_hurt_selected_found:
movzx ecx, word ptr [rax+0x80]
cmp edx, ecx
jb salt_hurt_clear
movzx r8d, word ptr [rax+0x82]
add ecx, r8d
cmp edx, ecx
jae salt_hurt_clear
cmp word ptr [r9+0x14], bx
jne salt_hurt_clear
mov r10, qword ptr [r14+0x60]
test r10, r10
je salt_hurt_clear
movzx ecx, word ptr [r14+0x6A]
test ecx, ecx
je salt_hurt_clear
cmp cx, word ptr [r14+0x68]
ja salt_hurt_clear
xor edx, edx
salt_hurt_unique_loop:
cmp qword ptr [r10+rdx*8], r9
je salt_hurt_parameters
inc edx
cmp edx, ecx
jb salt_hurt_unique_loop
jmp salt_hurt_clear
salt_hurt_parameters:
mov rax, qword ptr [rsp+0x98]
test rax, rax
je salt_hurt_clear
mov r10, qword ptr [rax+0x20]
test r10, r10
je salt_hurt_clear
cmp ebx, 224
je salt_hurt_motionless
cmp ebx, 151
je salt_hurt_motionless
mov eax, ebx
sub eax, 106
shr eax, 1
imul eax, eax, 6
add eax, 30102
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
mov rax, qword ptr [r12+0x38]
test rax, rax
je salt_hurt_clear
cmp dword ptr [rax+0x50], 1
ja salt_hurt_clear
mov qword ptr [rsp+0x80], rax
mov dword ptr [rsp+0xA8], 2
salt_hurt_resource_slot:
mov rax, qword ptr [rsp+0x80]
mov ecx, dword ptr [rsp+0xA8]
mov rax, qword ptr [rax+rcx*8+8]
test rax, rax
je salt_hurt_clear
mov qword ptr [rsp+0xA0], rax
mov dword ptr [rsp+0xAC], 30102
salt_hurt_resource_clip:
mov rax, qword ptr [rsp+0xA0]
mov rcx, qword ptr [rax+0x480]
test rcx, rcx
je salt_hurt_clear
cmp dword ptr [rcx+8], 0
je salt_hurt_clear
cmp dword ptr [rcx+8], 0x10000
ja salt_hurt_clear
cmp qword ptr [rcx+0x10], 0
je salt_hurt_clear
mov edx, dword ptr [rsp+0xAC]
mov r8d, -1
call {native_ladder_motion_index}
test eax, eax
js salt_hurt_clear
cmp eax, 0x10000
jae salt_hurt_clear
mov rcx, qword ptr [rsp+0xA0]
mov r10, qword ptr [rcx+0x468]
test r10, r10
je salt_hurt_clear
mov rcx, qword ptr [rcx+0x470]
cmp rcx, r10
jbe salt_hurt_clear
sub rcx, r10
test cl, 7
jne salt_hurt_clear
cmp rcx, 0x80000
ja salt_hurt_clear
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae salt_hurt_clear
cmp qword ptr [r10+rdx], 0
je salt_hurt_clear
cmp dword ptr [rsp+0xAC], 30108
je salt_hurt_resource_next
mov dword ptr [rsp+0xAC], 30108
jmp salt_hurt_resource_clip
salt_hurt_resource_next:
cmp dword ptr [rsp+0xA8], 6
je salt_hurt_success
mov dword ptr [rsp+0xA8], 6
jmp salt_hurt_resource_slot
salt_hurt_motionless:
cmp dword ptr [r10+0x20], -1
jne salt_hurt_clear
cmp dword ptr [r15], 1
je salt_hurt_success
mov eax, dword ptr [r15-0x4EE4]
mov dword ptr [r15+4], eax
mov qword ptr [r15+8], r12
mov qword ptr [r15+0x10], r13
mov rax, qword ptr [rsp+0x90]
mov qword ptr [r15+0x18], rax
mov qword ptr [r15+0x20], r14
xor eax, eax
mov qword ptr [r15+0x28], rax
mov qword ptr [r15+0x30], rax
mov qword ptr [r15+0x38], rax
mov dword ptr [r15], 1
salt_hurt_success:
mov rax, qword ptr [rsp+0x98]
test rsi, rsi
je salt_hurt_restore
mov dword ptr [rsi], 2
jmp salt_hurt_restore
salt_hurt_clear:
cmp dword ptr [rsp+0xB4], 0
je salt_hurt_reject
xor eax, eax
pxor xmm0, xmm0
movdqu xmmword ptr [r15], xmm0
movdqu xmmword ptr [r15+0x10], xmm0
movdqu xmmword ptr [r15+0x20], xmm0
movdqu xmmword ptr [r15+0x30], xmm0
salt_hurt_reject:
mov qword ptr [rsp+0x98], 0
salt_hurt_restore:
mov rax, qword ptr [rsp+0x98]
ldmxcsr dword ptr [rsp+0xB8]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xC8
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
ret
'''


def _short_failure_islands(source):
    """Keep identical conditional failures near their branch instructions.

    Each island jumps around one unconditional jump to the common failure.
    No instruction changes flags or registers, and every failure still reaches
    exactly the same clear/qualification-reject block. This saves private slot
    bytes without removing guards or extending another carrier.
    """
    head, tail = source.split('salt_hurt_clear:\n', 1)
    lines = head.splitlines()
    result = []
    for number, first in enumerate(range(0, len(lines), 29)):
        chunk = lines[first:first+29]
        failures = any(line.startswith(('je ', 'jne ', 'ja ', 'jae ', 'jb ', 'jbe ', 'js ', 'jle '))
                       and line.endswith(' salt_hurt_clear') for line in chunk)
        if failures:
            name = 'salt_hurt_failure_' + str(number)
            chunk = [line.replace(' salt_hurt_clear', ' '+name)
                     if line.startswith(('je ', 'jne ', 'ja ', 'jae ', 'jb ', 'jbe ', 'js ', 'jle '))
                     else line for line in chunk]
            chunk += ['jmp '+name+'_continue', name+':', 'jmp salt_hurt_clear', name+'_continue:']
        result.extend(chunk)
    return '\n'.join(result)+'\nsalt_hurt_clear:\n'+tail


ASM = _short_failure_islands(ASM)


def apply_salt_hurt_compatibility(previous):
    if (previous.get('tool_version') != '0.55-experimental'
            or len(previous.get('hooks', ())) != 50
            or (previous.get('allocation_size'), previous.get('data_offset')) != (0x14000, 0xF000)
            or not previous.get('salt_event_catchup')):
        raise ValueError('Complete frozen v0.55 event profile required')
    plan = deepcopy(previous)
    carrier, lookup = (plan['hooks'][i] for i in HOOK_INDICES)
    if ((carrier['name'], carrier['code_offset'], carrier.get('code_capacity')) != ('HE_RoarDigitFive', 0xB800, 0xC00)
            or (lookup['name'], lookup['rva'], lookup['code_offset'], lookup.get('code_capacity')) != ('HE_LadderCommonLookup', 0x73FA40, 0xE800, 0x800)):
        raise ValueError('Exact unused Roar tail and fixed Common lookup required')
    marker = 'mov ebx, edx\nmov rsi, r8\n'
    padding = 'nop\n' * LOOKUP_PADDING + 'hot_spring_resource_entry:'
    if lookup['asm'].count(marker) != 1 or lookup['asm'].count(padding) != 1:
        raise ValueError('Frozen lookup dispatcher/padding changed')
    lookup['asm'] = lookup['asm'].replace(marker, marker + DISPATCHER_ASM, 1)
    # 93B token validator and a separate exact Salt schedule check. Fixed
    # padding is checked against assembly by tests at every supported ASLR.
    lookup['asm'] = lookup['asm'].replace(padding,
        'nop\n' * (AUX_OFFSET-0xE800-(0x600-LOOKUP_PADDING+DISPATCHER_LENGTH))
        + AUX_TOKEN_ASM + AUX_SALT_ASM + 'nop\n'
        + 'hot_spring_resource_entry:', 1)
    carrier['asm'] += '\n' + 'nop\n' * (HELPER_OFFSET-0xB800-PREFIX_LENGTH) + ASM
    plan['targets'].update(salt_hurt_first_return=0x711A09,
        salt_hurt_next_return=0x711B1B, salt_hurt_qualification_return=0x7216D7)
    plan.update(tool_version='0.56-experimental', stage='unverified_salt_rear_hurt_bank_compatibility',
        salt_hurt_compatibility=True, salt_hurt_changed_hook_indices=list(HOOK_INDICES),
        salt_hurt_helper_offset=HELPER_OFFSET, salt_hurt_helper_capacity=HELPER_CAPACITY,
        salt_hurt_aux_offset=AUX_OFFSET, salt_hurt_aux_capacity=AUX_CAPACITY,
        salt_hurt_token_offset=TOKEN_OFFSET, salt_hurt_token_size=TOKEN_SIZE,
        salt_hurt_arm_transition=5170, salt_hurt_arm_target=224,
        salt_hurt_motionless_targets=[224, 151], salt_hurt_rear_targets=[106,107,108,109],
        salt_hurt_required_common_motions=[30102,30108], salt_hurt_required_motion_slots=[2,6],
        salt_hurt_front_native_preserved=True, salt_hurt_missing_common_motion_ids=[30009],
        salt_hurt_gameplay_verified=False, special_items_damage_compatibility_fully_verified=False,
        special_items_gameplay_confirmation_pending=True, distribution_ready=False)
    return plan
