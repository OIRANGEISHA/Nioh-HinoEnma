"""Scoped native Signpost dispatcher; no direct item/object/position writes.

William's observed action609/motion123 owns the original scheduled events.
Select common172 for exactly one accepted34765/category21 idle request, then
continue the original751862 path which sets parent input24 and clears555.
Incomplete resources preserve the old native item-animation gate.
"""
from copy import deepcopy

FRAGMENT_SLOT = 0x2C00
HELPER_OFFSET = 0x100
RESOURCE_SLOT = 0x1400
RESOURCE_OFFSET = 0x100
FRAGMENT_PADDING = 49
RESOURCE_PADDING = 220
SIGNPOST_TARGETS = {'signpost_action_lookup': 0x73FA40}
EXPECTED_SLOTS = (
    (5, 'HE_EquipmentPrepare', 0x882639, 7, 0x1400, 0x400),
    (6, 'HE_InputA', 0x721044, 5, 0x1800, 0x400),
    (7, 'HE_InputB', 0x721099, 5, 0x1C00, 0x400),
    (11, 'HE_HimorogiFragment', 0x75185D, 5, 0x2C00, 0x400),
)
NATIVE_SIGNATURE_SPANS = (
    ('signpost_query285', 0x738345, 0x2F),
    ('signpost_query285_jump', 0x73AF74, 4),
    ('signpost_native_action_setter', 0x706070, 0x4B),
    ('signpost_native_motion_index', 0x917500, 0xBC),
)

# Entry arrives with RSP%16==8. Eight pushes and A8 reserve Win64 shadow
# space with native callees aligned. The helper returns every flag/GPR/SSE
# and MXCSR unchanged, including carry: it makes no caller branch decision.
HELPER_ASM = '''signpost_helper:
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xA8
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0x90]
mov r11, {data}
cmp dword ptr [r11+4], 0
je signpost_fail_a
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je signpost_fail_a
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne signpost_fail_a
cmp dword ptr [rdx+4], 0x10000
jne signpost_fail_a
cmp dword ptr [rdx], 0x58E5E
je signpost_role
cmp dword ptr [rdx], 0x51BE1
jne signpost_fail_a
signpost_role:
cmp dword ptr [rdx+0xEF0], 0
jne signpost_fail_a
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je signpost_fail_a
cmp dword ptr [rax+0x0C], 1
jne signpost_fail_a
mov ecx, dword ptr [rdx]
cmp dword ptr [rax], ecx
jne signpost_fail_a
mov rax, qword ptr [rdx+0x240]
test rax, rax
je signpost_fail_a
cmp qword ptr [rax], rdx
jne signpost_fail_a
cmp qword ptr [rax+0x108], rdx
jne signpost_fail_a
cmp qword ptr [rax+0x20], 0
jle signpost_fail_a
jmp signpost_owner
signpost_fail_a:
jmp signpost_restore
signpost_owner:
mov rax, qword ptr [rdx+0x230]
test rax, rax
je signpost_fail_b
cmp qword ptr [rax], rdx
jne signpost_fail_b
cmp qword ptr [rax+8], rdi
jne signpost_fail_b
cmp qword ptr [rdi+0x50], rdx
jne signpost_fail_b
cmp dword ptr [rdi+0x548], 34765
jne signpost_fail_b
cmp dword ptr [rdi+0x54C], 21
jne signpost_fail_b
cmp dword ptr [rdi+0x550], 1
jne signpost_fail_b
cmp word ptr [rdi+0x554], 0x0100
jne signpost_fail_b
cmp word ptr [rdi+0x556], 0
jne signpost_fail_b
cmp qword ptr [rdi+0x558], 0
jne signpost_fail_b
cmp qword ptr [rdi+0x728], 0
jne signpost_fail_b
mov rax, qword ptr [rdi+0x720]
test rax, rax
je signpost_fail_b
cmp qword ptr [rax], rax
jne signpost_fail_b
cmp qword ptr [rax+8], rax
jne signpost_fail_b
mov rax, qword ptr [rdi+0x58]
test rax, rax
je signpost_fail_b
cmp dword ptr [rax], 0
jne signpost_fail_b
mov rcx, qword ptr [rdi+0x78]
test rcx, rcx
je signpost_fail_b
cmp qword ptr [rax+0x38], rcx
jne signpost_fail_b
mov rax, qword ptr [rax+0x20]
test rax, rax
je signpost_fail_b
test byte ptr [rax], 1
je signpost_fail_b
test byte ptr [rax+1], 8
jne signpost_fail_b
jmp signpost_records
signpost_fail_b:
jmp signpost_restore
signpost_records:
mov rax, qword ptr [rdi+0x80]
test rax, rax
je signpost_restore
cmp dword ptr [rax+0x130], 0
je signpost_restore
cmp dword ptr [rax+0x130], 0x1000
ja signpost_restore
cmp qword ptr [rax+0x128], 0
je signpost_restore
mov qword ptr [rsp+0x80], rax
lea rcx, [rdi+0x70]
mov edx, 172
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je signpost_restore
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x38], rcx
jne signpost_restore
cmp byte ptr [rax+0x40], 0
je signpost_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je signpost_restore
cmp dword ptr [rax+0x20], -1
jne signpost_restore
lea rcx, [rdi+0x70]
mov edx, 609
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je signpost_restore
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x38], rcx
jne signpost_restore
cmp byte ptr [rax+0x40], 0
je signpost_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je signpost_restore
cmp dword ptr [rax+0x20], 123
jne signpost_restore
mov rax, {data}
mov rax, qword ptr [rax+0x10]
mov rcx, qword ptr [rax+0x38]
test rcx, rcx
je signpost_restore
cmp dword ptr [rcx+0x50], 1
ja signpost_restore
call {data} - 0xDB00
test al, al
je signpost_restore
mov rcx, rdi
mov edx, 172
call {native_ladder_set_action}
signpost_restore:
ldmxcsr dword ptr [rsp+0x90]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xA8
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
ret
'''

RESOURCE_ASM = '''signpost_resources:
sub rsp, 0x38
mov qword ptr [rsp+0x20], rcx
mov dword ptr [rsp+0x34], 2
signpost_resource_slot:
mov rax, qword ptr [rsp+0x20]
mov ecx, dword ptr [rsp+0x34]
mov rax, qword ptr [rax+rcx*8+8]
test rax, rax
je signpost_resource_false
mov qword ptr [rsp+0x28], rax
mov rcx, qword ptr [rax+0x480]
test rcx, rcx
je signpost_resource_false
cmp dword ptr [rcx+8], 0
je signpost_resource_false
cmp dword ptr [rcx+8], 0x10000
ja signpost_resource_false
cmp qword ptr [rcx+0x10], 0
je signpost_resource_false
mov edx, 123
mov r8d, -1
call {native_ladder_motion_index}
test eax, eax
js signpost_resource_false
cmp eax, 0x10000
jae signpost_resource_false
mov rcx, qword ptr [rsp+0x28]
mov r10, qword ptr [rcx+0x468]
test r10, r10
je signpost_resource_false
mov rcx, qword ptr [rcx+0x470]
cmp rcx, r10
jbe signpost_resource_false
sub rcx, r10
test cl, 7
jne signpost_resource_false
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae signpost_resource_false
cmp qword ptr [r10+rdx], 0
je signpost_resource_false
cmp dword ptr [rsp+0x34], 2
jne signpost_resource_true
mov dword ptr [rsp+0x34], 6
jmp signpost_resource_slot
signpost_resource_true:
mov eax, 1
add rsp, 0x38
ret
signpost_resource_false:
xor eax, eax
add rsp, 0x38
ret
'''


def _input_scope(suffix):
    return '''push rdx
cmp dword ptr [rdx+0x0C], 1
jne signpost_input_continue_SUFFIX
mov rdx, {player_slot}
mov rdx, qword ptr [rdx]
cmp qword ptr [rax+0x10], rdx
jne signpost_input_continue_SUFFIX
cmp dword ptr [rdx+4], 0x10000
jne signpost_input_continue_SUFFIX
cmp dword ptr [rdx], 0x58E5E
je signpost_input_record_SUFFIX
cmp dword ptr [rdx], 0x51BE1
jne signpost_input_continue_SUFFIX
signpost_input_record_SUFFIX:
mov rdx, qword ptr [rbx+0x58]
test rdx, rdx
je signpost_input_continue_SUFFIX
cmp dword ptr [rdx], 609
jne signpost_input_continue_SUFFIX
mov rdx, qword ptr [rdx+0x38]
test rdx, rdx
je signpost_input_continue_SUFFIX
cmp qword ptr [rbx+0x80], rdx
jne signpost_input_continue_SUFFIX
mov rdx, qword ptr [rbx+0x58]
mov rdx, qword ptr [rdx+0x20]
test rdx, rdx
je signpost_input_continue_SUFFIX
cmp dword ptr [rdx+0x20], 123
jne signpost_input_continue_SUFFIX
pop rdx
jmp input_SUFFIX_done
signpost_input_continue_SUFFIX:
pop rdx
'''.replace('SUFFIX', suffix)


def apply_signpost(previous_profile):
    """Pure v0.44 -> v0.45 transformation, preserving all45 sites/layouts."""
    if previous_profile.get('tool_version') != '0.44' or len(previous_profile['hooks']) != 45:
        raise ValueError('Signpost requires the complete verified v0.44 profile')
    plan = deepcopy(previous_profile)
    if plan['data_offset'] != 0xF000:
        raise ValueError('Unexpected private data layout')
    for index, name, rva, length, offset, capacity in EXPECTED_SLOTS:
        hook = plan['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != (name, rva, length, offset, capacity):
            raise ValueError('Unexpected Signpost native entry or private slot')
    resource, fragment = plan['hooks'][5], plan['hooks'][11]
    for hook, fields in ((resource, ('HE_EquipmentPrepare', 0x882639, RESOURCE_SLOT)),
                         (fragment, ('HE_HimorogiFragment', 0x75185D, FRAGMENT_SLOT))):
        if (hook['name'], hook['rva'], hook['code_offset']) != fields or hook.get('code_capacity', 0x400) != 0x400:
            raise ValueError('Unexpected Signpost carrier layout')
    marker = 'test r14b, r14b\njne {item_use_ready}\n'
    if fragment['asm'].count(marker) != 1:
        raise ValueError('Unexpected Fragment entry')
    fragment['asm'] = fragment['asm'].replace(marker, marker + 'call {data} - 0xC300\n')
    fragment['asm'] += '\n' + 'nop\n'*FRAGMENT_PADDING + HELPER_ASM
    resource['asm'] += '\n' + 'nop\n'*RESOURCE_PADDING + RESOURCE_ASM
    for index, suffix in ((6, 'a'), (7, 'b')):
        hook = plan['hooks'][index]
        if hook['name'] != 'HE_Input'+suffix.upper() or hook['asm'].count('inc dword ptr [rax+0x24]') != 1:
            raise ValueError('Unexpected native input compatibility guard')
        hook['asm'] = hook['asm'].replace('inc dword ptr [rax+0x24]',
                                         _input_scope(suffix) + 'inc dword ptr [rax+0x24]')
    plan['targets'].update(SIGNPOST_TARGETS)
    plan.update(tool_version='0.45', stage='native_signpost_action', signpost_revision=1,
        signpost_talisman=True, signpost_changed_hook_indices=[5,6,7,11],
        signpost_item_id=34765, signpost_use_category=21,
        signpost_common_actions=[172,609], signpost_main_motion_id=123,
        signpost_helper_offsets=dict(entry=FRAGMENT_SLOT+HELPER_OFFSET,
                                     resources=RESOURCE_SLOT+RESOURCE_OFFSET),
        signpost_resource_failure_fallback='previous_native_item_animation_gate',
        signpost_direct_inventory_position_writes=False,
        signpost_gameplay_confirmation_pending=True)
    return plan
