"""Start an accepted NPC conversation through its original common action family.

Native request46 selects common1155 through query346 after common170. The
original event0/120 and TalkMode script flag own the conversation; query345
ends its1156 wait. No NPC flags, interaction fields, scripts or save data are
written here. Incomplete owned records or clips leave the prior queue alone.
"""
from copy import deepcopy

from hinoenma_signpost import RESOURCE_ASM as _SINGLE_MOTION_RESOURCES


CARRIER_SLOT = 0x10800
HELPER_ENTRY = 0x200
RESOURCE_ENTRY = 0x700
CARRIER_PADDING = 202  # Frozen actor-unload prefix310B; entry at10A00.
HELPER_PADDING = 103  # Helper1177B; resource leaf fixed at10F00.

EXPECTED_SLOTS = (
    (9, 'HE_QueuedDoor', 0x75129F, 11, 0x2400, 0x400),
    (46, 'HE_SameTemplateUnloadActor', 0x8B18C9, 11, CARRIER_SLOT, 0x800),
)

NATIVE_SIGNATURE_SPANS = (
    ('talk_native_queue_before_revenant', 0x751242, 0x54),
    ('talk_native_set_action', 0x706070, 0x4B),
    ('talk_native_action_setter_prefix', 0x70ECE0, 0xFA),
    ('talk_native_interaction_boundary', 0x710254, 0xD9),
    ('talk_original_action_lookup_tail', 0x73FA45, 0xCC),
    ('talk_request_predicate', 0x73DE10, 0x44),
    ('talk_query346', 0x737E2E, 0x0F),
    ('talk_query345', 0x739E64, 0x17),
    ('talk_query345_346_table', 0x73B064, 8),
    ('talk_native_motion_index', 0x917500, 0xBC),
    ('talk_original_interaction_start', 0x70936F, 0x40),
)

# Call inside the original queued hook's fully saved frame arrives atRSP%16=8.
# Eight saves andC8 locals align native calls with32B Win64 shadow space.
# Volatile SSE/MXCSR and every caller flag/register are restored on all exits.
HELPER_ASM = '''talk_helper:
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xC8
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0x90]
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne talk_fail_a
cmp dword ptr [r11+4], 0x58E5E
je talk_selected
cmp dword ptr [r11+4], 0x51BE1
jne talk_fail_a
talk_selected:
mov ecx, dword ptr [r11+0x1C]
test ecx, ecx
je talk_fail_a
mov dword ptr [rsp+0x94], ecx
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je talk_fail_a
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne talk_fail_a
cmp dword ptr [rdx+4], 0x10000
jne talk_fail_a
cmp dword ptr [rdx], 0x58E5E
je talk_role
cmp dword ptr [rdx], 0x51BE1
jne talk_fail_a
talk_role:
cmp dword ptr [rdx+0xEF0], 0
jne talk_fail_a
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je talk_fail_a
cmp dword ptr [rax+0x0C], 1
jne talk_fail_a
mov ecx, dword ptr [rdx]
cmp dword ptr [rax], ecx
jne talk_fail_a
mov rax, qword ptr [rdx+0x240]
test rax, rax
je talk_fail_a
cmp qword ptr [rax], rdx
jne talk_fail_a
cmp qword ptr [rax+0x108], rdx
jne talk_fail_a
cmp qword ptr [rax+0x20], 0
jle talk_fail_a
jmp talk_owner
talk_fail_a:
jmp talk_restore
talk_owner:
mov rax, qword ptr [rdx+0x230]
test rax, rax
je talk_fail_b
cmp qword ptr [rax], rdx
jne talk_fail_b
cmp qword ptr [rax+8], rdi
jne talk_fail_b
cmp qword ptr [rdi+0x50], rdx
jne talk_fail_b
mov qword ptr [rsp+0xC0], rdx
mov r9, qword ptr [rdi+0x510]
test r9, r9
je talk_fail_b
cmp r9, rdx
je talk_fail_b
cmp word ptr [r9+4], 0
jne talk_fail_b
mov rax, qword ptr [r9+0xE90]
test rax, rax
je talk_fail_b
mov ecx, dword ptr [r9]
cmp dword ptr [rax], ecx
jne talk_fail_b
mov qword ptr [rsp+0xB8], rax
mov rax, qword ptr [r9]
mov qword ptr [rsp+0xB0], rax
mov qword ptr [rsp+0xA0], r9
mov r10, qword ptr [rdi+0x528]
test r10, r10
je talk_fail_b
cmp qword ptr [r10], r9
jne talk_fail_b
cmp byte ptr [r10+8], 1
jne talk_fail_b
cmp byte ptr [r10+9], 1
ja talk_fail_b
cmp byte ptr [r10+0x0A], 0
jne talk_fail_b
cmp dword ptr [r10+0x48], 46
jne talk_fail_b
cmp qword ptr [r10+0x4C], 0
jne talk_fail_b
mov qword ptr [rsp+0xA8], r10
jmp talk_idle
talk_fail_b:
jmp talk_restore
talk_idle:
mov rax, qword ptr [rdi+0x58]
test rax, rax
je talk_fail_c
cmp dword ptr [rax], 0
jne talk_fail_c
mov rcx, qword ptr [rdi+0x78]
test rcx, rcx
je talk_fail_c
cmp qword ptr [rax+0x38], rcx
jne talk_fail_c
mov rax, qword ptr [rax+0x20]
test rax, rax
je talk_fail_c
test byte ptr [rax], 1
je talk_fail_c
test byte ptr [rax+1], 8
jne talk_fail_c
mov rax, qword ptr [rdx+0x38]
test rax, rax
je talk_fail_c
cmp dword ptr [rax+0x50], 1
ja talk_fail_c
mov qword ptr [rsp+0x80], rax
jmp talk_records
talk_fail_c:
jmp talk_restore
talk_records:
mov rax, qword ptr [rdi+0x80]
test rax, rax
je talk_restore
cmp dword ptr [rax+0x130], 0
je talk_restore
cmp dword ptr [rax+0x130], 0x1000
ja talk_restore
cmp qword ptr [rax+0x128], 0
je talk_restore
mov qword ptr [rsp+0x88], rax
mov dword ptr [rsp+0x98], 170
talk_record_loop:
lea rcx, [rdi+0x70]
mov edx, dword ptr [rsp+0x98]
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je talk_restore
mov ecx, dword ptr [rsp+0x98]
cmp dword ptr [rax], ecx
jne talk_restore
mov rcx, qword ptr [rsp+0x88]
cmp qword ptr [rax+0x38], rcx
jne talk_restore
cmp byte ptr [rax+0x40], 0
je talk_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je talk_restore
cmp dword ptr [rax+0x34], -1
jne talk_restore
cmp dword ptr [rsp+0x98], 170
jne talk_family
cmp dword ptr [rax+0x20], -1
jne talk_restore
mov dword ptr [rsp+0x98], 1155
jmp talk_record_loop
talk_family:
cmp dword ptr [rsp+0x98], 1155
jne talk_wait_record
cmp dword ptr [rax+0x20], 8
jne talk_restore
cmp dword ptr [rax+0x40], 0
jne talk_restore
cmp dword ptr [rax+0x44], 0x78FFFF
jne talk_restore
cmp dword ptr [rax+0x48], 0xFFFF0000
jne talk_restore
jmp talk_next_record
talk_wait_record:
cmp dword ptr [rax+0x20], 0
jne talk_restore
cmp word ptr [rax+0x40], -1
jne talk_restore
talk_next_record:
cmp dword ptr [rsp+0x98], 1157
je talk_events
inc dword ptr [rsp+0x98]
jmp talk_record_loop
talk_events:
mov rax, qword ptr [rsp+0x88]
movzx ecx, word ptr [rax+0x88]
cmp ecx, 120
jbe talk_restore
cmp ecx, 0x1000
ja talk_restore
mov rax, qword ptr [rax+0x80]
test rax, rax
je talk_restore
cmp qword ptr [rax], 0
je talk_restore
cmp qword ptr [rax+960], 0
je talk_restore
mov rcx, qword ptr [rsp+0x80]
call {data} + 0x1F00
test eax, eax
je talk_restore
mov r11, {data}
mov ecx, dword ptr [rsp+0x94]
cmp dword ptr [r11+0x1C], ecx
jne talk_restore
mov rdx, qword ptr [rsp+0xC0]
cmp qword ptr [r11+0x10], rdx
jne talk_restore
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne talk_restore
cmp qword ptr [rdi+0x50], rdx
jne talk_restore
mov r9, qword ptr [rsp+0xA0]
cmp qword ptr [rdi+0x510], r9
jne talk_restore
mov r10, qword ptr [rsp+0xA8]
cmp qword ptr [rdi+0x528], r10
jne talk_restore
mov rax, qword ptr [rsp+0xB0]
cmp qword ptr [r9], rax
jne talk_restore
mov rax, qword ptr [rsp+0xB8]
cmp qword ptr [r9+0xE90], rax
jne talk_restore
cmp qword ptr [r10], r9
jne talk_restore
cmp byte ptr [r10+8], 1
jne talk_restore
cmp byte ptr [r10+9], 1
ja talk_restore
cmp byte ptr [r10+0x0A], 0
jne talk_restore
cmp dword ptr [r10+0x48], 46
jne talk_restore
cmp qword ptr [r10+0x4C], 0
jne talk_restore
mov rcx, rdi
mov edx, 170
call {native_ladder_set_action}
talk_restore:
ldmxcsr dword ptr [rsp+0x90]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xC8
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

# Both the entry pose8 and wait/exit pose0 must exist in both common slots.
RESOURCE_ASM = (_SINGLE_MOTION_RESOURCES.replace('signpost_', 'talk_')
    .replace('mov dword ptr [rsp+0x34], 2\n',
             'mov dword ptr [rsp+0x34], 2\nmov byte ptr [rsp+0x30], 8\n')
    .replace('mov edx, 123\n', 'talk_resource_clip:\nmovzx edx, byte ptr [rsp+0x30]\n')
    .replace('cmp dword ptr [rsp+0x34], 2\n',
             'cmp byte ptr [rsp+0x30], 8\njne talk_resource_next_slot\n'
             'mov byte ptr [rsp+0x30], 0\nmov rax, qword ptr [rsp+0x28]\n'
             'mov rcx, qword ptr [rax+0x480]\njmp talk_resource_clip\n'
             'talk_resource_next_slot:\ncmp dword ptr [rsp+0x34], 2\n')
    .replace('mov dword ptr [rsp+0x34], 6\n',
             'mov dword ptr [rsp+0x34], 6\nmov byte ptr [rsp+0x30], 8\n'))


def apply_talk(previous_profile):
    """Pure0.48→0.49; two private payloads and no new native patches."""
    if previous_profile.get('tool_version') != '0.48' or len(previous_profile['hooks']) != 49:
        raise ValueError('Talk compatibility requires the complete frozen v0.48 profile')
    if (previous_profile.get('allocation_size'), previous_profile.get('data_offset')) != (0x14000, 0xF000):
        raise ValueError('Unexpected frozen private allocation/data layout')
    for index, name, rva, length, offset, capacity in EXPECTED_SLOTS:
        hook = previous_profile['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != (name, rva, length, offset, capacity):
            raise ValueError('Unexpected talk compatibility entry/private slot')
    plan = deepcopy(previous_profile)
    queued, carrier = (plan['hooks'][i] for i in (9, 46))
    marker = 'pushfq\ncall {data} - 0xCEF0\ncall {data} + 0x1310\n'
    if queued['asm'].count(marker) != 1:
        raise ValueError('Unexpected native queued saved frame')
    queued['asm'] = queued['asm'].replace(marker, marker+'call {data} + 0x1A00\n')
    carrier['asm'] += ('\n' + 'nop\n' * CARRIER_PADDING + HELPER_ASM
                      + 'nop\n' * HELPER_PADDING + RESOURCE_ASM)
    queued['purpose'] += '; accepted owned NPC request46 enters native common170 talk family'
    carrier['purpose'] += '; unreachable fixed tail carries owned NPC talk and resource helpers'
    plan.update(tool_version='0.49', stage='native_npc_talk_action', talk_revision=1,
        talk_changed_hook_indices=[9, 46], talk_dispatch=46,
        talk_native_queries=dict(start=346, completion=345),
        talk_common_actions=[170, 1155, 1156, 1157], talk_main_motion_ids=[8, 0],
        talk_local_event_indices=[0, 120], talk_required_motion_slots=[2, 6],
        talk_helper_offsets=dict(queued=CARRIER_SLOT+HELPER_ENTRY,
                                 resources=CARRIER_SLOT+RESOURCE_ENTRY),
        talk_resource_failure_fallback='previous_accepted_native_queue',
        talk_direct_interaction_script_save_writes=False,
        talk_native_state_and_other_features_preserved=True,
        talk_gameplay_confirmation_pending=True)
    return plan
