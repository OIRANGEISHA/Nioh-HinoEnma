"""Extend the verified HP stage with exact native Ki, attack and defense growth.

Only the captured playable Hino-Enma's derived basis is changed. A valid
saved level uses the preceding HP stage's mapping (1..400 -> 1..1410, capped
above 400); the mapped index must exceed its native scene index. The component index,
metadata, equipment, saved growth and secondary curve fields remain intact.
The original player/equipment delta and later native Ki/HP modifiers still run.

For metadata role 1 the native Boss function gives all five physical attack
records the same basis; its role-0 guardian override does not apply. Attack
and defense reproduce the native two-stage float/truncate calculation and
the mutually exclusive status/difficulty factors before the existing copy.
"""
from copy import deepcopy

from hinoenma_hp_growth import HP_GROWTH_ASM


# The existing frame's 80..8F bytes have not yet received the Boss snapshot.
# They hold the desired index, two integer intermediates and saved MXCSR until the
# attr_copy_boss loop overwrites them. Native call shadow space is 00..1F;
# saved volatile XMM registers occupy 20..7F.
COMBAT_GROWTH_ASM = (
    HP_GROWTH_ASM.split('call {hp_growth_native_hp}\n', 1)[0]
        .replace('hp_growth_keep_native', 'combat_growth_keep_native')
    + '''stmxcsr dword ptr [rsp+0x8C]
mov dword ptr [rsp+0x80], edx
call {hp_growth_native_hp}
mov dword ptr [r12], eax
mov ecx, dword ptr [rsp+0x80]
call {combat_growth_native_ki}
mov rdx, qword ptr [r14+0xE90]
mov eax, dword ptr [rdx+0xD0]
xorps xmm1, xmm1
cvtsi2ss xmm1, rax
mulss xmm0, xmm1
cvttss2si rax, xmm0
mov dword ptr [r12+4], eax
mov rcx, qword ptr [r14+0xE90]
mov edx, dword ptr [rsp+0x80]
call {combat_growth_native_attack}
mov eax, eax
xorps xmm0, xmm0
cvtsi2ss xmm0, rax
mulss xmm0, dword ptr [rsi+0x12A0]
cvttss2si rax, xmm0
mov dword ptr [rsp+0x84], eax
mov rcx, qword ptr [r14+0xE90]
mov edx, dword ptr [rsp+0x80]
call {combat_growth_native_defense}
mov eax, eax
xorps xmm0, xmm0
cvtsi2ss xmm0, rax
mulss xmm0, dword ptr [rsi+0x12A4]
cvttss2si rax, xmm0
mov dword ptr [rsp+0x88], eax
mov rax, {combat_growth_world_slot}
mov rax, qword ptr [rax]
cmp qword ptr [rax+0x560], 0
je combat_growth_write_baseline
call {combat_growth_difficulty_index}
movsxd rdx, eax
mov r10, {combat_growth_one}
movss xmm4, dword ptr [r10]
movaps xmm5, xmm4
cmp byte ptr [rsi+0x12CC], 0
jne combat_growth_ordinary_factors
lea r10, [rsi+0x12AD]
mov ecx, 32
combat_growth_status_scan:
cmp byte ptr [r10], 0
jne combat_growth_status_factors
inc r10
dec ecx
jne combat_growth_status_scan
combat_growth_ordinary_factors:
mov rax, qword ptr [r14+0xE90]
test byte ptr [rax+4], 2
jne combat_growth_write_baseline
cmp byte ptr [r14+0x44F], 0
jne combat_growth_write_baseline
cmp edx, 5
jl combat_growth_write_baseline
mov r10, {combat_growth_attack_high_factor}
movss xmm4, dword ptr [r10]
jmp combat_growth_apply_factors
combat_growth_status_factors:
mov rax, qword ptr [r14+0xE90]
movzx ecx, word ptr [rax+0xFC]
movd xmm2, ecx
cvtdq2ps xmm2, xmm2
mov r10, {combat_growth_percent}
mulss xmm2, dword ptr [r10]
movaps xmm4, xmm2
mov r10, {combat_growth_attack_factor_table}
mulss xmm4, dword ptr [r10+rdx*4]
movaps xmm0, xmm5
subss xmm0, xmm4
xorps xmm3, xmm3
comiss xmm0, xmm3
jb combat_growth_attack_factor_ready
movaps xmm4, xmm5
combat_growth_attack_factor_ready:
mov r10, {combat_growth_defense_factor_table}
mulss xmm2, dword ptr [r10+rdx*4]
movaps xmm0, xmm5
subss xmm0, xmm2
comiss xmm0, xmm3
jae combat_growth_apply_factors
movaps xmm5, xmm2
combat_growth_apply_factors:
mov eax, dword ptr [rsp+0x84]
xorps xmm0, xmm0
cvtsi2ss xmm0, rax
mulss xmm0, xmm4
cvttss2si rax, xmm0
mov dword ptr [rsp+0x84], eax
mov eax, dword ptr [rsp+0x88]
xorps xmm0, xmm0
cvtsi2ss xmm0, rax
mulss xmm0, xmm5
cvttss2si rax, xmm0
mov dword ptr [rsp+0x88], eax
combat_growth_write_baseline:
mov eax, dword ptr [rsp+0x84]
mov dword ptr [r12+0x08], eax
mov dword ptr [r12+0x30], eax
mov dword ptr [r12+0x58], eax
mov dword ptr [r12+0x80], eax
mov dword ptr [r12+0xA8], eax
mov eax, dword ptr [rsp+0x88]
mov dword ptr [r12+0xE0], eax
ldmxcsr dword ptr [rsp+0x8C]
combat_growth_keep_native:
'''
)


NATIVE_TARGETS = dict(
    combat_growth_native_ki=0x7EFDC0,
    combat_growth_native_attack=0x7EFBF0,
    combat_growth_native_defense=0x7EFC40,
    combat_growth_difficulty_index=0x8B08B0,
    combat_growth_world_slot=0x18715E0,
    combat_growth_one=0x1588938,
    combat_growth_percent=0x1588764,
    combat_growth_attack_high_factor=0x11A07AC,
    combat_growth_attack_factor_table=0x11A11E0,
    combat_growth_defense_factor_table=0x11A11F8,
)


def apply_combat_growth(previous_profile):
    if (previous_profile.get('tool_version') != '0.42'
            or previous_profile.get('hp_growth_revision') != 2
            or len(previous_profile['hooks']) != 45):
        raise ValueError('Combat growth requires the complete verified v0.42 revision-2 profile')
    plan = deepcopy(previous_profile)
    hook = next(entry for entry in plan['hooks'] if entry['name'] == 'HE_AttributeOverlay')
    if (hook['asm'].count(HP_GROWTH_ASM) != 1 or hook['rva'] != 0x7C82DB
            or hook['code_offset'] != 0x3C00 or hook['code_capacity'] != 0xC00
            or not hook['asm'].endswith('jmp {return}\n')):
        raise ValueError('Unexpected verified attribute overlay slot or HP stage')
    hook['asm'] = hook['asm'].replace(HP_GROWTH_ASM, COMBAT_GROWTH_ASM)
    hook['purpose'] += ('; extend the same mapped saved-level basis to native Ki, '
        'five physical attack scalars and defense with exact native modifiers')
    plan['targets'].update(NATIVE_TARGETS)
    plan.update(tool_version='0.43', stage='native_boss_combat_level_growth',
        combat_growth_revision=1,
        combat_growth_level_source='persistent_manager_AE5C4',
        combat_growth_valid_level_range=[1, 750],
        combat_growth_level_mapping=deepcopy(plan['hp_growth_level_mapping']),
        combat_growth_keeps_higher_native_scene_index=True,
        combat_growth_preserves_secondary_curve_fields=True,
        combat_growth_fields=['hp', 'ki', 'attack', 'defense'],
        combat_growth_gameplay_confirmation_pending=True,
        pending_level_growth_fields=[])
    return plan
