"""Scoped numerical protection for an active native paired execution.

Finite zero-length lines return the native no-hit value before normalization.
The already-stalled, exactly bound NaN query exits through the native no-hit
epilogue. Actor state, query objects, damage and mission data are not written.
"""
from copy import deepcopy

from hinoenma_orochi_trial import SAVE, RESTORE, player_guard

BIND_SIZE=0x200


def paired_guard(prefix):
    return f'''mov rax, {{execution_data}}
cmp dword ptr [rax], 0x4643524F
jne {prefix}_original
cmp dword ptr [rax+0x74], 1
jne {prefix}_original
cmp qword ptr [rax+8], r10
jne {prefix}_original
mov rax, qword ptr [r11+0x1A8]
cmp qword ptr [r8+0x58], rax
jne {prefix}_original
mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x5B0], r9
jne {prefix}_original
mov rax, qword ptr [r11+0x20]
cmp qword ptr [r9], rax
jne {prefix}_original
mov rax, qword ptr [r9+0x230]
test rax, rax
je {prefix}_original
cmp qword ptr [rax], r9
jne {prefix}_original
mov rax, qword ptr [rax+8]
cmp rax, qword ptr [r11+0xA8]
jne {prefix}_original
cmp qword ptr [rax+0x50], r9
jne {prefix}_original
cmp qword ptr [rax+0x5B0], r10
jne {prefix}_original
mov rdx, qword ptr [r11+0x1F0]
cmp qword ptr [rax+0x58], rdx
jne {prefix}_original
cmp dword ptr [rdx], 4001
jne {prefix}_original
cmp byte ptr [rdx+0x40], 1
jne {prefix}_original
'''


def zero_ray_hook():
    asm=SAVE+player_guard('zr')+paired_guard('zr')+'''mov rax, {actor_ray_return}
cmp qword ptr [rsp+0xD8], rax
jne zr_original
cmp r15, r10
je zr_owner
cmp r15, qword ptr [r11+0x18]
jne zr_original
zr_owner:
mov r8, qword ptr [rsp+0xB0]
mov r9, qword ptr [rsp+0xA8]
'''
    for offset in (0,4,8):
        for reg in ('r8','r9'):
            asm+=f'''mov eax, dword ptr [{reg}+{offset}]
and eax, 0x7F800000
cmp eax, 0x7F800000
je zr_no_hit
'''
    for offset in (0,4,8):
        asm+=f'''movss xmm0, dword ptr [r8+{offset}]
ucomiss xmm0, dword ptr [r9+{offset}]
jne zr_original
'''
    asm+='''zr_no_hit:
inc dword ptr [r11+0x1D0]
mov eax, -1
mov qword ptr [rsp+0xC8], rax
'''+RESTORE+'''ret
zr_original:
'''+RESTORE+'''mov qword ptr [rsp+8], rbx
jmp {return}
'''
    return dict(name='HE_OrochiZeroLengthRay',rva=0x7DCF10,length=5,
                original='48895c2408',code_offset=0,code_capacity=0x1000,asm=asm,
                purpose='Return native no-hit for a zero-length or non-finite line from the bound paired actors, before normalization')


def stalled_ray_hook():
    asm=SAVE+player_guard('sr')+paired_guard('sr')+'''cmp rdi, qword ptr [r11+0x1D8]
jne sr_original
cmp rsi, qword ptr [r11+0x1E0]
jne sr_original
mov rax, {nested_ray_return}
cmp qword ptr [rsp+0x310], rax
jne sr_original
mov rax, qword ptr [rsp+0x2D8]
cmp rax, r10
je sr_owner
cmp rax, qword ptr [r11+0x18]
jne sr_original
sr_owner:
'''
    for offset in (0x20,0x24,0x28,0x30,0x34,0x38):
        asm+=f'''mov eax, dword ptr [rdi+{offset}]
and eax, 0x7F800000
cmp eax, 0x7F800000
je sr_no_hit
'''
    asm+='''jmp sr_original
sr_no_hit:
inc dword ptr [r11+0x1D4]
'''+RESTORE+'''jmp {geometry_no_hit}
sr_original:
'''+RESTORE+'''test r8, r8
jne {geometry_hit}
jmp {return}
'''
    return dict(name='HE_OrochiStalledInvalidRayExit',rva=0x216AC7,length=5,
                original='4d85c07566',code_offset=0x1000,code_capacity=0x1000,asm=asm,
                purpose='Exit the exact captured non-finite query through its native no-hit epilogue without editing the live query or thread registers')


def addon_plan(production,module_base,production_allocation,execution_data):
    plan={key:deepcopy(production[key]) for key in
          ('schema','disk_sha256','image_size','pe_timestamp_hex','product_version')}
    plan.update(tool_version='orochi-paired-ray-guard.1',allocation_size=0x3000,
                data_offset=0x2000,own_data_size=BIND_SIZE,
                hooks=[zero_ray_hook(),stalled_ray_hook()],
                targets=dict(player_slot=production['targets']['player_slot'],
                    production_data=production_allocation+production['data_offset']-module_base,
                    execution_data=execution_data-module_base,actor_ray_return=0x6E86B8,
                    nested_ray_return=0x7DED33,geometry_no_hit=0x216ADD,
                    geometry_hit=0x216B32))
    return plan
