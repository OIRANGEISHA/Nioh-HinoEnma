"""Offline selected Salt injury chain; no process access or distribution.

Extends frozen57 only within the existing Salt token: exact224->147->205,
and exact owned147/205/85/96 injury re-evaluation through224. Common151's
three exact front selectors use Common85/m30002. Native input, queries,
damage, Ki, requests and completion remain untouched. Qualification never
arms or clears the token. These CPU-only rules do not prove gameplay.
"""
from copy import deepcopy
import struct

import hinoenma_salt_damage96_draft as previous
import hinoenma_salt_hurt_compatibility as frozen

CHANGED_HOOK_INDICES = (0, 34, 39)
EXPECTED_MOTION_OFFSET, EXPECTED_MOTION_CAPACITY = 0x80, 0x80
RESOURCE_HELPER_OFFSET, RESOURCE_HELPER_CAPACITY = 0x100, 0x120
SIGNATURE_OFFSET, SIGNATURE_CAPACITY = 0x220, 0x130
ROUTES_OFFSET, ROUTES_CAPACITY = 0x350, 0xB0
SELECTED_INDEX_OFFSET, SELECTED_INDEX_CAPACITY = 0xEEF4, 0x10C

# target, source, selected index, second query, exact source first/count.
# Shared q52 descriptors must be paired with the current owned source ID
# when evaluating224, rather than guessed from descriptor-pointer identity.
ROUTES = (
    (224, 982, 5170, 0xFFFF, 5166, 21),
    (224, 147, 2552, 0xFFFF, 2546, 9),
    (224, 205, 4540, 0xFFFF, 4530, 13),
    (224, 85, 1715, 0xFFFF, 1704, 14),
    (224, 96, 1869, 0xFFFF, 1858, 14),
    (147, 224, 7892, 43, 7870, 73),
    (205, 147, 2548, 0xFFFF, 2546, 9),
    (85, 151, 2599, 63, 2587, 28),
    (85, 151, 2600, 62, 2587, 28),
    (85, 151, 2601, 61, 2587, 28),
    (152, 224, 7921, 332, 7870, 73),
    (152, 224, 7932, 73, 7870, 73),
    (152, 224, 7933, 29, 7870, 73),
    (96, 152, 2634, 60, 2615, 32),
)
ROUTE_BYTES = b''.join(struct.pack('<6H', *row) for row in ROUTES)

EXPECTED_MOTION_ASM = '''salt58_expected_motion:
cmp ecx, 85
je salt58_motion85
cmp ecx, 96
je salt58_motion96
cmp ecx, 205
je salt58_motion205
mov eax, ecx
sub eax, 106
cmp eax, 3
ja salt58_motion_invalid
shr eax, 1
imul eax, eax, 6
add eax, 30102
ret
salt58_motion85:
mov eax, 30002
ret
salt58_motion96:
mov eax, 30014
ret
salt58_motion205:
mov eax, 30310
ret
salt58_motion_invalid:
mov eax, -2
ret
'''

SELECTED_INDEX_ASM = '''salt58_selected_index:
mov r10, qword ptr [r14+0x50]
test r10, r10
je salt58_index_invalid
movzx ecx, word ptr [r14+0x5A]
cmp cx, word ptr [r14+0x58]
ja salt58_index_invalid
mov r9, qword ptr [r13+0x90]
test r9, r9
je salt58_index_invalid
mov r11, {data}
sub r11, 0xECB0
mov r8d, 14
salt58_index_loop:
cmp word ptr [r11], bx
jne salt58_index_next
cmp ebx, 224
jne salt58_index_candidate
mov rax, qword ptr [r13+0x58]
mov eax, dword ptr [rax]
cmp ax, word ptr [r11+2]
jne salt58_index_next
salt58_index_candidate:
movzx eax, word ptr [r11+4]
cmp eax, ecx
jae salt58_index_invalid
cmp qword ptr [r10+rax*8], r9
jne salt58_index_next
movzx edx, word ptr [r11+2]
ret
salt58_index_next:
add r11, 12
dec r8d
jne salt58_index_loop
salt58_index_invalid:
mov eax, -1
ret
'''

SIGNATURE_ASM = '''salt58_selected_signature:
mov r11, qword ptr [rsp+0x88]
mov ecx, dword ptr [r11+8]
cmp dword ptr [rax+0x80], ecx
jne salt58_signature_invalid
mov r8, qword ptr [rax+0x20]
test r8, r8
je salt58_signature_invalid
movzx ecx, word ptr [r11+2]
call {data} - 0xEF80
cmp ecx, 982
jne salt58_signature_not_salt
mov eax, 120
salt58_signature_not_salt:
cmp eax, -2
jne salt58_signature_source_motion
mov eax, -1
salt58_signature_source_motion:
cmp dword ptr [r8+0x20], eax
jne salt58_signature_invalid
movzx eax, word ptr [r11+6]
shl rax, 16
mov ax, 52
cmp ebx, 205
jne salt58_signature_queries
mov ax, 0xFFFF
salt58_signature_queries:
mov r10, 0xFFFFFFFF00000000
or rax, r10
cmp qword ptr [r9], rax
jne salt58_signature_invalid
mov r10, 0x00FFFFFFFF00FFFF
cmp qword ptr [r9+8], r10
jne salt58_signature_invalid
mov eax, ebx
shl rax, 32
cmp qword ptr [r9+16], rax
jne salt58_signature_invalid
mov r10, 0x00200040646480FF
cmp ebx, 205
jne salt58_signature_tail
mov r10, 0x00000000646480FF
salt58_signature_tail:
cmp qword ptr [r9+24], r10
jne salt58_signature_invalid
mov r10, 0xFFFFFFFF7FFF8000
cmp qword ptr [r9+32], r10
jne salt58_signature_invalid
cmp qword ptr [r9+40], -1
jne salt58_signature_invalid
mov eax, 1
ret
salt58_signature_invalid:
xor eax, eax
ret
'''


def main_helper_asm():
    source = previous._without_islands(previous.main_helper_asm())
    source = previous._once(source, '''cmp eax, 152
je salt_hurt_current_motionless
''', '''cmp eax, 152
je salt_hurt_current_motionless
cmp eax, 147
je salt_hurt_current_motionless
''')
    source = source.replace('call {data} - 0x10C', 'call {data} - 0xEF80')
    start = source.index('salt_hurt_dispatch:\n')
    end = source.index('salt_hurt_records:\n', start)
    source = source[:start]+'''salt_hurt_dispatch:
cmp ebx, 224
jne salt58_dispatch_active
test byte ptr [r13+0x40], 2
je salt_hurt_clear
cmp dword ptr [r13+0x2C8], 48
ja salt_hurt_clear
jmp salt58_dispatch
salt58_dispatch_active:
cmp dword ptr [r15], 1
jne salt_hurt_clear
cmp ebx, 152
je salt58_dispatch
cmp ebx, 96
je salt58_dispatch
cmp ebx, 147
je salt58_dispatch
cmp ebx, 205
je salt58_dispatch
cmp ebx, 85
jne salt58_dispatch_rear
salt58_dispatch:
call {data} - 0x10C
test eax, eax
js salt_hurt_clear
mov dword ptr [rsp+0xA8], eax
mov dword ptr [rsp+0xAC], edx
mov qword ptr [rsp+0x80], r11
jmp salt_hurt_records
salt58_dispatch_rear:
mov dword ptr [rsp+0xA8], 7935
mov dword ptr [rsp+0xAC], 224
cmp ebx, 151
je salt_hurt_records
mov dword ptr [rsp+0xA8], 2593
mov dword ptr [rsp+0xAC], 151
mov eax, ebx
sub eax, 106
cmp eax, 3
ja salt_hurt_clear
mov rax, qword ptr [rsp+0x88]
mov eax, dword ptr [rax]
sub eax, 106
cmp eax, 3
ja salt_hurt_records
add eax, 106
mov dword ptr [rsp+0xAC], eax
mov dword ptr [rsp+0xA8], -1
'''+source[end:]
    start = source.index('salt_hurt_parameters:\n')
    end = source.index('mov rax, qword ptr [rsp+0x98]\n', start)
    source = source[:start]+'''salt_hurt_parameters:
cmp ebx, 151
je salt58_parameters_rear
mov eax, ebx
sub eax, 106
cmp eax, 3
jbe salt58_parameters_rear
mov rax, qword ptr [rsp+0xA0]
call {data} - 0xEDE0
test eax, eax
je salt_hurt_clear
salt58_parameters_rear:
'''+source[end:]
    source = previous._once(source, '''cmp ebx, 152
je salt_hurt_motionless
''', '''cmp ebx, 152
je salt_hurt_motionless
cmp ebx, 147
je salt_hurt_motionless
''')
    source = previous._once(source, '''mov edx, 30102
mov r8d, 30108
cmp ebx, 96
jne salt96_resources
mov edx, 30014
mov r8d, 30014
salt96_resources:
''', '''mov ecx, ebx
call {data} - 0xEF80
mov edx, eax
mov r8d, eax
cmp ebx, 106
jb salt58_resources
cmp ebx, 109
ja salt58_resources
mov edx, 30102
mov r8d, 30108
salt58_resources:
''')
    # Expected-motion lookup uses EAX only. Restore the already checked model
    # component in RCX before the shared exact slots2/6 resource helper call.
    source = previous._once(source, '''salt58_resources:
call {data} - 0xEF00
''', '''salt58_resources:
mov rcx, qword ptr [r12+0x38]
call {data} - 0xEF00
''')
    return frozen._short_failure_islands(source)


def _append_at(prefix_asm, extra_asm, offset, plan, base, allocation, carrier):
    raw = previous._assemble(prefix_asm, plan, base, allocation, carrier)
    if carrier+len(raw)>offset:
        raise ValueError('Salt58 spare carrier boundary exceeded')
    return prefix_asm+'\n'+'nop\n'*(offset-carrier-len(raw))+extra_asm


def apply_salt_damage205_draft(frozen57):
    if (frozen57.get('tool_version')!='0.57-experimental'
            or not frozen57.get('salt_damage96_draft')
            or len(frozen57.get('hooks',()))!=50
            or (frozen57.get('allocation_size'),frozen57.get('data_offset'))!=(0x14000,0xF000)):
        raise ValueError('Complete frozen57 Salt96 profile required')
    plan=deepcopy(frozen57)
    preload,main,lookup=(plan['hooks'][i]for i in CHANGED_HOOK_INDICES)
    if (not preload['asm'].endswith(previous.selected_signature_asm())
            or not main['asm'].endswith(previous.main_helper_asm())
            or not lookup['asm'].endswith(previous.SELECTED_INDEX_ASM)):
        raise ValueError('Frozen57 Salt96 carrier suffix differs')
    base,allocation=0x140000000,0x144000000
    prefix=preload['asm'].split('\nsalt_front_resources:',1)[0]
    old=previous._assemble(prefix,plan,base,allocation,0)
    if len(old)!=0x100 or old[0x80:]!=b'\x90'*0x80:
        raise ValueError('Frozen57 exact preload prefix differs')
    # Keep the original callable prefix and use its previously unused tail.
    prefix=prefix[:-len('nop\n')*0x80]
    preload['asm']=_append_at(prefix,EXPECTED_MOTION_ASM,EXPECTED_MOTION_OFFSET,plan,base,allocation,0)
    preload['asm']=_append_at(preload['asm'],previous.RESOURCE_HELPER_ASM,RESOURCE_HELPER_OFFSET,plan,base,allocation,0)
    preload['asm']=_append_at(preload['asm'],SIGNATURE_ASM,SIGNATURE_OFFSET,plan,base,allocation,0)
    rows='.byte '+','.join(str(b)for b in ROUTE_BYTES)+'\n'
    preload['asm']=_append_at(preload['asm'],rows,ROUTES_OFFSET,plan,base,allocation,0)
    main['asm']=main['asm'][:-len(previous.main_helper_asm())]+main_helper_asm()
    lookup['asm']=lookup['asm'].split('\nsalt96_expected_motion:',1)[0]+ '\n'+SELECTED_INDEX_ASM
    for i in CHANGED_HOOK_INDICES:
        h=plan['hooks'][i]
        raw=previous._assemble(h['asm'],plan,base,allocation,h['code_offset'])
        if not 0<len(raw)<=h.get('code_capacity',0x400):
            raise ValueError('Salt58 exceeds fixed carrier: '+h['name'])
    for asm,offset,capacity in ((EXPECTED_MOTION_ASM,EXPECTED_MOTION_OFFSET,EXPECTED_MOTION_CAPACITY),
            (previous.RESOURCE_HELPER_ASM,RESOURCE_HELPER_OFFSET,RESOURCE_HELPER_CAPACITY),
            (SIGNATURE_ASM,SIGNATURE_OFFSET,SIGNATURE_CAPACITY),
            (SELECTED_INDEX_ASM,SELECTED_INDEX_OFFSET,SELECTED_INDEX_CAPACITY)):
        if len(previous._assemble(asm,plan,base,allocation,offset))>capacity:
            raise ValueError('Salt58 helper exceeds fixed spare interval')
    if len(ROUTE_BYTES)>ROUTES_CAPACITY:
        raise ValueError('Salt58 route table exceeds spare interval')
    plan.update(tool_version='0.58-experimental',stage='offline_salt_actual147_205_front85_draft',
        salt_damage205_draft=True,salt_damage205_gameplay_verified=False,
        salt_damage205_changed_hook_indices=list(CHANGED_HOOK_INDICES),
        salt_damage205_selected_routes=[list(r)for r in ROUTES],
        salt_damage205_common_motion_ids=[30002,30310],
        salt_damage205_active_repeat_sources=[147,205,85,96],
        distribution_ready=False)
    return plan
