"""Uninstalled revision: include native weapon event tables and motion presence.

The failed trial skipped the native NULL-slot check before its motion hook,
and omitted the independent TMG_PACK lookup. This revision supplies both as
scoped register/flag views. It does not populate any actor or shared slots.
"""
from copy import deepcopy

from hinoenma_orochi_trial import (
    SAVE, RESTORE, player_guard, resources_guard, trial_plan as failed_plan,
)

BIND_SIZE = 0x200


def event_resources_guard(prefix):
    source = ''
    for package_offset, wrapper_offset, owner_offset, bank_offset, map_offset, capacity_offset in (
            (0x198,0xB8,0xC8,0xD8,0xE8,0x108),
            (0x1A0,0xC0,0xD0,0xE0,0xF0,0x10C)):
        source += f'''mov rax, qword ptr [r11+0x28]
mov r9, qword ptr [r11+{wrapper_offset:#x}]
cmp qword ptr [rax+{package_offset:#x}], r9
jne {prefix}_original
mov rax, {{weapon_event_vtable}}
cmp qword ptr [r9], rax
jne {prefix}_original
mov rax, qword ptr [r11+{owner_offset:#x}]
cmp qword ptr [r9+0x468], rax
jne {prefix}_original
mov r9, qword ptr [r11+{bank_offset:#x}]
cmp qword ptr [rax], r9
jne {prefix}_original
mov rdx, 0x4B4341505F474D54
cmp qword ptr [r9], rdx
jne {prefix}_original
mov r9, qword ptr [r11+{map_offset:#x}]
cmp qword ptr [rax+8], r9
jne {prefix}_original
mov edx, dword ptr [r11+{capacity_offset:#x}]
test edx, edx
je {prefix}_original
cmp edx, 0x10000
ja {prefix}_original
cmp dword ptr [r9+8], edx
jne {prefix}_original
cmp qword ptr [r9+0x10], 0
je {prefix}_original
'''
    return source


def finisher_guard(prefix):
    return f'''cmp dword ptr [r11+0x74], 1
jne {prefix}_original
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
je {prefix}_record_ready
cmp qword ptr [r8+0x60], rax
jne {prefix}_original
{prefix}_record_ready:
'''


def presence_hook():
    return dict(name='HE_OrochiWeaponMotionPresence',rva=0x954EBC,length=6,
        original='4a837cc90800',code_offset=0x2000,code_capacity=0x800,
        asm=SAVE+player_guard('op')+finisher_guard('op')+'''mov rax, qword ptr [r10+0x38]
cmp qword ptr [rsp+0xC0], rax
jne op_original
cmp dword ptr [rsp+0xB8], 1200
jne op_original
cmp qword ptr [rsp+0xA8], 1
je op_owned
cmp qword ptr [rsp+0xA8], 5
jne op_original
op_owned:
'''+resources_guard('op')+event_resources_guard('op')+'''cmp qword ptr [r11+0x40], 0
pushfq
pop rax
mov qword ptr [rsp+0xD0], rax
inc dword ptr [r11+0x110]
'''+RESTORE+'''jmp {return}
op_original:
'''+RESTORE+'''cmp qword ptr [rcx+r9*8+8], 0
jmp {return}
''',purpose='Preserve the native nonzero resource predicate for verified finisher1200 banks1/5 without changing actor motion slots')


def event_hook():
    return dict(name='HE_OrochiWeaponEventRead',rva=0x968B77,length=5,
        original='498b4cce10',code_offset=0x2800,code_capacity=0x800,
        asm=SAVE+player_guard('oe')+finisher_guard('oe')+'''cmp r14, qword ptr [r11+0xB0]
jne oe_original
cmp qword ptr [r14+8], r10
jne oe_original
cmp dword ptr [rsp+0xB8], 1200
jne oe_original
cmp qword ptr [rsp+0xC0], 1
je oe_primary
cmp qword ptr [rsp+0xC0], 4
jne oe_original
'''+resources_guard('oe')+event_resources_guard('oe')+'''mov rax, qword ptr [r11+0xD0]
jmp oe_selected
oe_primary:
'''+resources_guard('oe')+event_resources_guard('oe')+'''mov rax, qword ptr [r11+0xC8]
oe_selected:
mov qword ptr [rsp+0xC0], rax
inc dword ptr [r11+0x114]
'''+RESTORE+'''jmp {return}
oe_original:
'''+RESTORE+'''mov rcx, qword ptr [r14+rcx*8+0x10]
jmp {return}
''',purpose='Supply the matched owned TMG_PACK owner for native motion-event1200 bank1/4 lookups, preserving the native event schedule')


def candidate_plan(production,module_base,production_allocation,menu_guard):
    plan=failed_plan(production,module_base,production_allocation,menu_guard)
    plan.update(tool_version='orochi-scene-candidate.2',uninstalled=True,
                gameplay_validated=False,own_data_size=BIND_SIZE)
    plan['targets']['weapon_event_vtable']=0x12C5408
    plan['targets']['mission_temp_owner']=0x189F408
    # Every resource view now requires both native event owners as well as the
    # matching motion owners. The old CPU proof remains archived separately.
    for hook,prefix in zip(plan['hooks'],('oh','ob','om')):
        marker=resources_guard(prefix)
        hook['asm']=hook['asm'].replace(marker,marker+event_resources_guard(prefix))
    heavy=plan['hooks'][0]
    heavy['asm']=heavy['asm'].replace('cmp dword ptr [rax], 3205',
        'mov edx, dword ptr [r11+0x118]\ncmp dword ptr [rax], edx')
    marker=resources_guard('oh')
    last_head='''mov rax, {mission_temp_owner}
mov rax, qword ptr [rax]
cmp rax, qword ptr [r11+0x130]
jne oh_original
mov rax, qword ptr [r11+0x120]
cmp byte ptr [rax], 7
jne oh_original
cmp dword ptr [rax+4], 1
jne oh_original
mov r9, qword ptr [r11+0x18]
mov rax, qword ptr [r11+0x128]
cmp qword ptr [r9+0x240], rax
jne oh_original
cmp qword ptr [rax], r9
jne oh_original
cmp qword ptr [rax+0x20], 1
jne oh_original
'''
    heavy['asm']=heavy['asm'].replace(marker,last_head+marker)
    motion=plan['hooks'][2]
    motion['asm']=motion['asm'].replace('test rcx, rcx\nje om_primary\ncmp rcx, 4',
                                      'cmp rcx, 1\nje om_primary\ncmp rcx, 5')
    plan['hooks'].extend((presence_hook(),event_hook()))
    return deepcopy(plan)
