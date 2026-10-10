"""Private revision3: retain Hino preview through both native initial refreshes.

The frozen revision2 behavior is reused unchanged except the state0 gear
binder ancestry. BaseMode refreshes stats directly and then refreshes the
changed native parameter through 7B4BE0. Only that second exact nested
call, 7B4C10 inside the map call returning 8C54A3, gains suppression.
"""
from __future__ import annotations

import menu_preview_appearance_rev2_hooks as frozen

ALLOCATION_SIZE, DATA_OFFSET = frozen.ALLOCATION_SIZE, frozen.DATA_OFFSET
HOOK_RVA, ORIGINAL = frozen.HOOK_RVA, frozen.ORIGINAL
IDLE_RVA, IDLE_ORIGINAL = frozen.IDLE_RVA, frozen.IDLE_ORIGINAL
IDLE_SELECT_RVA, IDLE_SELECT_ORIGINAL = frozen.IDLE_SELECT_RVA, frozen.IDLE_SELECT_ORIGINAL
LOADOUT_RVA, LOADOUT_ORIGINAL = frozen.LOADOUT_RVA, frozen.LOADOUT_ORIGINAL
HOOKS = frozen.HOOKS
TARGET_RVAS = dict(frozen.TARGET_RVAS,
    initial_parameter_return=0x7B4C10, initial_parameter_map_return=0x8C54A3)
ADDITIONAL_NATIVE_SPANS = ((0x7B4BE0, 0x37), (0x8C5493, 0x56),
                           (0x7C7EB0, 0x67), (0x7B1518, 0x19B))
NATIVE_SPANS = frozen.NATIVE_SPANS + ADDITIONAL_NATIVE_SPANS


def appearance_asm():
    source = frozen.appearance_asm()
    for suffix in ('', '_recheck'):
        ready = 'appearance_owner_recheck' if suffix else 'appearance_owner_ready'
        old = f'''appearance_initial{suffix}:
mov rcx, {{initial_stats_return}}
cmp qword ptr [rsp+0x228], rcx
jne appearance_done
{ready}:
'''
        new = f'''appearance_initial{suffix}:
mov rcx, {{initial_stats_return}}
cmp qword ptr [rsp+0x228], rcx
je {ready}
mov rcx, {{initial_parameter_return}}
cmp qword ptr [rsp+0x228], rcx
jne appearance_done
mov rcx, {{initial_parameter_map_return}}
cmp qword ptr [rsp+0x258], rcx
jne appearance_done
{ready}:
'''
        if source.count(old) != 1:
            raise ValueError('Frozen gear initial ancestry boundary changed')
        source = source.replace(old, new)
    return source


def build_plan(base: int, production_data: int, visual_data: int, allocation: int) -> dict:
    plan = frozen.build_plan(base, production_data, visual_data, allocation)
    plan['tool_version'] = 'menu-appearance-private-3'
    plan['targets'] = dict(plan['targets'], **TARGET_RVAS)
    plan['hooks'][0]['asm'] = appearance_asm()
    plan['hooks'][0]['purpose'] = 'Suppress both exactly scoped native initial map gear refreshes'
    plan['native_initial_parameter_update_preserved'] = True
    plan['initial_parameter_scope'] = dict(inner_return=0x7B4C10,
        outer_return=0x8C54A3, native_stack_offsets=[0x148, 0x178],
        saved_stack_offsets=[0x228, 0x258], owner_state=0)
    return plan


def native_signatures(code=None):
    if code is None:
        from code_inspect import CodeImage
        code = CodeImage()
    signatures = frozen.native_signatures(code)
    fixed = ((0x7B4BE0, '48 83 EC 28'),
        (0x7B4C0B, 'E8 A0 32 01 00 B0 01 48 83 C4 28 C3'),
        (0x8C5493, '48 8B 8B 40 02 00 00 48 83 C1 10 E8 3D F7 EE FF'))
    for rva, expected in fixed:
        at, expected = code.file_offset(rva), bytes.fromhex(expected)
        if bytes(code.data[at:at+len(expected)]) != expected:
            raise ValueError(f'Native initial parameter signature differs at {rva:X}')
    for rva, length in ADDITIONAL_NATIVE_SPANS:
        at = code.file_offset(rva)
        signatures.append(dict(rva=rva, length=length,
            original=bytes(code.data[at:at+length]).hex()))
    return signatures
