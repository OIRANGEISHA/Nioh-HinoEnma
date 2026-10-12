"""Pure scene-candidate changes for native Living Weapon startup input.

The first digit9 queues action169 and flushes its native first-frame schedule
once at the late input hook. The event owns initialization and the startup
child. This module never opens a process.
"""
from copy import deepcopy
from living_weapon_start_views import _ptr

BIND_DELTA=0x44200-0xF000
MAGIC=0x534C5748


def replace(source,before,after):
    if source.count(before)!=1:
        raise ValueError('Frozen input boundary changed')
    return source.replace(before,after,1)


def owned_modes(prefix,bad):
    return f'''cmp dword ptr [r11+0xE50], 1
je {prefix}_owned
cmp dword ptr [r11+0xE50], 2
jne {bad}
{prefix}_owned:
'''


def current_pending(bad):
    return f'''mov rax, {{data}}
add rax, 0x{BIND_DELTA:X}
cmp dword ptr [rax], 0x{MAGIC:X}
jne {bad}
cmp dword ptr [rax+0x18], 1
jne {bad}
mov ecx, dword ptr [r11+0x1C]
cmp ecx, dword ptr [rax+4]
jne {bad}
cmp r10, qword ptr [rax+8]
jne {bad}
cmp rsi, qword ptr [rax+0x10]
jne {bad}
mov rcx, qword ptr [rsi+0x58]
cmp rcx, qword ptr [rax+0x60]
je lw_pending_valid
cmp rcx, qword ptr [rax+0x68]
je lw_pending_valid
cmp rcx, qword ptr [rax+0x70]
jne {bad}
lw_pending_valid:
'''


def empty_scheduler(bad):
    # 7188F0 also advances secondary/running/queued events. Only the native
    # empty containers may be present before the late first-frame flush.
    return f'''cmp qword ptr [rsi+0xB0], 0
jne {bad}
mov rax, qword ptr [rsi+0x490]
'''+_ptr('rax',bad,scratch='rcx')+f'''cmp qword ptr [rax], 0
jne {bad}
mov rax, qword ptr [rsi+0x498]
'''+_ptr('rax',bad,scratch='rcx')+f'''cmp qword ptr [rax], rax
jne {bad}
cmp qword ptr [rax+8], rax
jne {bad}
cmp qword ptr [rsi+0x4A0], 0
jne {bad}
'''


def apply_input(previous,ready_code_offset):
    plan=deepcopy(previous)
    if len(plan['hooks'])!=82 or plan['data_offset']!=0xF000:
        raise ValueError('Exact supported82-hook layout required')
    plan['targets']['native_living_weapon_schedule']=0x7188F0
    h=plan['hooks'][36]
    if h['name']!='HE_LivingWeaponDigitNine':
        raise ValueError('Unexpected digit9 hook')
    h['asm']=replace(h['asm'],'''cmp dword ptr [rdx+0xB0], 1
je living_weapon_keep_active
mov dword ptr [r11+0xE50], 0
living_weapon_keep_active:
''',f'''cmp dword ptr [rdx+0xB0], 1
jne lw_update_inactive
cmp dword ptr [r11+0xE50], 2
jne living_weapon_keep_active
mov dword ptr [r11+0xE50], 1
inc dword ptr [r11+0xE48]
jmp living_weapon_keep_active
lw_update_inactive:
cmp dword ptr [r11+0xE50], 2
jne lw_pending_clear
{current_pending('lw_pending_clear')}
jmp living_weapon_keep_active
lw_pending_clear:
mov dword ptr [r11+0xE50], 0
mov rax, {{data}}
add rax, 0x{BIND_DELTA:X}
mov dword ptr [rax+0x18], 0
living_weapon_keep_active:
mov rdx, qword ptr [r10+0x240]
''')
    old='''mov dword ptr [r11+0xE50], 1
mov dword ptr [r11+0xE5C], 1
lea rcx, [rdx+0xB0]
call {native_living_weapon_start}
mov r11, {data}
mov dword ptr [r11+0xE5C], 0
mov rax, qword ptr [rsi+0x50]
mov rax, qword ptr [rax+0x240]
cmp dword ptr [rax+0xB0], 1
jne living_weapon_failed
inc dword ptr [r11+0xE48]
mov rcx, qword ptr [rsi+0x50]
call living_weapon_guardian_start
jmp living_weapon_done
'''
    h['asm']=replace(h['asm'],old,f'''mov rcx, rsi
call {{data}} + 0x{ready_code_offset-0xF000:X}
test eax, eax
je living_weapon_done
mov eax, dword ptr [rsi+0x24]
test eax, eax
jle living_weapon_done
cmp eax, 0x7F800000
jae living_weapon_done
{empty_scheduler('living_weapon_done')}
mov r11, {{data}}
mov dword ptr [r11+0xE50], 2
mov rax, {{data}}
add rax, 0x{BIND_DELTA:X}
mov dword ptr [rax+0x18], 1
mov rcx, rsi
mov edx, 169
xor r8d, r8d
xor r9d, r9d
call {{native_ladder_set_action}}
mov r11, {{data}}
mov r10, qword ptr [r11+0x10]
mov rdx, qword ptr [r10+0x240]
cmp dword ptr [rdx+0xB0], 1
je lw_queued_active
mov rax, {{data}}
add rax, 0x{BIND_DELTA:X}
mov rcx, qword ptr [rsi+0x58]
cmp rcx, qword ptr [rax+0x68]
je lw_flush_first_frame
cmp rcx, qword ptr [rax+0x70]
jne lw_queued_pending
lw_flush_first_frame:
cmp dword ptr [rsi+0x28], 0
jne lw_queued_pending
mov rcx, rsi
call {{native_living_weapon_schedule}}
mov r11, {{data}}
mov r10, qword ptr [r11+0x10]
mov rdx, qword ptr [r10+0x240]
cmp dword ptr [rdx+0xB0], 1
jne lw_queued_pending
lw_queued_active:
mov dword ptr [r11+0xE50], 1
inc dword ptr [r11+0xE48]
jmp living_weapon_done
lw_queued_pending:
{current_pending('lw_queue_failed')}
jmp living_weapon_done
lw_queue_failed:
mov dword ptr [r11+0xE50], 0
mov dword ptr [rax+0x18], 0
jmp living_weapon_done
'''.replace('lw_pending_valid:', 'lw_queue_valid:').replace('je lw_pending_valid','je lw_queue_valid'))
    h['purpose']+='; first9 uses validated native169 startup and one native7188F0 first-frame schedule after late epilogue input; preserve legacy active9 summon; private pending2 promotes once on native state1'
    visual=plan['hooks'][37]
    visual['asm']=replace(visual['asm'],'''cmp dword ptr [r11+0xE50], 1
jne living_weapon_visual_original
''',owned_modes('lw_visual','living_weapon_visual_original'))
    visual['purpose']+='; owned pending2 also protects a scheduled native initializer before input callback promotion'
    factory=plan['hooks'][38]
    code=factory['asm']
    # Preserve RCX because the extra exact-record check uses it.
    code=replace(code,'push rax\npush r10\npush r11\n','push rax\npush rcx\npush r10\npush r11\n')
    code=code.replace('pop r10\npop rax\npopfq\n','pop r10\npop rcx\npop rax\npopfq\n')
    marker='''cmp dword ptr [r11+0xE5C], 1
jne living_weapon_element_original
'''
    code=replace(code,marker,f'''cmp dword ptr [r11+0xE5C], 1
je lw_factory_sync
mov rax, {{data}}
add rax, 0x{BIND_DELTA:X}
cmp dword ptr [rax], 0x{MAGIC:X}
jne living_weapon_element_original
cmp dword ptr [rax+0x18], 1
jne living_weapon_element_original
mov ecx, dword ptr [r11+0x1C]
cmp ecx, dword ptr [rax+4]
jne living_weapon_element_original
mov rcx, qword ptr [r11+0x10]
cmp rcx, qword ptr [rax+8]
jne living_weapon_element_original
mov rcx, qword ptr [rcx+0x230]
test rcx, rcx
je living_weapon_element_original
mov rcx, qword ptr [rcx+8]
cmp rcx, qword ptr [rax+0x10]
jne living_weapon_element_original
mov rcx, qword ptr [rcx+0x58]
cmp rcx, qword ptr [rax+0x60]
je lw_factory_sync
cmp rcx, qword ptr [rax+0x68]
je lw_factory_sync
cmp rcx, qword ptr [rax+0x70]
jne living_weapon_element_original
lw_factory_sync:
''')
    code=replace(code,'''cmp dword ptr [r11+0xE50], 1
jne living_weapon_element_original
''',owned_modes('lw_factory','living_weapon_element_original'))
    factory['asm']=code
    factory['purpose']+='; exact scheduled startup record/epoch protects native kind60 at7B5BA7 without a broad sync latch or charge check'
    plan.update(living_weapon_start_trial_revision=4,living_weapon_start_binding_data_offset=0x44200,
        living_weapon_start_binding_data_size=0x200,scene_bound_startup_candidate=True)
    return plan
