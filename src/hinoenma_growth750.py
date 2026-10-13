"""Additive level750 / Focus revision over the unchanged Beta5.6.2 source.

Only HE_AttributeOverlay changes. No saved levels, actor metadata, equipment,
component indices, current HP, or other payloads are written by this revision.
The native context factors retain their original float32/truncation order;
the new 401 threshold multiplies only the fresh Boss basis, before player
deltas. The selected native flat attack is inherited separately from main.
"""
from copy import deepcopy

from hinoenma_combat_growth import COMBAT_GROWTH_ASM
from living_weapon_start_production_layout import validate_production_layout

BASE_VERSION = '1.0.0-beta.5.6.2'
REVISION = 1
HOOK_NAME = 'HE_AttributeOverlay'
LEVEL_MAPPING = dict(level_min=0, level_max=750, index_min=1, index_max=4525,
                     rounding='floor', formula='1 + floor(4524 * level / 750)')


def mapped_index(level):
    """Mathematical endpoint 0 is valid here; live save levels require 1..750."""
    if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 750:
        raise ValueError('Expected a mathematical level in 0..750')
    return 1 + 4524 * level // 750


# 80..97 are scratch only until attr_copy_boss. 90 stores the validated saved
# level across the native leaf calls; 80..8F retain the prior revision's ABI.
GROWTH_PREFIX = '''cmp r14, qword ptr [rsi+0x108]
jne growth750_done
mov rcx, qword ptr [r14+0xE90]
mov eax, dword ptr [r14]
cmp eax, dword ptr [rcx]
jne growth750_done
mov rax, {hp_growth_saved_manager}
mov rax, qword ptr [rax]
test rax, rax
je growth750_done
mov edx, dword ptr [rax+0xAE5C4]
cmp edx, 1
jb growth750_done
cmp edx, 750
ja growth750_done
mov dword ptr [rsp+0x90], edx
mov eax, edx
imul eax, eax, 4524
xor edx, edx
mov r8d, 750
div r8d
lea edx, [rax+1]
cmp edx, dword ptr [rsi+8]
jbe growth750_multiply
'''

# Reuse the reviewed exact native curve/context block. When the actor already
# has an equal or higher native index, boss_stats has generated that basis;
# it still reaches growth750_multiply, without replacing or re-scaling it.
GROWTH_ASM = GROWTH_PREFIX + COMBAT_GROWTH_ASM.split(
    'stmxcsr dword ptr [rsp+0x8C]\n', 1)[1].rsplit(
    'combat_growth_keep_native:\n', 1)[0]
GROWTH_ASM = GROWTH_ASM.replace(
    'mov dword ptr [rsp+0x80], edx\n',
    'stmxcsr dword ptr [rsp+0x8C]\nmov dword ptr [rsp+0x80], edx\n', 1)
GROWTH_ASM += '''growth750_multiply:
cmp dword ptr [rsp+0x90], 401
jb growth750_done
mov eax, dword ptr [r12]
shl rax, 1
mov r8d, 0xFFFFFFFF
cmp rax, r8
cmova rax, r8
mov dword ptr [r12], eax
'''
for _offset in (8, 0x30, 0x58, 0x80, 0xA8):
    # DWORD Boss scalars use a wide intermediate and saturate on overflow.
    GROWTH_ASM += f'''mov eax, dword ptr [r12+0x{_offset:X}]
imul rax, rax, 6
xor edx, edx
mov ecx, 5
div rcx
cmp rax, r8
cmova rax, r8
mov dword ptr [r12+0x{_offset:X}], eax
'''
GROWTH_ASM += 'growth750_done:\n'


# 218..21F is the unused gap after the 198-byte Boss snapshot at80 and before
# the naked-reference snapshot at220. It survives cache capture and the loop.
FLAT_CAPTURE = '''movsxd rax, dword ptr [r12+rdx+0x0C]
movsxd rcx, dword ptr [rsp+rdx+0x22C]
sub rax, rcx
mov qword ptr [rsp+0x218], rax
'''
FLAT_RESTORE = '''movsxd rax, dword ptr [r12+rdx+4]
add rax, qword ptr [rsp+0x218]
mov r9d, 0x7FFFFFFF
cmp rax, r9
cmovg rax, r9
mov r9, -2147483648
cmp rax, r9
cmovl rax, r9
mov dword ptr [r12+rdx+4], eax
'''


def _replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Growth750 source insertion does not match exactly')
    return source.replace(old, new, 1)


def apply_growth750(previous):
    """Pure candidate derivation; keep released manifests and old generators."""
    validate_production_layout(previous)
    if (previous.get('tool_version') != BASE_VERSION
            or previous.get('growth750_revision')
            or previous.get('inherent_element_revision') != 2):
        raise ValueError('Unmodified current Beta5.6.2 required')
    plan = deepcopy(previous)
    hook = next(h for h in plan['hooks'] if h['name'] == HOOK_NAME)
    if (hook['rva'], hook['length'], hook['code_offset'], hook['code_capacity']) != (
            0x7C82DB, 5, 0x1B000, 0x1000):
        raise ValueError('Exact current attribute slot required')
    source = _replace_once(hook['asm'], COMBAT_GROWTH_ASM, GROWTH_ASM)
    source = _replace_once(source,
        'imul edx, edx, 0x28\nmov eax, dword ptr [r12+rdx+8]',
        'imul edx, edx, 0x28\n' + FLAT_CAPTURE + 'mov eax, dword ptr [r12+rdx+8]')
    source = _replace_once(source,
        'mov dword ptr [r12+rdx], r8d\nadd edx, 0x28',
        'mov dword ptr [r12+rdx], r8d\n' + FLAT_RESTORE + 'add edx, 0x28')
    hook.update(asm=source, purpose=hook['purpose'] +
        '; level0..750 -> index1..4525; from401 Boss-only HPx2/ATKx1.2; '
        'selected native signed flat-attack delta retained separately')
    plan.update(growth750_revision=REVISION,
        growth750_base_version=BASE_VERSION,
        growth750_trial=True, stage='growth750_focus_local_trial',
        hp_growth_level_mapping=deepcopy(LEVEL_MAPPING),
        combat_growth_level_mapping=deepcopy(LEVEL_MAPPING),
        growth750_extra_multipliers=dict(first_level=401, hp=[2, 1], attack=[6, 5]),
        growth750_focus_channels=['hp', 'attack', 'defense', 'luck'],
        growth750_flat_attack_separate=True,
        growth750_gameplay_confirmation_pending=True)
    validate_production_layout(plan)
    return plan
