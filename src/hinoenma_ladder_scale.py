"""Bounded Common ladder scale repair for the current local Hino-Enma player.

The original 55 hooks and data pages remain unchanged. Three scalar SIMD reads
use unit scale only for owned Common ladder actions; one native sampler hook
captures the requested clip in its local stack slot. The pending-clip check
also covers native endpoint displacement before the next action is committed.
No actor, motion, resource, input or diagnostic field is modified.
"""
from __future__ import annotations
from copy import deepcopy

PLAYER_SLOT_RVA = 0x18A0490


ORIGINAL_SIGNATURES = (
    ('HE_LadderScaleRdiDraft', 0x95470C, 'F3 0F 10 97 20 03 00 00', 'rdi', 'xmm2'),
    ('HE_LadderScaleRbxDraft', 0x954849, 'F3 0F 10 93 20 03 00 00', 'rbx', 'xmm2'),
    ('HE_LadderScaleRenderDraft', 0x954091, 'F3 0F 10 80 20 03 00 00', 'rax', 'xmm0'),
)


SAVE = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
'''


RESTORE = '''pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {return}
'''


def pointer_guard(register: str, prefix: str) -> str:
    """Reject null, low and noncanonical pointers before an added dereference."""
    return f'''cmp {register}, 0x10000
jb {prefix}_done
mov rcx, {register}
shr rcx, 47
jne {prefix}_done
'''


def scale_asm(index: int) -> str:
    name, _, _, owner, xmm = ORIGINAL_SIGNATURES[index]
    prefix = f'ladder_scale_{index}'
    owner_copy = f'mov r8, {owner}\n' if owner != 'rax' else 'mov r8, qword ptr [rsp+0x30]\n'
    code = f'movss {xmm}, dword ptr [{owner}+0x320]\n' + SAVE + owner_copy
    if index == 2:
        # Original R9 is a blend-layer descriptor, independent of controller R9.
        code += 'mov rax, qword ptr [rsp+0x10]\n' + pointer_guard('rax', prefix)
        code += f'cmp byte ptr [rax+0x28], 0\nje {prefix}_done\n'
    code += '''mov r11, {data}
cmp dword ptr [r11+4], 0
je P_done
mov r10, qword ptr [r11+0x10]
'''.replace('P_', prefix + '_')
    code += pointer_guard('r10', prefix)
    code += '''mov rax, {player_slot}
cmp r10, qword ptr [rax]
jne P_done
mov eax, dword ptr [r10]
cmp eax, dword ptr [r11+4]
jne P_done
cmp eax, 0x58E5E
je P_hino
cmp eax, 0x51BE1
jne P_done
P_hino:
cmp dword ptr [r10+4], 0x10000
jne P_done
cmp dword ptr [r10+0xEF0], 0
jne P_done
mov rax, qword ptr [r10+0xE90]
'''.replace('P_', prefix + '_')
    code += pointer_guard('rax', prefix)
    code += '''cmp dword ptr [rax+0x0C], 1
jne P_done
cmp r8, qword ptr [r10+0x38]
jne P_done
cmp r10, qword ptr [r8]
jne P_done
mov rax, qword ptr [r10+0x230]
'''.replace('P_', prefix + '_')
    code += pointer_guard('rax', prefix)
    code += '''cmp r10, qword ptr [rax]
jne P_done
mov r9, qword ptr [rax+8]
'''.replace('P_', prefix + '_')
    code += pointer_guard('r9', prefix)
    code += '''cmp r10, qword ptr [r9+0x50]
jne P_done
mov rax, qword ptr [r9+0x58]
'''.replace('P_', prefix + '_')
    code += pointer_guard('rax', prefix)
    code += '''cmp byte ptr [rax+0x40], 0
je P_done
cmp dword ptr [rax], 56
jb P_done
cmp dword ptr [rax], 70
ja P_done
mov rdx, qword ptr [r9+0x80]
test rdx, rdx
je P_done
cmp rdx, qword ptr [rax+0x38]
jne P_done
mov rdx, qword ptr [rax+0x20]
'''.replace('P_', prefix + '_')
    code += pointer_guard('rdx', prefix)
    code += '''test dword ptr [rdx], 0x800
je P_done
mov ecx, dword ptr [rdx+0x20]
cmp ecx, 250
jb P_done
cmp ecx, 267
ja P_done
cmp ecx, dword ptr [r8+0xEC]
jne P_done
mov rax, qword ptr [r9+0x510]
mov rdx, qword ptr [r9+0x528]
test rax, rax
je P_exit
test rdx, rdx
je P_exit
'''.replace('P_', prefix + '_')
    code += pointer_guard('rax', prefix) + pointer_guard('rdx', prefix)
    code += '''cmp qword ptr [rdx], rax
jne P_done
cmp word ptr [rax+4], 2
jne P_done
cmp byte ptr [rdx+8], 1
jne P_done
cmp byte ptr [rdx+9], 1
ja P_done
cmp byte ptr [rdx+0xA], 1
ja P_done
cmp dword ptr [rdx+0x4C], 1
jb P_done
cmp dword ptr [rdx+0x4C], 0x1000
ja P_done
cmp dword ptr [rdx+0x50], 1
jb P_done
cmp dword ptr [rdx+0x50], 0x1000
ja P_done
cmp dword ptr [rdx+0x48], 8
je P_replace
cmp dword ptr [rdx+0x48], 9
jne P_done
jmp P_replace
P_exit:
mov rax, qword ptr [r9+0x58]
cmp dword ptr [rax], 61
je P_replace
cmp dword ptr [rax], 62
je P_replace
cmp dword ptr [rax], 66
jne P_done
P_replace:
mov eax, 0x3F800000
'''.replace('P_', prefix + '_')
    code += f'''movd {xmm}, eax
{prefix}_done:
''' + RESTORE
    return code


NATIVE_SIGNATURES = ORIGINAL_SIGNATURES + (
    ('HE_LadderSampleClipCaptureDraft', 0x954684, '4C 63 51 50 49 8B E9', 'rcx', None),
)


SAMPLE_LOCAL_OFFSET = 0x20


SAMPLE_SAVED_OFFSET = 0x60


def candidate_guard(prefix: str, rejected: str, *, pending: bool = False) -> str:
    """Validate selected action RAX against native sampler clip on this stack."""
    code = pointer_guard('rax', prefix)
    if pending:
        code += f'cmp byte ptr [rax+0x40], 1\nja {prefix}_done\n'
    else:
        code += f'cmp byte ptr [rax+0x40], 0\nje {prefix}_done\n'
    code += f'''cmp dword ptr [rax], 56
jb {prefix}_done
cmp dword ptr [rax], 70
ja {prefix}_done
mov rdx, qword ptr [r9+0x80]
test rdx, rdx
je {prefix}_done
cmp rdx, qword ptr [rax+0x38]
jne {prefix}_done
mov rdx, qword ptr [rax+0x20]
'''
    code += pointer_guard('rdx', prefix)
    code += f'''test dword ptr [rdx], 0x800
je {prefix}_done
mov ecx, dword ptr [rdx+0x20]
cmp ecx, dword ptr [rsp+0x60]
jne {prefix}_done
'''
    return code.replace(prefix + '_done', rejected)


def transition_sampler_asm() -> str:
    """Keep native owner guards; replace only the sampler's action-selection gate."""
    prefix = 'ladder_scale_0'
    previous = scale_asm(0)
    begin = 'mov rax, qword ptr [r9+0x58]\n'
    end = 'mov rax, qword ptr [r9+0x510]\n'
    if previous.count(begin) != 2 or previous.count(end) != 1:
        raise ValueError('Immutable sampler source selection boundary changed')
    first = previous.index(begin)
    last = previous.index(end, first)
    gate = f'''cmp dword ptr [r8+0x48], 2
jne {prefix}_done
mov ecx, dword ptr [rsp+0x60]
cmp ecx, 250
jb {prefix}_done
cmp ecx, 267
ja {prefix}_done
xor r10d, r10d
mov rax, qword ptr [r9+0x58]
'''
    gate += candidate_guard(prefix + '_current', prefix + '_pending')
    gate += f'''jmp {prefix}_selected
{prefix}_pending:
mov r10d, 1
mov rax, qword ptr [r9+0x60]
'''
    gate += candidate_guard(prefix + '_pending_guard', prefix + '_done', pending=True)
    gate += f'''{prefix}_selected:
mov r11, rax
'''
    updated = previous[:first] + gate + previous[last:]
    old_exit = f'''{prefix}_exit:
mov rax, qword ptr [r9+0x58]
cmp dword ptr [rax], 61
je {prefix}_replace
cmp dword ptr [rax], 62
je {prefix}_replace
cmp dword ptr [rax], 66
jne {prefix}_done
'''
    new_exit = f'''{prefix}_exit:
test r10d, r10d
jne {prefix}_done
cmp dword ptr [r11], 61
je {prefix}_replace
cmp dword ptr [r11], 62
je {prefix}_replace
cmp dword ptr [r11], 66
jne {prefix}_done
'''
    if updated.count(old_exit) != 1:
        raise ValueError('Immutable sampler exit guard changed')
    return updated.replace(old_exit, new_exit)


def sample_capture_asm() -> str:
    """Replay both native instructions; save R8d without changing any flags."""
    return '''movsxd r10, dword ptr [rcx+0x50]
mov rbp, r9
mov dword ptr [rsp+0x20], r8d
jmp {return}
'''


CODE_OFFSETS = (0x19000, 0x19600, 0x19C00, 0x1A200)


CODE_CAPACITY = 0x600


ALLOCATION_SIZE = 0x1B000


DATA_OFFSET = 0xF000


PROTECTED_DATA_PAGES = ((0xF000, 0x10000), (0x13000, 0x14000))


def apply_ladder_scale(previous_plan: dict) -> dict:
    """Append four revision-2 sampler repairs to the 55-hook Beta 5.1 base."""
    if (len(previous_plan.get('hooks', ())) != 55
            or previous_plan.get('allocation_size') != 0x19000
            or previous_plan.get('data_offset') != DATA_OFFSET
            or previous_plan.get('targets', {}).get('player_slot') != PLAYER_SLOT_RVA):
        raise ValueError('Ladder scale repair requires the complete 55-hook Beta 5.1 layout')
    hooks = previous_plan['hooks']
    names = [hook['name'] for hook in hooks]
    if len(set(names)) != len(names):
        raise ValueError('Duplicate baseline hook name')
    native = sorted((hook['rva'], hook['rva'] + hook['length']) for hook in hooks)
    code = sorted((hook['code_offset'], hook['code_offset']
                   + hook.get('code_capacity', 0x400)) for hook in hooks)
    if (any(left[1] > right[0] for left, right in zip(native, native[1:]))
            or any(left[1] > right[0] for left, right in zip(code, code[1:]))
            or any(start < 0 or end > 0x19000 for start, end in code)
            or any(max(start, protected_start) < min(end, protected_end)
                   for start, end in code for protected_start, protected_end in PROTECTED_DATA_PAGES)):
        raise ValueError('Baseline code, native spans or data pages overlap')
    additions = []
    for index, (name, rva, original, _, _) in enumerate(NATIVE_SIGNATURES):
        length = len(bytes.fromhex(original))
        if any(max(start, rva) < min(end, rva + length) for start, end in native):
            raise ValueError('Ladder scale native span already patched')
        asm = (transition_sampler_asm() if index == 0 else sample_capture_asm()
               if index == 3 else scale_asm(index)).replace('{production_data}', '{data}')
        additions.append(dict(name=name.removesuffix('Draft'), rva=rva,
            original=original, length=length, code_offset=CODE_OFFSETS[index],
            code_capacity=CODE_CAPACITY, asm=asm,
            purpose=('Local Hino-Enma exact-sampled Common ladder unit-scale repair'
                     if index < 3 else 'Native sampler requested-clip local stack capture')))
    plan = deepcopy(previous_plan)
    plan['hooks'].extend(additions)
    plan.update(allocation_size=ALLOCATION_SIZE, tool_version='0.60',
        ladder_unit_scale_revision=2, ladder_unit_scale_register_only=True,
        ladder_unit_scale_native_writes=False, ladder_unit_scale_counters=False,
        ladder_unit_scale_common_actions=list(range(56, 71)),
        ladder_unit_scale_cleared_exit_actions=[61, 62, 66],
        ladder_unit_scale_render_common_layer_only=True,
        ladder_unit_scale_sample_capture_local_offset=0x20,
        ladder_unit_scale_sample_capture_saved_offset=0x60,
        ladder_unit_scale_sampler_common_resource_bank=2,
        ladder_unit_scale_sampler_current_or_pending=True,
        ladder_unit_scale_pending_inactive_allowed=True,
        ladder_unit_scale_gameplay_status='Reported normal up/down, per-step movement and exit height on tested ladders',
        stage='beta51_hotfix1_ladder_transition_gameplay_confirmed')
    return plan

