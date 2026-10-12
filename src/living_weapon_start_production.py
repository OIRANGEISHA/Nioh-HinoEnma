"""Pure integration of the proved native start and automatic resource discovery."""
from copy import deepcopy

import living_weapon_start_views as views
from living_weapon_start_input import apply_input, replace
from living_weapon_start_production_layout import (
    apply_production_layout, validate_production_layout, INPUT_CODE_OFFSET)
import living_weapon_start_bootstrap as bootstrap


def assemble_helper(plan, source, offset):
    from build_profile import assemble
    temporary = deepcopy(plan)
    hook = deepcopy(plan['hooks'][36])
    hook.update(asm=source, code_offset=offset,
                code_capacity=bootstrap.CODE_END-offset)
    temporary['hooks'] = [hook]
    return assemble(temporary, 0x140000000, 0x144000000)[0]['payload']


def apply_native_start(previous):
    plan = apply_input(views.apply_views(deepcopy(previous)), views.READY_OFFSET)
    plan = apply_production_layout(plan)
    plan['targets'].update(bootstrap.targets())
    hook = plan['hooks'][36]
    marker = f'mov rcx, rsi\ncall {{data}} + 0x{views.READY_OFFSET-views.CORE_OFFSET:X}\n'
    call = f'''mov r11, {{data}}
mov rcx, qword ptr [r11+0x10]
mov rdx, rsi
mov r8, r11
mov r9, r11
add r9, 0x{views.DATA_OFFSET-views.CORE_OFFSET:X}
call {{data}} + 0x{bootstrap.CODE_OFFSET-views.CORE_OFFSET:X}
test eax, eax
je living_weapon_done
'''
    hook['asm'] = replace(hook['asm'], marker, call + marker)
    input_bytes = views._assemble_one(plan, hook['asm'], INPUT_CODE_OFFSET)
    helper = bootstrap.bootstrap_source()
    helper_bytes = assemble_helper(plan, helper, bootstrap.CODE_OFFSET)
    gap = bootstrap.CODE_OFFSET - INPUT_CODE_OFFSET - len(input_bytes)
    if gap < 0 or bootstrap.CODE_OFFSET + len(helper_bytes) > bootstrap.CODE_END:
        raise ValueError('Automatic startup discovery exceeds its exact code region')
    hook['asm'] += '\n' + '.byte 0\n' * gap + helper
    hook['purpose'] += '; automatic bounded current-equipment discovery before first9; no compiled heap pointers'
    plan['abyss_assembly_code_intervals'][hook['name']] = [
        [0, len(input_bytes)],
        [bootstrap.CODE_OFFSET-INPUT_CODE_OFFSET,
         bootstrap.CODE_OFFSET-INPUT_CODE_OFFSET+len(helper_bytes)]]
    plan.update(living_weapon_start_bootstrap_revision=1,
        living_weapon_start_bootstrap_code_offset=bootstrap.CODE_OFFSET,
        living_weapon_start_bootstrap_code_size=len(helper_bytes),
        living_weapon_start_input_payload_size=len(input_bytes),
        scene_bound_startup_candidate=False,
        living_weapon_start_automatic_resources=True,
        living_weapon_start_views_gameplay_validated=True,
        living_weapon_start_production_gameplay_validated=False)
    validate_production_layout(plan)
    return plan
