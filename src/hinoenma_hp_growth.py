"""Grow only the captured Hino-Enma's native Boss HP basis with saved level.

This is the first stage of player-level compatibility. The existing native
Boss calculation still runs first, and its other derived fields are retained.
The HP leaf uses the actor's own metadata and the persistent level source used
by growth_load; its owned preview buffer may already have been reset to one.
User-selected mapping: level1 -> index1, level400 -> index1410, integer floor
between them. Levels above400 are capped at that endpoint, not extrapolated.
Higher native scene indices remain authoritative. Neither the component's
index, saved growth, equipment, nor current/maximum HP is written here.
"""
from copy import deepcopy


HP_GROWTH_ASM = '''cmp r14, qword ptr [rsi+0x108]
jne hp_growth_keep_native
mov rcx, qword ptr [r14+0xE90]
mov eax, dword ptr [r14]
cmp eax, dword ptr [rcx]
jne hp_growth_keep_native
mov rax, {hp_growth_saved_manager}
mov rax, qword ptr [rax]
test rax, rax
je hp_growth_keep_native
mov edx, dword ptr [rax+0xAE5C4]
cmp edx, 1
jb hp_growth_keep_native
cmp edx, 750
ja hp_growth_keep_native
cmp edx, 400
jbe hp_growth_map_level
mov edx, 400
hp_growth_map_level:
mov eax, edx
dec eax
imul eax, eax, 1409
xor edx, edx
mov r8d, 399
div r8d
lea edx, [rax+1]
cmp edx, dword ptr [rsi+8]
jbe hp_growth_keep_native
call {hp_growth_native_hp}
mov dword ptr [r12], eax
hp_growth_keep_native:
'''


def apply_hp_growth(previous_profile):
    if previous_profile.get('tool_version') != '0.41' or len(previous_profile['hooks']) != 45:
        raise ValueError('HP growth requires the complete verified v0.41 profile')
    plan = deepcopy(previous_profile)
    hook = next(entry for entry in plan['hooks'] if entry['name'] == 'HE_AttributeOverlay')
    marker = '''cmp qword ptr [r12+0x1A8], 0
je attr_overlay_done
xor ecx, ecx
attr_copy_boss:
'''
    if (hook['asm'].count(marker) != 1 or hook['rva'] != 0x7C82DB
            or hook['code_offset'] != 0x3C00 or hook['code_capacity'] != 0xC00):
        raise ValueError('Unexpected verified attribute overlay slot or source')
    hook['asm'] = hook['asm'].replace(marker,
        marker.split('xor ecx', 1)[0] + HP_GROWTH_ASM + 'xor ecx, ecx\nattr_copy_boss:\n')
    hook['purpose'] += ('; map saved player levels 1..400 linearly to native Boss indices '
        '1..1410, cap higher valid levels at 400, retain higher scene index '
        'and additive native player/equipment delta')
    plan['targets'].update(hp_growth_native_hp=0x7EFC80,
                           hp_growth_saved_manager=0x189F408)
    plan.update(tool_version='0.42', stage='native_boss_hp_level_growth',
        hp_growth_revision=2, hp_growth_level_source='persistent_manager_AE5C4',
        hp_growth_valid_level_range=[1, 750],
        hp_growth_level_mapping={'level_min': 1, 'level_max': 400,
            'index_min': 1, 'index_max': 1410, 'rounding': 'floor',
            'higher_valid_levels': 'cap_at_level_400'},
        hp_growth_keeps_higher_native_scene_index=True,
        hp_growth_gameplay_confirmation_pending=True,
        pending_level_growth_fields=['ki', 'attack', 'defense'])
    return plan
