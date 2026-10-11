"""Scene-bound native Orochi finisher, including its three-frame blend path.

Revision2's live read-only evidence showed a real transition to3491 with
blend_frames3. Native6FF652 selects954FD0, whose resource predicate and
lookup are independent of954E90. This adds matching read/flag views only.
"""
from copy import deepcopy

from hinoenma_orochi_trial import SAVE, RESTORE, player_guard, resources_guard
from hinoenma_orochi_candidate_v2 import (
    BIND_SIZE, candidate_plan as second_plan, event_resources_guard, finisher_guard,
)


def blend_scope(prefix):
    return (SAVE+player_guard(prefix)+finisher_guard(prefix)+f'''mov rax, qword ptr [r10+0x38]
cmp rdi, rax
jne {prefix}_original
cmp esi, 1200
jne {prefix}_original
cmp qword ptr [rsp+0xC0], 1
je {prefix}_owned
cmp qword ptr [rsp+0xC0], 5
jne {prefix}_original
{prefix}_owned:
'''+resources_guard(prefix)+event_resources_guard(prefix))


def blend_presence_hook():
    return dict(name='HE_OrochiWeaponBlendPresence',rva=0x9550A6,length=5,
        original='4c3974cf08',code_offset=0x3000,code_capacity=0x800,
        asm=blend_scope('bp')+'''cmp qword ptr [r11+0x40], r14
pushfq
pop rax
mov qword ptr [rsp+0xD0], rax
inc dword ptr [r11+0x138]
'''+RESTORE+'''jmp {return}
bp_original:
'''+RESTORE+'''cmp qword ptr [rdi+rcx*8+8], r14
jmp {return}
''',purpose='Provide the matched nonnull native motion1200 predicate for the real blended finisher without populating motion slots')


def blend_motion_hook():
    return dict(name='HE_OrochiWeaponBlendRead',rva=0x9550EC,length=5,
        original='488b5ccf08',code_offset=0x3800,code_capacity=0x800,
        asm=blend_scope('br')+'''cmp qword ptr [rsp+0xC0], 1
je br_primary
mov rax, qword ptr [r11+0x48]
jmp br_selected
br_primary:
mov rax, qword ptr [r11+0x40]
br_selected:
mov qword ptr [rsp+0x90], rax
inc dword ptr [r11+0x13C]
'''+RESTORE+'''jmp {return}
br_original:
'''+RESTORE+'''mov rbx, qword ptr [rdi+rcx*8+8]
jmp {return}
''',purpose='Supply the matched primary or auxiliary weapon motion1200 resource to the native blended lookup')


def candidate_plan(production,module_base,production_allocation,menu_guard):
    plan=second_plan(production,module_base,production_allocation,menu_guard)
    plan.update(tool_version='orochi-scene-candidate.3',allocation_size=0x5000,
                data_offset=0x4000,uninstalled=True,gameplay_validated=False)
    plan['hooks'].extend((blend_presence_hook(),blend_motion_hook()))
    return deepcopy(plan)
