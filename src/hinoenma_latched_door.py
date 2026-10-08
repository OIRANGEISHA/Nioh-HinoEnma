"""Queue the verified wooden-latch request through its native action events.

The observed object15/kind2/instance1 request16 maps via native query115
from common170 to common157/motion223. Its event descriptors0/75, native
tracked references and door script remain responsible for starting/opening.
Only complete owned common records, descriptors and both motion clips permit
the animated route; otherwise the prior immediate interaction remains.
No door flags, save state, event resources or item quantities are written.
"""
from copy import deepcopy

from hinoenma_hot_spring import _restore
from hinoenma_signpost import RESOURCE_ASM as _SINGLE_MOTION_RESOURCES


CARRIER_SLOT = 0x10000
GENERIC_ENTRY = 0x300
QUEUED_ENTRY = 0x310
HELPER_BODY = 0x320
RESOURCE_ENTRY = 0x700
CARRIER_PADDING = 430  # Frozen v047 child prefix is338 bytes; entry is+300.
HELPER_PADDING = 43  # Keep the resource leaf fixed at10700 after assembly.

EXPECTED_SLOTS = (
    (8, 'HE_Interaction', 0x751156, 10, 0x2000, 0x400),
    (9, 'HE_QueuedDoor', 0x75129F, 11, 0x2400, 0x400),
    (45, 'HE_SameTemplateUnloadChild', 0x8B1868, 7, CARRIER_SLOT, 0x800),
)

NATIVE_SIGNATURE_SPANS = (
    ('latched_door_native_queue_before_revenant', 0x751242, 0x54),
    ('latched_door_native_set_action', 0x706070, 0x4B),
    ('latched_door_native_action_setter_prefix', 0x70ECE0, 0xFA),
    ('latched_door_native_interaction_boundary', 0x710254, 0xD9),
    ('latched_door_original_action_lookup_tail', 0x73FA45, 0xCC),
    ('latched_door_request_predicate', 0x73DE10, 0x44),
    ('latched_door_query115', 0x737A10, 0x0F),
    ('latched_door_query115_table', 0x73ACCC, 4),
    ('latched_door_native_motion_index', 0x917500, 0xBC),
    ('latched_door_original_interaction_start', 0x70936F, 0x40),
    ('latched_door_object_actor_reference', 0x744D50, 0x74),
)

# Call arrives withRSP%16==8; a mode push plus eight saves aligns this frame.
# The generic entry returns its eligibility inCF only; queued mode restores
# every caller flag. Volatile SSE, MXCSR and the Win64 shadow space are saved.
HELPER_ASM = '''latched_door_helper_body:
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
jne latched_door_fail_a
cmp dword ptr [r11+4], 0x58E5E
je latched_door_selected
cmp dword ptr [r11+4], 0x51BE1
jne latched_door_fail_a
latched_door_selected:
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je latched_door_fail_a
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne latched_door_fail_a
cmp dword ptr [rdx+4], 0x10000
jne latched_door_fail_a
cmp dword ptr [rdx], 0x58E5E
je latched_door_role
cmp dword ptr [rdx], 0x51BE1
jne latched_door_fail_a
latched_door_role:
cmp dword ptr [rdx+0xEF0], 0
jne latched_door_fail_a
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je latched_door_fail_a
cmp dword ptr [rax+0x0C], 1
jne latched_door_fail_a
mov ecx, dword ptr [rdx]
cmp dword ptr [rax], ecx
jne latched_door_fail_a
mov rax, qword ptr [rdx+0x240]
test rax, rax
je latched_door_fail_a
cmp qword ptr [rax], rdx
jne latched_door_fail_a
cmp qword ptr [rax+0x108], rdx
jne latched_door_fail_a
cmp qword ptr [rax+0x20], 0
jle latched_door_fail_a
jmp latched_door_owner
latched_door_fail_a:
jmp latched_door_restore
latched_door_owner:
mov rax, qword ptr [rdx+0x230]
test rax, rax
je latched_door_fail_b
cmp qword ptr [rax], rdx
jne latched_door_fail_b
cmp qword ptr [rax+8], rdi
jne latched_door_fail_b
cmp qword ptr [rdi+0x50], rdx
jne latched_door_fail_b
mov r9, qword ptr [rsp+0xB8]
mov r10, qword ptr [rsp+0xD0]
cmp qword ptr [rsp+0xE0], 0
je latched_door_pair
mov r9, qword ptr [rdi+0x510]
mov r10, qword ptr [rdi+0x528]
latched_door_pair:
test r9, r9
je latched_door_fail_b
cmp dword ptr [r9], 15
jne latched_door_fail_b
cmp dword ptr [r9+4], 0x10002
jne latched_door_fail_b
mov rcx, qword ptr [r9+0x320]
test rcx, rcx
je latched_door_object_owner
cmp rcx, rdx
jne latched_door_fail_b
latched_door_object_owner:
test r10, r10
je latched_door_fail_b
cmp qword ptr [r10], r9
jne latched_door_fail_b
cmp word ptr [r10+8], 0x0101
jne latched_door_fail_b
cmp byte ptr [r10+0x0A], 0
jne latched_door_fail_b
cmp dword ptr [r10+0x48], 16
jne latched_door_fail_b
cmp qword ptr [r10+0x4C], 0
jne latched_door_fail_b
jmp latched_door_idle
latched_door_fail_b:
jmp latched_door_restore
latched_door_idle:
mov rax, qword ptr [rdi+0x58]
test rax, rax
je latched_door_fail_c
cmp dword ptr [rax], 0
jne latched_door_fail_c
mov rcx, qword ptr [rdi+0x78]
test rcx, rcx
je latched_door_fail_c
cmp qword ptr [rax+0x38], rcx
jne latched_door_fail_c
mov rax, qword ptr [rax+0x20]
test rax, rax
je latched_door_fail_c
test byte ptr [rax], 1
je latched_door_fail_c
test byte ptr [rax+1], 8
jne latched_door_fail_c
mov rax, qword ptr [rdx+0x38]
test rax, rax
je latched_door_fail_c
cmp dword ptr [rax+0x50], 1
ja latched_door_fail_c
mov qword ptr [rsp+0x80], rax
jmp latched_door_records
latched_door_fail_c:
jmp latched_door_restore
latched_door_records:
mov rax, qword ptr [rdi+0x80]
test rax, rax
je latched_door_restore
cmp dword ptr [rax+0x130], 0
je latched_door_restore
cmp dword ptr [rax+0x130], 0x1000
ja latched_door_restore
cmp qword ptr [rax+0x128], 0
je latched_door_restore
mov qword ptr [rsp+0x88], rax
lea rcx, [rdi+0x70]
mov edx, 170
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je latched_door_restore
mov rcx, qword ptr [rsp+0x88]
cmp qword ptr [rax+0x38], rcx
jne latched_door_restore
cmp byte ptr [rax+0x40], 0
je latched_door_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je latched_door_restore
cmp dword ptr [rax+0x20], -1
jne latched_door_restore
lea rcx, [rdi+0x70]
mov edx, 157
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je latched_door_restore
mov rcx, qword ptr [rsp+0x88]
cmp qword ptr [rax+0x38], rcx
jne latched_door_restore
cmp byte ptr [rax+0x40], 0
je latched_door_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je latched_door_restore
cmp dword ptr [rax+0x20], 223
jne latched_door_restore
cmp dword ptr [rax+0x34], -1
jne latched_door_restore
cmp dword ptr [rax+0x40], 0
jne latched_door_restore
cmp dword ptr [rax+0x44], 0x4BFFFF
jne latched_door_restore
cmp dword ptr [rax+0x48], 0xFFFF0000
jne latched_door_restore
mov rax, qword ptr [rsp+0x88]
movzx ecx, word ptr [rax+0x88]
cmp ecx, 75
jbe latched_door_restore
cmp ecx, 0x1000
ja latched_door_restore
mov rax, qword ptr [rax+0x80]
test rax, rax
je latched_door_restore
cmp qword ptr [rax], 0
je latched_door_restore
cmp qword ptr [rax+600], 0
je latched_door_restore
mov rcx, qword ptr [rsp+0x80]
call {data} + 0x1700
test eax, eax
je latched_door_restore
inc dword ptr [rsp+0x94]
cmp qword ptr [rsp+0xE0], 0
je latched_door_restore
mov rcx, rdi
mov edx, 170
call {native_ladder_set_action}
latched_door_restore:
cmp qword ptr [rsp+0xE0], 0
jne latched_door_epilogue
and qword ptr [rsp+0xD8], -2
cmp dword ptr [rsp+0x94], 0
je latched_door_epilogue
or qword ptr [rsp+0xD8], 1
latched_door_epilogue:
''' + _restore() + '''ret
'''

RESOURCE_ASM = (_SINGLE_MOTION_RESOURCES.replace('signpost_', 'latched_door_')
                .replace('mov edx, 123\n', 'mov edx, 223\n'))


def apply_latched_door(previous_profile):
    """Pure verified0.47→0.48: same49 sites/allocation, three private slots."""
    if previous_profile.get('tool_version') != '0.47' or len(previous_profile['hooks']) != 49:
        raise ValueError('Latched door requires the complete frozen v0.47 profile')
    if (previous_profile.get('allocation_size'), previous_profile.get('data_offset')) != (0x14000, 0xF000):
        raise ValueError('Unexpected frozen private allocation/data layout')
    for index, name, rva, length, offset, capacity in EXPECTED_SLOTS:
        hook = previous_profile['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != (name, rva, length, offset, capacity):
            raise ValueError('Unexpected latch compatibility entry/private slot')
    plan = deepcopy(previous_profile)
    generic, queued, carrier = (plan['hooks'][i] for i in (8, 9, 45))
    marker = 'generic_immediate:\ncall {data} - 0xCF00\n'
    if generic['asm'].count(marker) != 1:
        raise ValueError('Unexpected generic immediate branch')
    generic['asm'] = generic['asm'].replace(marker,
        'generic_immediate:\ncall {data} + 0x1300\njc generic_original\ncall {data} - 0xCF00\n')
    marker = '\n' + 'nop\n' * 17 + 'hot_spring_generic_entry:\n'
    if generic['asm'].count(marker) != 1:
        raise ValueError('Unexpected fixed Hot Spring helper padding')
    generic['asm'] = generic['asm'].replace(marker,
        '\n' + 'nop\n' * 6 + 'hot_spring_generic_entry:\n')
    marker = 'pushfq\ncall {data} - 0xCEF0\n'
    if queued['asm'].count(marker) != 1:
        raise ValueError('Unexpected native queued saved frame')
    queued['asm'] = queued['asm'].replace(marker,
        marker + 'call {data} + 0x1310\n')
    carrier['asm'] += ('\n' + 'nop\n' * CARRIER_PADDING
        + 'latched_door_generic_entry:\npush 0\njmp latched_door_helper_body\n'
        + 'nop\n' * 12
        + 'latched_door_queued_entry:\npush 1\njmp latched_door_helper_body\n'
        + 'nop\n' * 12 + HELPER_ASM
        + 'nop\n' * HELPER_PADDING + RESOURCE_ASM)
    generic['purpose'] += '; complete owned object15 request16 latch action permits native queue'
    queued['purpose'] += '; scoped idle native170 entry for object15 request16 wooden latch'
    carrier['purpose'] += '; unreachable fixed tail carries guarded latch preflight/resource helpers'
    plan.update(tool_version='0.48', stage='native_latched_door_action',
        latched_door_revision=1, latched_door_changed_hook_indices=[8, 9, 45],
        latched_door_object=dict(id=15, kind=2, instance=1),
        latched_door_dispatch=16, latched_door_native_query=115,
        latched_door_common_actions=[170, 157], latched_door_main_motion_id=223,
        latched_door_local_event_indices=[0, 75], latched_door_required_motion_slots=[2, 6],
        latched_door_helper_offsets=dict(generic=CARRIER_SLOT+GENERIC_ENTRY,
            queued=CARRIER_SLOT+QUEUED_ENTRY, body=CARRIER_SLOT+HELPER_BODY,
            resources=CARRIER_SLOT+RESOURCE_ENTRY),
        latched_door_resource_failure_fallback='previous_native_immediate_interaction',
        latched_door_native_state_and_other_features_preserved=True,
        latched_door_gameplay_confirmation_pending=True)
    return plan
