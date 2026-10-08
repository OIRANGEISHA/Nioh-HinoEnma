"""Start an accepted NPC rescue through the original common170/368 family.

Request22 is native query181 (737CC6 -> 73DE10). Common368 uses motion400
and the original local event references0/frame30 and13/frame0. This module
only asks706070 to enter common170 after complete owned records and clips
exist. It does not write NPC state, HP, interaction flags, inventory or saves.
"""
from copy import deepcopy

from hinoenma_talk import HELPER_ASM as _TALK_HELPER
from hinoenma_signpost import RESOURCE_ASM as _SINGLE_MOTION_RESOURCES


CARRIER_SLOT = 0x11000
HELPER_ENTRY = 0x200
RESOURCE_ENTRY = 0x700
CARRIER_PADDING = 203  # Frozen world-unload prefix309B; entry at11200.
HELPER_PADDING = 9  # Helper1271B; resource leaf fixed at11700.

EXPECTED_SLOTS = (
    (9, 'HE_QueuedDoor', 0x75129F, 11, 0x2400, 0x400),
    (47, 'HE_SameTemplateUnloadWorldActor', 0x8B1955, 8, CARRIER_SLOT, 0x800),
)

NATIVE_SIGNATURE_SPANS = (
    ('rescue_native_queue_before_revenant', 0x751242, 0x54),
    ('rescue_native_set_action', 0x706070, 0x4B),
    ('rescue_native_action_setter_prefix', 0x70ECE0, 0xFA),
    ('rescue_native_interaction_boundary', 0x710254, 0xD9),
    ('rescue_original_action_lookup_tail', 0x73FA45, 0xCC),
    ('rescue_request_predicate', 0x73DE10, 0x44),
    ('rescue_query181', 0x737CC6, 0x0F),
    ('rescue_query181_table', 0x73ADD4, 4),
    ('rescue_native_motion_index', 0x917500, 0xBC),
    ('rescue_original_interaction_start', 0x70936F, 0x40),
)


def _replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Frozen talk helper shape differs: ' + old.splitlines()[0])
    return source.replace(old, new, 1)


# The established queued frame calls with RSP%16=8. Eight saves and D8 locals
# align native callees with32B shadow space. Volatile SSE, MXCSR, flags and
# all saved registers are restored. The extra C8 local pins the NPC component.
HELPER_ASM = _TALK_HELPER.replace('talk_', 'rescue_').replace('0xC8', '0xD8')
HELPER_ASM = _replace_once(HELPER_ASM,
    'cmp word ptr [r9+4], 0\njne rescue_fail_b\n',
    'cmp word ptr [r9+4], 0\njne rescue_fail_b\n'
    'cmp word ptr [r9+6], 1\nje rescue_fail_b\n')
HELPER_ASM = _replace_once(HELPER_ASM,
    'cmp dword ptr [rax], ecx\njne rescue_fail_b\n'
    'mov qword ptr [rsp+0xB8], rax\n',
    'cmp dword ptr [rax], ecx\njne rescue_fail_b\n'
    'cmp dword ptr [rax+0x0C], 0\njne rescue_fail_b\n'
    'mov qword ptr [rsp+0xB8], rax\n'
    'mov rax, qword ptr [r9+0x240]\ntest rax, rax\nje rescue_fail_b\n'
    'cmp qword ptr [rax], r9\njne rescue_fail_b\n'
    'cmp qword ptr [rax+0x108], r9\njne rescue_fail_b\n'
    'cmp qword ptr [rax+0x20], 0\njle rescue_fail_b\n'
    'mov qword ptr [rsp+0xC8], rax\n')
if HELPER_ASM.count('cmp dword ptr [r10+0x48], 46\n') != 2:
    raise ValueError('Frozen talk request guards differ')
HELPER_ASM = HELPER_ASM.replace('cmp dword ptr [r10+0x48], 46\n',
                              'cmp dword ptr [r10+0x48], 22\n')
HELPER_ASM = _replace_once(HELPER_ASM,
    'mov dword ptr [rsp+0x98], 1155\n',
    'mov dword ptr [rsp+0x98], 368\n')
_family_start = HELPER_ASM.index('rescue_family:\n')
_family_end = HELPER_ASM.index('rescue_events:\n')
HELPER_ASM = HELPER_ASM[:_family_start] + '''rescue_family:
cmp dword ptr [rax+0x20], 400
jne rescue_restore
cmp dword ptr [rax+0x40], 0x001E0000
jne rescue_restore
cmp dword ptr [rax+0x44], 0x000DFFFF
jne rescue_restore
cmp dword ptr [rax+0x48], 0xFFFF0000
jne rescue_restore
''' + HELPER_ASM[_family_end:]
HELPER_ASM = _replace_once(HELPER_ASM, 'cmp ecx, 120\n', 'cmp ecx, 13\n')
HELPER_ASM = _replace_once(HELPER_ASM,
    'cmp qword ptr [rax+960], 0\n', 'cmp qword ptr [rax+104], 0\n')
HELPER_ASM = _replace_once(HELPER_ASM,
    'call {data} + 0x1F00\n', 'call {data} + 0x2700\n')
HELPER_ASM = _replace_once(HELPER_ASM,
    'cmp qword ptr [r9+0xE90], rax\njne rescue_restore\n',
    'cmp qword ptr [r9+0xE90], rax\njne rescue_restore\n'
    'cmp dword ptr [rax+0x0C], 0\njne rescue_restore\n'
    'mov rax, qword ptr [rsp+0xC8]\n'
    'cmp qword ptr [r9+0x240], rax\njne rescue_restore\n'
    'cmp qword ptr [rax], r9\njne rescue_restore\n'
    'cmp qword ptr [rax+0x108], r9\njne rescue_restore\n'
    'cmp qword ptr [rax+0x20], 0\njle rescue_restore\n'
    'cmp dword ptr [rdx+0xEF0], 0\njne rescue_restore\n')

# 917500 is the original bounded motion hash lookup. Require400 in both
# owned common slots2 and6 and a nonnull clip inside the proven468..470 bank.
RESOURCE_ASM = (_SINGLE_MOTION_RESOURCES.replace('signpost_', 'rescue_')
                .replace('mov edx, 123\n', 'mov edx, 400\n'))


def apply_rescue(previous_profile):
    """Pure0.49->0.50; two private payloads, all49 native sites unchanged."""
    if previous_profile.get('tool_version') != '0.49' or len(previous_profile['hooks']) != 49:
        raise ValueError('NPC rescue requires the complete frozen v0.49 profile')
    if (previous_profile.get('allocation_size'), previous_profile.get('data_offset')) != (0x14000, 0xF000):
        raise ValueError('Unexpected frozen private allocation/data layout')
    for index, name, rva, length, offset, capacity in EXPECTED_SLOTS:
        hook = previous_profile['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != (name, rva, length, offset, capacity):
            raise ValueError('Unexpected NPC rescue entry/private slot')
    plan = deepcopy(previous_profile)
    queued, carrier = (plan['hooks'][i] for i in (9, 47))
    marker = 'pushfq\ncall {data} - 0xCEF0\ncall {data} + 0x1310\ncall {data} + 0x1A00\n'
    if queued['asm'].count(marker) != 1:
        raise ValueError('Unexpected frozen queued saved frame')
    queued['asm'] = queued['asm'].replace(marker, marker+'call {data} + 0x2200\n')
    carrier['asm'] += ('\n' + 'nop\n' * CARRIER_PADDING + HELPER_ASM
                      + 'nop\n' * HELPER_PADDING + RESOURCE_ASM)
    queued['purpose'] += '; accepted owned nonplayer NPC request22 enters native common170 rescue family'
    carrier['purpose'] += '; unreachable fixed tail carries NPC rescue and resource helpers'
    plan.update(tool_version='0.50', stage='native_npc_rescue_action', rescue_revision=1,
        rescue_changed_hook_indices=[9, 47], rescue_dispatch=22,
        rescue_native_queries=dict(start=181), rescue_common_actions=[170, 368],
        rescue_main_motion_ids=[400], rescue_local_event_indices=[0, 13],
        rescue_required_motion_slots=[2, 6],
        rescue_helper_offsets=dict(queued=CARRIER_SLOT+HELPER_ENTRY,
                                   resources=CARRIER_SLOT+RESOURCE_ENTRY),
        rescue_resource_failure_fallback='previous_accepted_native_queue',
        rescue_direct_interaction_npc_hp_script_save_writes=False,
        rescue_native_state_and_other_features_preserved=True,
        rescue_gameplay_confirmation_pending=True)
    return plan
