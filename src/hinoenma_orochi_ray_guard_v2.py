"""Keep the numerical guard active through the native post-kill finish.

After event10019 the engine clears both pairing references. The same owned
4000/4001 actors remain covered only while head HP is zero and the native
initialized death counter is exactly eight. No actor or mission data is written.
"""
from hinoenma_orochi_ray_guard import BIND_SIZE, addon_plan as parent_plan
from hinoenma_orochi_ray_guard import paired_guard as parent_guard


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
mov rdx, qword ptr [r11+0x1F0]
cmp qword ptr [rax+0x58], rdx
jne {prefix}_original
cmp dword ptr [rdx], 4001
jne {prefix}_original
cmp byte ptr [rdx+0x40], 1
jne {prefix}_original
cmp qword ptr [r8+0x5B0], r9
je {prefix}_live_pair
cmp qword ptr [r8+0x5B0], 0
jne {prefix}_original
cmp qword ptr [rax+0x5B0], 0
jne {prefix}_original
mov rdx, qword ptr [r11+0x128]
cmp qword ptr [r9+0x240], rdx
jne {prefix}_original
cmp qword ptr [rdx], r9
jne {prefix}_original
cmp qword ptr [rdx+0x20], 0
jne {prefix}_original
mov rdx, {{mission_temp_owner}}
mov rdx, qword ptr [rdx]
cmp rdx, qword ptr [r11+0x130]
jne {prefix}_original
lea rdx, [rdx+0x158184]
cmp rdx, qword ptr [r11+0x120]
jne {prefix}_original
cmp byte ptr [rdx], 8
jne {prefix}_original
cmp dword ptr [rdx+4], 1
jne {prefix}_original
jmp {prefix}_pair_ready
{prefix}_live_pair:
cmp qword ptr [rax+0x5B0], r10
jne {prefix}_original
{prefix}_pair_ready:
'''


def addon_plan(production, module_base, production_allocation, execution_data):
    plan = parent_plan(production, module_base, production_allocation, execution_data)
    for hook, prefix in zip(plan['hooks'], ('zr', 'sr')):
        before = parent_guard(prefix)
        if hook['asm'].count(before) != 1:
            raise ValueError('Frozen numerical guard fragment changed')
        hook['asm'] = hook['asm'].replace(before, paired_guard(prefix), 1)
    plan['targets']['mission_temp_owner'] = 0x189F408
    plan['tool_version'] = 'orochi-paired-ray-guard.2'
    return plan
