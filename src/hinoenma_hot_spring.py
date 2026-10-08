"""Scoped native Hot Spring actions for the verified v0.43 local Hino.

Observed object50/kind2/instance0 requests dispatch39. Native query237 maps
that request through common170 to1046, then1047/1048 (motions934/935/936).
Only a complete common family and both owned common motion resources permit
the animated path; otherwise the existing immediate interaction remains.
The native object-reference queue, interaction events, Buff and exit queries
remain in charge. This candidate still requires a gameplay confirmation.
"""
from copy import deepcopy

COMMON_SLOT = 0xE800
GENERIC_SLOT = 0x2000
GENERIC_ENTRY = 0x100
QUEUED_ENTRY = 0x110
HELPER_BODY = 0x120
RESOURCE_ENTRY = 0x600
COMMON_CAPACITY = 0x800
LOOKUP_PADDING = 346
GENERIC_PADDING = 17

NATIVE_SIGNATURE_SPANS = (
    # The omitted 751160..16A and751296..29F bytes are independently bound
    # HE_Kodama/HE_Revenant sites, not unpatched native signature spans.
    ('hot_spring_native_immediate_after_kodama', 0x75116A, 0xD8),
    ('hot_spring_native_queue_before_revenant', 0x751242, 0x54),
    ('hot_spring_set_action', 0x706070, 0x4B),
    ('hot_spring_action_setter_prefix', 0x70ECE0, 0xFA),
    ('hot_spring_interaction_boundary', 0x710254, 0xD9),
    ('hot_spring_request_predicate', 0x73DE10, 0x44),
    ('hot_spring_queries_237_238', 0x737DC5, 0x1E),
    ('hot_spring_query_table_237_238', 0x73AEB4, 0x08),
    ('hot_spring_motion_index', 0x917500, 0xBC),
    ('hot_spring_main_aux_motion_requests', 0x6FF530, 0x2B0),
    ('hot_spring_aux_event_request', 0x968D60, 0xA8),
    ('hot_spring_aux_event_dispatch', 0x968A10, 0x34B),
    ('hot_spring_aux_event_lookup', 0x968230, 0xE9),
)


LOOKUP_SCOPE = '''mov r9, qword ptr [rdi+0x510]
test r9, r9
je hot_spring_lookup_not_spring
cmp dword ptr [r9], 50
jne hot_spring_lookup_not_spring
cmp dword ptr [r9+0x04], 2
jne hot_spring_lookup_not_spring
mov r10, qword ptr [rdi+0x528]
test r10, r10
je ladder_lookup_original
cmp qword ptr [r10], r9
jne ladder_lookup_original
cmp qword ptr [r10+0x4C], 0
jne ladder_lookup_original
cmp byte ptr [r10+0x0A], 1
ja ladder_lookup_original
mov eax, dword ptr [r10+0x48]
cmp eax, 39
je hot_spring_lookup_request
cmp eax, 40
jne ladder_lookup_original
hot_spring_lookup_request:
mov r9, qword ptr [rdi+0x80]
test r9, r9
je ladder_lookup_original
mov rax, qword ptr [rdi+0x58]
test rax, rax
je ladder_lookup_original
cmp qword ptr [rax+0x38], r9
jne hot_spring_lookup_entry
mov ecx, dword ptr [rax]
sub ecx, 1046
cmp ecx, 2
ja hot_spring_lookup_entry
mov rax, qword ptr [rax+0x20]
test rax, rax
je ladder_lookup_original
add ecx, 934
cmp dword ptr [rax+0x20], ecx
jne ladder_lookup_original
cmp ebx, 1046
jb ladder_lookup_original
cmp ebx, 1048
ja ladder_lookup_original
jmp ladder_lookup_find
hot_spring_lookup_entry:
cmp word ptr [r10+0x08], 0x0101
jne ladder_lookup_original
cmp byte ptr [r10+0x0A], 0
jne ladder_lookup_original
cmp dword ptr [r10+0x48], 39
jne ladder_lookup_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je ladder_lookup_original
test byte ptr [rax], 1
je ladder_lookup_original
test byte ptr [rax+1], 8
jne ladder_lookup_original
cmp ebx, 170
je ladder_lookup_find
cmp ebx, 1046
je ladder_lookup_find
jmp ladder_lookup_original
hot_spring_lookup_not_spring:
'''

LOOKUP_MOTION = '''cmp ebx, 1046
jb hot_spring_lookup_ladder_motion
cmp ebx, 1048
ja hot_spring_lookup_ladder_motion
mov ecx, ebx
sub ecx, 112
cmp dword ptr [r11+0x20], ecx
jne ladder_lookup_original
jmp ladder_lookup_found
hot_spring_lookup_ladder_motion:
'''


def _restore():
    return '''ldmxcsr dword ptr [rsp+0x9C]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xA0
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
lea rsp, [rsp+8]
'''


# Both fixed entries push their mode before this frame. A call arrives with
# RSP%16==8; mode+8 saves give RSP%16==0 and A0 includes the Win64 shadow space.
HELPER_ASM = '''hot_spring_helper_body:
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xA0
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0x9C]
mov dword ptr [rsp+0x94], 0
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne hot_spring_helper_fail_a
cmp dword ptr [r11+0x04], 0
je hot_spring_helper_fail_a
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je hot_spring_helper_fail_a
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne hot_spring_helper_fail_a
cmp dword ptr [rdx+0x04], 0x10000
jne hot_spring_helper_fail_a
cmp dword ptr [rdx], 0x58E5E
je hot_spring_helper_role
cmp dword ptr [rdx], 0x51BE1
jne hot_spring_helper_fail_a
jmp hot_spring_helper_role
hot_spring_helper_fail_a:
jmp hot_spring_helper_restore
hot_spring_helper_role:
cmp dword ptr [rdx+0xEF0], 0
jne hot_spring_helper_fail_b
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je hot_spring_helper_fail_b
cmp dword ptr [rax+0x0C], 1
jne hot_spring_helper_fail_b
mov rax, qword ptr [rdx+0x240]
test rax, rax
je hot_spring_helper_fail_b
cmp qword ptr [rax+0x108], rdx
jne hot_spring_helper_fail_b
cmp qword ptr [rax+0x20], 0
jle hot_spring_helper_fail_b
mov rax, qword ptr [rdx+0x230]
test rax, rax
je hot_spring_helper_fail_b
cmp qword ptr [rax], rdx
jne hot_spring_helper_fail_b
cmp qword ptr [rax+0x08], rdi
jne hot_spring_helper_fail_b
cmp qword ptr [rdi+0x50], rdx
jne hot_spring_helper_fail_b
mov r9, qword ptr [rsp+0xB8]
mov r10, qword ptr [rsp+0xD0]
cmp qword ptr [rsp+0xE0], 0
je hot_spring_helper_pair
mov r9, qword ptr [rdi+0x510]
mov r10, qword ptr [rdi+0x528]
jmp hot_spring_helper_pair
hot_spring_helper_fail_b:
jmp hot_spring_helper_restore
hot_spring_helper_pair:
test r9, r9
je hot_spring_helper_fail_c
cmp dword ptr [r9], 50
jne hot_spring_helper_fail_c
cmp dword ptr [r9+0x04], 2
jne hot_spring_helper_fail_c
test r10, r10
je hot_spring_helper_fail_c
cmp qword ptr [r10], r9
jne hot_spring_helper_fail_c
cmp word ptr [r10+0x08], 0x0101
jne hot_spring_helper_fail_c
cmp byte ptr [r10+0x0A], 0
jne hot_spring_helper_fail_c
cmp dword ptr [r10+0x48], 39
jne hot_spring_helper_fail_c
cmp qword ptr [r10+0x4C], 0
jne hot_spring_helper_fail_c
mov rax, qword ptr [rdi+0x58]
test rax, rax
je hot_spring_helper_fail_c
mov rax, qword ptr [rax+0x20]
test rax, rax
je hot_spring_helper_fail_c
test byte ptr [rax], 1
je hot_spring_helper_fail_c
test byte ptr [rax+1], 8
jne hot_spring_helper_fail_c
mov rax, qword ptr [rdx+0x38]
test rax, rax
je hot_spring_helper_fail_c
cmp dword ptr [rax+0x50], 1
ja hot_spring_helper_fail_c
mov qword ptr [rsp+0x80], rax
jmp hot_spring_helper_bank
hot_spring_helper_fail_c:
jmp hot_spring_helper_restore
hot_spring_helper_bank:
mov r9, qword ptr [rdi+0x80]
test r9, r9
je hot_spring_helper_restore
mov ecx, dword ptr [r9+0x130]
test ecx, ecx
je hot_spring_helper_restore
cmp ecx, 0x1000
ja hot_spring_helper_restore
mov r10, qword ptr [r9+0x128]
test r10, r10
je hot_spring_helper_restore
xor edx, edx
xor r8d, r8d
hot_spring_helper_records:
mov rax, qword ptr [r10+rdx*8]
test rax, rax
je hot_spring_helper_next_record
mov r11d, dword ptr [rax]
cmp r11d, 170
je hot_spring_helper_record
sub r11d, 1046
cmp r11d, 2
ja hot_spring_helper_next_record
hot_spring_helper_record:
cmp byte ptr [rax+0x40], 0
je hot_spring_helper_restore
cmp qword ptr [rax+0x38], r9
jne hot_spring_helper_restore
mov r11, qword ptr [rax+0x20]
test r11, r11
je hot_spring_helper_restore
cmp dword ptr [rax], 170
jne hot_spring_helper_motion_record
cmp dword ptr [r11+0x20], -1
jne hot_spring_helper_restore
or r8d, 8
jmp hot_spring_helper_next_record
hot_spring_helper_motion_record:
mov eax, dword ptr [rax]
sub eax, 112
cmp dword ptr [r11+0x20], eax
jne hot_spring_helper_restore
sub eax, 934
bts r8d, eax
hot_spring_helper_next_record:
inc edx
cmp edx, ecx
jb hot_spring_helper_records
cmp r8d, 15
jne hot_spring_helper_restore
mov rcx, qword ptr [rsp+0x80]
call {data} - 0x200
test eax, eax
je hot_spring_helper_restore
hot_spring_helper_ready:
inc dword ptr [rsp+0x94]
cmp qword ptr [rsp+0xE0], 0
je hot_spring_helper_restore
mov rcx, rdi
mov edx, 170
call {native_ladder_set_action}
hot_spring_helper_restore:
cmp qword ptr [rsp+0xE0], 0
jne hot_spring_helper_epilogue
and qword ptr [rsp+0xD8], -2
cmp dword ptr [rsp+0x94], 0
je hot_spring_helper_epilogue
or qword ptr [rsp+0xD8], 1
hot_spring_helper_epilogue:
''' + _restore() + '''ret
'''

# The parent helper saves every volatile register/SSE state. This leaf only
# uses volatile GPRs, owns its shadow space, and calls the pure native hash map.
RESOURCE_ASM = '''hot_spring_resource_entry:
sub rsp, 0x38
mov qword ptr [rsp+0x20], rcx
mov dword ptr [rsp+0x34], 2
hot_spring_resource_slot:
mov rax, qword ptr [rsp+0x20]
mov ecx, dword ptr [rsp+0x34]
mov rax, qword ptr [rax+rcx*8+0x08]
test rax, rax
je hot_spring_resource_false
mov qword ptr [rsp+0x28], rax
mov dword ptr [rsp+0x30], 934
hot_spring_resource_clip:
mov rax, qword ptr [rsp+0x28]
mov rcx, qword ptr [rax+0x480]
test rcx, rcx
je hot_spring_resource_false
cmp dword ptr [rcx+0x08], 0
je hot_spring_resource_false
cmp dword ptr [rcx+0x08], 0x10000
ja hot_spring_resource_false
cmp qword ptr [rcx+0x10], 0
je hot_spring_resource_false
mov edx, dword ptr [rsp+0x30]
mov r8d, -1
call {native_ladder_motion_index}
test eax, eax
js hot_spring_resource_false
cmp eax, 0x10000
jae hot_spring_resource_false
mov rcx, qword ptr [rsp+0x28]
mov r10, qword ptr [rcx+0x468]
test r10, r10
je hot_spring_resource_false
mov rcx, qword ptr [rcx+0x470]
cmp rcx, r10
jbe hot_spring_resource_false
sub rcx, r10
test cl, 7
jne hot_spring_resource_false
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae hot_spring_resource_false
cmp qword ptr [r10+rdx], 0
je hot_spring_resource_false
inc dword ptr [rsp+0x30]
cmp dword ptr [rsp+0x30], 937
jb hot_spring_resource_clip
cmp dword ptr [rsp+0x34], 2
jne hot_spring_resource_true
mov dword ptr [rsp+0x34], 6
jmp hot_spring_resource_slot
hot_spring_resource_true:
mov eax, 1
add rsp, 0x38
ret
hot_spring_resource_false:
xor eax, eax
add rsp, 0x38
ret
'''


def apply_hot_spring(previous_profile):
    if previous_profile.get('tool_version') != '0.43' or len(previous_profile['hooks']) != 45:
        raise ValueError('Hot Spring actions require the complete verified v0.43 profile')
    plan = deepcopy(previous_profile)
    generic, queued, lookup = (plan['hooks'][i] for i in (8, 9, 39))
    expected = (('HE_Interaction', 0x751156, 0x2000),
                ('HE_QueuedDoor', 0x75129F, 0x2400),
                ('HE_LadderCommonLookup', 0x73FA40, COMMON_SLOT))
    for hook, fields in zip((generic, queued, lookup), expected):
        if (hook['name'], hook['rva'], hook['code_offset']) != fields:
            raise ValueError('Unexpected interaction/common private slot')
    if plan['data_offset'] != 0xF000 or lookup.get('code_capacity') != COMMON_CAPACITY:
        raise ValueError('Unexpected fixed shared helper allocation layout')
    marker = 'generic_immediate:\ninc dword ptr [r11+0x34]'
    if generic['asm'].count(marker) != 1:
        raise ValueError('Unexpected immediate interaction source')
    generic['asm'] = generic['asm'].replace(marker,
        'generic_immediate:\ncall {data} - 0xCF00\njc generic_original\ninc dword ptr [r11+0x34]')
    marker = 'pushfq\nmov r11, {data}'
    if queued['asm'].count(marker) != 1:
        raise ValueError('Unexpected queued interaction source')
    queued['asm'] = queued['asm'].replace(marker,
        'pushfq\ncall {data} - 0xCEF0\nmov r11, {data}')
    marker = 'mov r9, qword ptr [rdi+0x510]'
    if lookup['asm'].count(marker) != 1:
        raise ValueError('Unexpected common lookup source')
    lookup['asm'] = lookup['asm'].replace(marker, LOOKUP_SCOPE + marker)
    marker = 'ladder_lookup_motion:\n'
    if lookup['asm'].count(marker) != 1:
        raise ValueError('Unexpected common lookup motion guard')
    lookup['asm'] = lookup['asm'].replace(marker, marker + LOOKUP_MOTION)
    generic['asm'] += ('\n' + 'nop\n' * GENERIC_PADDING
        + 'hot_spring_generic_entry:\npush 0\njmp hot_spring_helper_body\n'
        + 'nop\n' * 12
        + 'hot_spring_queued_entry:\npush 1\njmp hot_spring_helper_body\n'
        + 'nop\n' * 12 + HELPER_ASM)
    lookup['asm'] += '\n' + 'nop\n' * LOOKUP_PADDING + RESOURCE_ASM
    generic['purpose'] += '; complete owned Hot Spring clips permit native animation queue; incomplete family retains immediate effect'
    queued['purpose'] += '; scoped native170 Hot Spring entry after original tracked references are queued'
    lookup['purpose'] += '; object50 request39/40 common170 and1046..1048 only; shared guarded resource preflight'
    plan.update(tool_version='0.44', stage='native_hot_spring_actions',
        hot_spring_revision=1, hot_spring_changed_hook_indices=[8, 9, 39],
        hot_spring_dispatch=39, hot_spring_exit_dispatch=40,
        hot_spring_object=dict(id=50, kind=2, instance=0),
        hot_spring_common_actions=[170, 1046, 1047, 1048],
        hot_spring_main_motion_ids=[934, 935, 936],
        hot_spring_required_motion_slots=[2, 6],
        hot_spring_helper_offsets=dict(generic=GENERIC_SLOT+GENERIC_ENTRY,
            queued=GENERIC_SLOT+QUEUED_ENTRY, body=GENERIC_SLOT+HELPER_BODY,
            resources=COMMON_SLOT+RESOURCE_ENTRY),
        hot_spring_resource_failure_fallback='previous_native_immediate_interaction',
        hot_spring_native_buff_and_level_growth_preserved=True,
        hot_spring_gameplay_confirmation_pending=True)
    return plan
