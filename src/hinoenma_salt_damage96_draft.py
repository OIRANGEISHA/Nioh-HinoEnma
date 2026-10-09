"""Offline owned Salt -> Common224 -> Common152 -> Common96 candidate.

No producer, profile, proof, installer, process access or game validation.
The frozen rear rules, token lifetime, ABI and native damage/query/requests
remain intact. Only three exact selected Common224 entries may choose152;
only owned Common152 entry2634 with its full48-byte signature may choose96.
Both actual loaded slots2/6 must contain the exact Common30014 clip.
"""
from copy import deepcopy
import re

import hinoenma_salt_hurt_compatibility as frozen


RESOURCE_HELPER_ASM = '''salt_front_resources:
sub rsp, 0x48
mov qword ptr [rsp+0x20], rcx
mov dword ptr [rsp+0x3C], edx
mov dword ptr [rsp+0x38], r8d
mov dword ptr [rsp+0x28], 2
salt_front_resource_slot:
mov rax, qword ptr [rsp+0x20]
mov ecx, dword ptr [rsp+0x28]
mov rax, qword ptr [rax+rcx*8+8]
test rax, rax
je salt_front_resource_invalid
mov qword ptr [rsp+0x30], rax
mov eax, dword ptr [rsp+0x3C]
mov dword ptr [rsp+0x2C], eax
salt_front_resource_clip:
mov rax, qword ptr [rsp+0x30]
mov rcx, qword ptr [rax+0x480]
test rcx, rcx
je salt_front_resource_invalid
cmp dword ptr [rcx+8], 0
je salt_front_resource_invalid
cmp dword ptr [rcx+8], 0x10000
ja salt_front_resource_invalid
cmp qword ptr [rcx+0x10], 0
je salt_front_resource_invalid
mov edx, dword ptr [rsp+0x2C]
mov r8d, -1
call {native_ladder_motion_index}
test eax, eax
js salt_front_resource_invalid
cmp eax, 0x10000
jae salt_front_resource_invalid
mov rcx, qword ptr [rsp+0x30]
mov r10, qword ptr [rcx+0x468]
test r10, r10
je salt_front_resource_invalid
mov rcx, qword ptr [rcx+0x470]
cmp rcx, r10
jbe salt_front_resource_invalid
sub rcx, r10
test cl, 7
jne salt_front_resource_invalid
cmp rcx, 0x80000
ja salt_front_resource_invalid
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae salt_front_resource_invalid
cmp qword ptr [r10+rdx], 0
je salt_front_resource_invalid
mov eax, dword ptr [rsp+0x2C]
cmp eax, dword ptr [rsp+0x38]
je salt_front_resource_next
mov eax, dword ptr [rsp+0x38]
mov dword ptr [rsp+0x2C], eax
jmp salt_front_resource_clip
salt_front_resource_next:
cmp dword ptr [rsp+0x28], 6
je salt_front_resource_valid
mov dword ptr [rsp+0x28], 6
jmp salt_front_resource_slot
salt_front_resource_valid:
mov eax, 1
add rsp, 0x48
ret
salt_front_resource_invalid:
xor eax, eax
add rsp, 0x48
ret
'''


def _once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Frozen v056 shape changed: '+old.splitlines()[0])
    return source.replace(old, new, 1)


def _without_islands(source):
    source = re.sub(r'jmp salt_hurt_failure_(\d+)_continue\n'
                    r'salt_hurt_failure_\1:\njmp salt_hurt_clear\n'
                    r'salt_hurt_failure_\1_continue:\n', '', source)
    return re.sub(r' salt_hurt_failure_\d+(?=\n)', ' salt_hurt_clear', source)


def _assemble(source, plan, base, allocation, offset):
    from keystone import Ks, KS_ARCH_X86, KS_MODE_64
    values = {k: base+v for k,v in plan['targets'].items()}
    values['data'] = allocation+plan['data_offset']
    carrier = next((h for h in plan['hooks'] if h['code_offset']==offset), None)
    if carrier is not None:
        values['return'] = base+carrier['rva']+carrier['length']
    return bytes(Ks(KS_ARCH_X86, KS_MODE_64).asm(
        source.format(**values), addr=allocation+offset)[0])

CHANGED_HOOK_INDICES = (0, 34, 39)
RESOURCE_HELPER_OFFSET, RESOURCE_HELPER_CAPACITY = 0x100, 0x120
SELECTED_SIGNATURE_OFFSET, SELECTED_SIGNATURE_CAPACITY = 0x220, 0x1E0
EXPECTED_MOTION_OFFSET, EXPECTED_MOTION_CAPACITY = 0xEEF4, 0x3C
SELECTED_INDEX_OFFSET, SELECTED_INDEX_CAPACITY = 0xEF30, 0xD0
SOURCE152_FIRST, SOURCE152_COUNT = 2615, 32
SELECTED96_INDEX = 2634
SELECTED152_INDICES = (7921, 7932, 7933)
SELECTED96_RAW = bytes.fromhex(
    '34003c00ffffffffffff00ffffffff000000000060000000ff806464400020000080ff7fffffffffffffffffffffffff')

EXPECTED_MOTION_ASM = '''salt96_expected_motion:
cmp ecx, 96
jne salt96_expected_rear
mov eax, 30014
ret
salt96_expected_rear:
mov eax, ecx
sub eax, 106
cmp eax, 3
ja salt96_expected_invalid
shr eax, 1
imul eax, eax, 6
add eax, 30102
ret
salt96_expected_invalid:
mov eax, -1
ret
'''

# This compares only bounded table-slot values; the main helper still proves
# source-record range, owner, enabled state and unique membership before
# the signature helper dereferences the selected record.
SELECTED_INDEX_ASM = '''salt96_selected_index:
mov r10, qword ptr [r14+0x50]
test r10, r10
je salt96_index_invalid
movzx ecx, word ptr [r14+0x5A]
cmp cx, word ptr [r14+0x58]
ja salt96_index_invalid
mov r9, qword ptr [r13+0x90]
test r9, r9
je salt96_index_invalid
cmp ebx, 96
jne salt96_index152
mov eax, 2634
mov edx, 152
cmp eax, ecx
jae salt96_index_invalid
cmp qword ptr [r10+rax*8], r9
je salt96_index_done
jmp salt96_index_invalid
salt96_index152:
cmp ebx, 152
jne salt96_index_invalid
mov edx, 224
mov eax, 7921
cmp eax, ecx
jae salt96_index_invalid
cmp qword ptr [r10+rax*8], r9
je salt96_index_done
mov eax, 7932
cmp eax, ecx
jae salt96_index_invalid
cmp qword ptr [r10+rax*8], r9
je salt96_index_done
mov eax, 7933
cmp eax, ecx
jae salt96_index_invalid
cmp qword ptr [r10+rax*8], r9
jne salt96_index_invalid
salt96_index_done:
ret
salt96_index_invalid:
mov eax, -1
ret
'''


def selected_signature_asm():
    # r9 is the already proven owned unique-table member, rax source record.
    # Each byte of all48 descriptor bytes is checked, including queries,
    # native target, input, flags and frame windows. No query is rewritten.
    source = '''salt96_selected_signature:
cmp ebx, 96
jne salt96_signature152
cmp dword ptr [rax+0x80], 0x00200A37
jne salt96_signature_invalid
mov r10, qword ptr [rax+0x20]
test r10, r10
je salt96_signature_invalid
cmp dword ptr [r10+0x20], -1
jne salt96_signature_invalid
mov r10, 0xFFFFFFFF003C0034
cmp qword ptr [r9], r10
jne salt96_signature_invalid
jmp salt96_signature_tail
salt96_signature152:
cmp ebx, 152
jne salt96_signature_invalid
cmp ecx, 7921
jne salt96_signature7932
mov eax, 332
jmp salt96_signature_query
salt96_signature7932:
cmp ecx, 7932
jne salt96_signature7933
mov eax, 73
jmp salt96_signature_query
salt96_signature7933:
cmp ecx, 7933
jne salt96_signature_invalid
mov eax, 29
salt96_signature_query:
cmp word ptr [r9+2], ax
jne salt96_signature_invalid
mov r10, qword ptr [r9]
mov r11, 0xFFFFFFFF0000FFFF
and r10, r11
mov r11, 0xFFFFFFFF00000034
cmp r10, r11
jne salt96_signature_invalid
salt96_signature_tail:
'''
    for offset, value in zip((8, 24, 32, 40),
                            (0x00FFFFFFFF00FFFF, 0x00200040646480FF,
                             0xFFFFFFFF7FFF8000, 0xFFFFFFFFFFFFFFFF)):
        source += (f'mov r10, {value}\ncmp qword ptr [r9+{offset}], r10\n'
                   'jne salt96_signature_invalid\n')
    source += '''mov eax, ebx
shl rax, 32
cmp qword ptr [r9+16], rax
jne salt96_signature_invalid
mov eax, 1
ret
salt96_signature_invalid:
xor eax, eax
ret
'''
    return source


def main_helper_asm():
    source = _without_islands(frozen.ASM)
    motionless = '''cmp eax, 151
je salt_hurt_current_motionless
'''
    source = _once(source, motionless, motionless+'''cmp eax, 152
je salt_hurt_current_motionless
''')
    source = _once(source, '''sub eax, 106
cmp eax, 3
ja salt_hurt_clear
shr eax, 1
imul eax, eax, 6
add eax, 30102
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
jmp salt_hurt_dispatch
''', '''mov ecx, eax
call {data} - 0x10C
test eax, eax
js salt_hurt_clear
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
jmp salt_hurt_dispatch
''')
    marker = '''salt_hurt_dispatch_active:
cmp dword ptr [r15], 1
jne salt_hurt_clear
'''
    source = _once(source, marker, marker+'''cmp ebx, 152
je salt96_dispatch
cmp ebx, 96
jne salt96_dispatch_rear
salt96_dispatch:
call {data} - 0xD0
test eax, eax
js salt_hurt_clear
mov dword ptr [rsp+0xA8], eax
mov dword ptr [rsp+0xAC], edx
jmp salt_hurt_records
salt96_dispatch_rear:
''')
    # The original unique-member proof leads directly to parameters. Insert
    # the exact selected signature only for the two added native targets.
    marker = '''salt_hurt_parameters:
mov rax, qword ptr [rsp+0x98]
'''
    source = _once(source, marker, '''salt_hurt_parameters:
cmp ebx, 152
je salt96_signature
cmp ebx, 96
jne salt96_parameters_rear
salt96_signature:
mov rax, qword ptr [rsp+0xA0]
mov ecx, dword ptr [rsp+0xA8]
call {data} - 0xEDE0
test eax, eax
je salt_hurt_clear
salt96_parameters_rear:
mov rax, qword ptr [rsp+0x98]
''')
    marker = '''cmp ebx, 151
je salt_hurt_motionless
'''
    source = _once(source, marker, marker+'''cmp ebx, 152
je salt_hurt_motionless
''')
    source = _once(source, '''mov eax, ebx
sub eax, 106
shr eax, 1
imul eax, eax, 6
add eax, 30102
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
''', '''mov ecx, ebx
call {data} - 0x10C
test eax, eax
js salt_hurt_clear
cmp dword ptr [r10+0x20], eax
jne salt_hurt_clear
''')
    start = source.index('mov qword ptr [rsp+0x80], rax\n')
    end = source.index('salt_hurt_motionless:\n', start)
    source = source[:start]+'''mov rcx, rax
mov edx, 30102
mov r8d, 30108
cmp ebx, 96
jne salt96_resources
mov edx, 30014
mov r8d, 30014
salt96_resources:
call {data} - 0xEF00
test eax, eax
je salt_hurt_clear
jmp salt_hurt_success
'''+source[end:]
    return frozen._short_failure_islands(source)


def apply_salt_damage96_draft(previous):
    if (previous.get('tool_version') != '0.56-experimental'
            or not previous.get('salt_hurt_compatibility')
            or len(previous.get('hooks', ())) != 50
            or (previous.get('allocation_size'), previous.get('data_offset')) != (0x14000,0xF000)):
        raise ValueError('Complete frozen v056 profile required')
    plan = deepcopy(previous)
    preload, main, lookup = (plan['hooks'][i] for i in CHANGED_HOOK_INDICES)
    if ((preload['name'],preload['code_offset'],preload.get('code_capacity',0x400)) != ('HE_Preload',0,0x400)
            or not main['asm'].endswith(frozen.ASM)
            or (lookup['name'],lookup['code_offset'],lookup.get('code_capacity')) != ('HE_LadderCommonLookup',0xE800,0x800)):
        raise ValueError('Frozen carrier layout differs')
    base, allocation = 0x140000000, 0x144000000
    old_preload = _assemble(preload['asm'],plan,base,allocation,0)
    if len(old_preload) != 0x80:
        raise ValueError('Frozen Preload prefix differs')
    resource = _assemble(RESOURCE_HELPER_ASM,plan,base,allocation,RESOURCE_HELPER_OFFSET)
    signature = _assemble(selected_signature_asm(),plan,base,allocation,SELECTED_SIGNATURE_OFFSET)
    expected = _assemble(EXPECTED_MOTION_ASM,plan,base,allocation,EXPECTED_MOTION_OFFSET)
    selection = _assemble(SELECTED_INDEX_ASM,plan,base,allocation,SELECTED_INDEX_OFFSET)
    for payload, capacity in ((resource,RESOURCE_HELPER_CAPACITY),
                             (signature,SELECTED_SIGNATURE_CAPACITY),
                             (expected,EXPECTED_MOTION_CAPACITY),
                             (selection,SELECTED_INDEX_CAPACITY)):
        if len(payload)>capacity:
            raise ValueError('Salt96 helper exceeds fixed spare tail')
    preload['asm'] += ('\n'+'nop\n'*(RESOURCE_HELPER_OFFSET-len(old_preload))
        +RESOURCE_HELPER_ASM+'nop\n'*(SELECTED_SIGNATURE_OFFSET-RESOURCE_HELPER_OFFSET-len(resource))
        +selected_signature_asm())
    main['asm'] = main['asm'][:-len(frozen.ASM)]+main_helper_asm()
    old_lookup = _assemble(lookup['asm'],plan,base,allocation,0xE800)
    if 0xE800+len(old_lookup) != EXPECTED_MOTION_OFFSET:
        raise ValueError('Frozen lookup resource tail differs')
    lookup['asm'] += ('\n'+EXPECTED_MOTION_ASM
        +'nop\n'*(EXPECTED_MOTION_CAPACITY-len(expected))+SELECTED_INDEX_ASM)
    plan.update(tool_version='0.57-experimental',stage='offline_salt_actual152_damage96_draft',
        salt_damage96_draft=True,salt_damage96_gameplay_verified=False,
        salt_damage96_changed_hook_indices=list(CHANGED_HOOK_INDICES),
        salt_damage96_selected_common224_entries=list(SELECTED152_INDICES),
        salt_damage96_selected_common152_entry=SELECTED96_INDEX,
        salt_damage96_selected_common152_signature=SELECTED96_RAW.hex(),
        salt_damage96_common_motion_ids=[30014],distribution_ready=False)
    return plan
