"""Scoped common170 -> 73/74/75 routing for the native Abyss entrance.
Fixed helper entries and address-free descriptor checks share the aura slot.
"""
from copy import deepcopy

from hinoenma_abyss_resources import resources
from hinoenma_abyss_assembly import assemble
HELPER_OFFSET = 0x2F000
GENERIC_OFFSET, QUEUED_OFFSET, LOOKUP_OFFSET, GATE_OFFSET = (0,0x40,0x80,0x400)
CHANGED_INDICES = (8,9,39,70)


def pointer(reg, bad, scratch='rax'):
    return f'''test {reg}, {reg}
je {bad}
cmp {reg}, 0x10000
jb {bad}
mov {scratch}, 0x7FFFFFFFFFFF
cmp {reg}, {scratch}
ja {bad}
'''

TABLES=[]

def equal_bytes(reg, raw, bad):
    if len(raw)%8:raise ValueError('Complete qwords required')
    if reg!='r10':raise ValueError('Bounded comparison input must be R10')
    offset=sum(map(len,TABLES));TABLES.append(raw)
    return f'''mov rax, {{data}}
add rax, 0x{0x23500+offset:X}
mov ecx, {len(raw)//8}
call abyss_actions_equal
jnc {bad}
'''

SAVES='''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
push rsi
push rdi
sub rsp, 0xC0
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0xB0]
'''
RESTORES='''ldmxcsr dword ptr [rsp+0xB0]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xC0
pop rdi
pop rsi
pop rbx
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''

def gate_asm(rows):
    bad='abyss_actions_gate_bad'
    s='abyss_actions_gate:\n'+SAVES+'''mov dword ptr [rsp+0xB4], 0
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne abyss_actions_gate_bad
mov edx, dword ptr [r11+4]
cmp edx, 0x58E5E
je abyss_actions_gate_selected
cmp edx, 0x51BE1
jne abyss_actions_gate_bad
abyss_actions_gate_selected:
cmp dword ptr [r11], edx
jne abyss_actions_gate_bad
mov r10, qword ptr [r11+0x10]
'''+pointer('r10',bad)+'''mov rax, {player_slot}
cmp qword ptr [rax], r10
jne abyss_actions_gate_bad
cmp dword ptr [r10], edx
jne abyss_actions_gate_bad
cmp dword ptr [r10+4], 0x10000
jne abyss_actions_gate_bad
cmp dword ptr [r10+0xEF0], 0
jne abyss_actions_gate_bad
mov qword ptr [rsp+0x80], r10
mov r9, qword ptr [r10+0xE90]
'''+pointer('r9',bad)+'''cmp dword ptr [r9], edx
jne abyss_actions_gate_bad
cmp dword ptr [r9+0xC], 1
jne abyss_actions_gate_bad
mov r9, qword ptr [r10+0x240]
'''+pointer('r9',bad)+'''cmp qword ptr [r9], r10
jne abyss_actions_gate_bad
cmp qword ptr [r9+0x108], r10
jne abyss_actions_gate_bad
cmp qword ptr [r9+0x20], 0
jle abyss_actions_gate_bad
mov r9, qword ptr [r10+0x230]
'''+pointer('r9',bad)+'''cmp qword ptr [r9], r10
jne abyss_actions_gate_bad
cmp qword ptr [r9+8], rdi
jne abyss_actions_gate_bad
cmp qword ptr [rdi+0x50], r10
jne abyss_actions_gate_bad
cmp qword ptr [rdi+0x5B0], 0
jne abyss_actions_gate_bad
cmp qword ptr [rdi+0x5D8], 0
jne abyss_actions_gate_bad
mov qword ptr [rsp+0x88], rdi
mov r9, qword ptr [rsp+0xF0]
mov r10, qword ptr [rsp+0x108]
cmp qword ptr [rsp+0x120], 0
je abyss_actions_gate_request
mov r9, qword ptr [rdi+0x510]
mov r10, qword ptr [rdi+0x528]
abyss_actions_gate_request:
'''+pointer('r9',bad)+pointer('r10',bad)+'''cmp dword ptr [r9], 0xEA6E
jne abyss_actions_gate_bad
cmp dword ptr [r9+4], 2
jne abyss_actions_gate_bad
mov rax, qword ptr [rsp+0x80]
mov rcx, qword ptr [r9+0x320]
test rcx, rcx
je abyss_actions_gate_object_owner
cmp rcx, rax
jne abyss_actions_gate_bad
abyss_actions_gate_object_owner:
cmp qword ptr [r10], r9
jne abyss_actions_gate_bad
cmp word ptr [r10+8], 0x101
jne abyss_actions_gate_bad
cmp byte ptr [r10+0xA], 1
ja abyss_actions_gate_bad
cmp dword ptr [r10+0x48], 10
jne abyss_actions_gate_bad
cmp qword ptr [r10+0x4C], 0
jne abyss_actions_gate_bad
mov qword ptr [rsp+0x90], r10
cmp qword ptr [rsp+0x120], 2
je abyss_actions_gate_bank
cmp byte ptr [r10+0xA], 0
jne abyss_actions_gate_bad
cmp qword ptr [rsp+0x120], 1
je abyss_actions_gate_idle
cmp byte ptr [rdi+0x4E9], 1
jne abyss_actions_gate_bad
abyss_actions_gate_idle:
mov r9, qword ptr [rdi+0x58]
'''+pointer('r9',bad)+'''cmp dword ptr [r9], 0
jne abyss_actions_gate_bad
cmp byte ptr [r9+0x40], 1
jne abyss_actions_gate_bad
abyss_actions_gate_bank:
mov rbx, qword ptr [rdi+0x80]
'''+pointer('rbx',bad)+'''mov qword ptr [rsp+0x98], rbx
cmp dword ptr [rbx+0x130], 0
je abyss_actions_gate_bad
cmp dword ptr [rbx+0x130], 0x1000
ja abyss_actions_gate_bad
mov rsi, qword ptr [rbx+0x128]
'''+pointer('rsi',bad)+'''mov r9, qword ptr [rbx+0x50]
'''+pointer('r9',bad)+'''movzx eax, word ptr [rbx+0x58]
cmp word ptr [rbx+0x5A], ax
ja abyss_actions_gate_bad
cmp ax, 0
je abyss_actions_gate_bad
'''
    for ident in (170,73,74,75):
        r=rows[ident]; p=f'abyss_actions_record_{ident}'
        s+=f'''xor edx, edx
xor r8d, r8d
{p}_loop:
mov r11, qword ptr [rsi+rdx*8]
test r11, r11
je {p}_next
cmp dword ptr [r11], {ident}
jne {p}_next
inc r8d
cmp r8d, 1
jne abyss_actions_gate_bad
cmp byte ptr [r11+0x40], 1
jne abyss_actions_gate_bad
cmp qword ptr [r11+0x38], rbx
jne abyss_actions_gate_bad
mov r10, qword ptr [r11+0x20]
'''+pointer('r10',bad)+equal_bytes('r10',bytes.fromhex(r['parameter_raw_00_a0']),bad)+f'''mov r9, qword ptr [rbx+0x50]
cmp qword ptr [r11+0x78], r9
jne abyss_actions_gate_bad
cmp word ptr [r11+0x80], {r['transition_first']}
jne abyss_actions_gate_bad
cmp word ptr [r11+0x82], {r['transition_count']}
jne abyss_actions_gate_bad
cmp word ptr [rbx+0x5A], {r['transition_first']+r['transition_count']}
jb abyss_actions_gate_bad
'''
        for ti,t in enumerate(r['transitions']):
            s+=f'mov r10, qword ptr [r9+{(r["transition_first"]+ti)*8}]\n'+pointer('r10',bad)+equal_bytes('r10',bytes.fromhex(t['raw']),bad)
        s+=f'''{p}_next:
inc edx
cmp edx, dword ptr [rbx+0x130]
jb {p}_loop
cmp r8d, 1
jne abyss_actions_gate_bad
'''
    s+='''mov r9, qword ptr [rbx+0x80]
'''+pointer('r9',bad)+'''cmp word ptr [rbx+0x88], 42
jbe abyss_actions_gate_bad
cmp word ptr [rbx+0x88], 0x1000
ja abyss_actions_gate_bad
'''
    for e in (r for r in rows[73]['references'] if r['index']>=0):
        s+=f'mov r10, qword ptr [r9+{e["index"]*8}]\n'+pointer('r10',bad)+equal_bytes('r10',bytes.fromhex(e['raw_00_80']),bad)
    s+='''mov rax, qword ptr [rsp+0x80]
mov r10, qword ptr [rax+0x38]
'''+pointer('r10',bad)+'''cmp dword ptr [r10+0x50], 1
ja abyss_actions_gate_bad
mov qword ptr [rsp+0xA0], r10
'''
    for slot in (2,6):
        for motion in (900,901,902):
            s+=f'''mov rax, qword ptr [rsp+0xA0]
mov rbx, qword ptr [rax+{8+slot*8}]
'''+pointer('rbx',bad)+'''mov rcx, qword ptr [rbx+0x480]
'''+pointer('rcx',bad)+'''cmp dword ptr [rcx+8], 0
je abyss_actions_gate_bad
cmp dword ptr [rcx+8], 0x10000
ja abyss_actions_gate_bad
mov r10, qword ptr [rcx+0x10]
'''+pointer('r10',bad)+f'''mov edx, {motion}
mov r8d, -1
call {{native_ladder_motion_index}}
test eax, eax
js abyss_actions_gate_bad
mov r10, qword ptr [rbx+0x468]
'''+pointer('r10',bad,scratch='r11')+'''mov rcx, qword ptr [rbx+0x470]
cmp rcx, r10
jbe abyss_actions_gate_bad
sub rcx, r10
cmp rcx, 0x80000
ja abyss_actions_gate_bad
test cl, 7
jne abyss_actions_gate_bad
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae abyss_actions_gate_bad
mov r9, qword ptr [r10+rdx]
'''+pointer('r9',bad)
    s+='''mov dword ptr [rsp+0xB4], 1
cmp qword ptr [rsp+0x120], 1
jne abyss_actions_gate_bad
mov rcx, qword ptr [rsp+0x88]
mov edx, 170
call {native_ladder_set_action}
abyss_actions_gate_bad:
and qword ptr [rsp+0x110], -2
cmp dword ptr [rsp+0xB4], 0
je abyss_actions_gate_restore
or qword ptr [rsp+0x110], 1
abyss_actions_gate_restore:
'''+RESTORES+'ret\n'
    return s

def lookup_asm():
    return 'abyss_actions_lookup:\n'+SAVES+'''mov ebx, edx
cmp ebx, 170
je abyss_actions_lookup_fast_family
sub ebx, 73
cmp ebx, 2
ja abyss_actions_lookup_original
add ebx, 73
abyss_actions_lookup_fast_family:
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne abyss_actions_lookup_original
cmp dword ptr [r11+4], 0x58E5E
je abyss_actions_lookup_fast_selected
cmp dword ptr [r11+4], 0x51BE1
jne abyss_actions_lookup_original
abyss_actions_lookup_fast_selected:
mov r10, qword ptr [r11+0x10]
test r10, r10
je abyss_actions_lookup_original
mov rax, {player_slot}
cmp qword ptr [rax], r10
jne abyss_actions_lookup_original
mov r9, qword ptr [r10+0x230]
test r9, r9
je abyss_actions_lookup_original
mov rdi, qword ptr [r9+8]
test rdi, rdi
je abyss_actions_lookup_original
lea rax, [rdi+0x70]
cmp rcx, rax
jne abyss_actions_lookup_original
mov ebx, edx
cmp ebx, 170
je abyss_actions_lookup_family
sub ebx, 73
cmp ebx, 2
ja abyss_actions_lookup_original
add ebx, 73
abyss_actions_lookup_family:
sub rsp, 0x10
mov qword ptr [rsp], 2
call abyss_actions_gate
lea rsp, [rsp+0x10]
jnc abyss_actions_lookup_original
mov r9, qword ptr [rdi+0x80]
mov r10, qword ptr [rdi+0x58]
test r10, r10
je abyss_actions_lookup_original
cmp dword ptr [r10], 0
je abyss_actions_lookup_entry
cmp qword ptr [r10+0x38], r9
jne abyss_actions_lookup_original
mov ecx, dword ptr [r10]
cmp ecx, 170
je abyss_actions_lookup_entry
sub ecx, 73
cmp ecx, 2
ja abyss_actions_lookup_original
cmp ebx, 170
je abyss_actions_lookup_original
jmp abyss_actions_lookup_scan
abyss_actions_lookup_entry:
cmp ebx, 170
je abyss_actions_lookup_scan
cmp ebx, 73
jne abyss_actions_lookup_original
abyss_actions_lookup_scan:
mov r10, qword ptr [r9+0x128]
xor ecx, ecx
abyss_actions_lookup_loop:
mov rax, qword ptr [r10+rcx*8]
test rax, rax
je abyss_actions_lookup_next
cmp dword ptr [rax], ebx
je abyss_actions_lookup_found
abyss_actions_lookup_next:
inc ecx
cmp ecx, dword ptr [r9+0x130]
jb abyss_actions_lookup_loop
jmp abyss_actions_lookup_original
abyss_actions_lookup_found:
mov qword ptr [rsp+0x108], rax
mov r8, qword ptr [rsp+0xF0]
test r8, r8
je abyss_actions_lookup_return
mov dword ptr [r8], 2
abyss_actions_lookup_return:
'''+RESTORES+'''ret
abyss_actions_lookup_original:
'''+RESTORES+'''pushfq
push rax
push rcx
push rdx
push r8
jmp {data} - 0x800 + 6
'''

def helpers(plan, gate):
    TABLES.clear()
    pieces=[('abyss_actions_generic:\npush 0\ncall abyss_actions_gate\nlea rsp, [rsp+8]\njc abyss_actions_generic_return\njmp {data} + 0x1300\nabyss_actions_generic_return:\nret\n',0),
            ('abyss_actions_queued:\npushfq\nsub rsp, 0x10\nmov qword ptr [rsp], 1\ncall abyss_actions_gate\nadd rsp, 0x10\npopfq\njmp {data} - 0xCEF0\n',0x40),
            (lookup_asm(),0x80),('''abyss_actions_equal:
push r8
abyss_actions_equal_loop:
dec ecx
mov r8, qword ptr [r10+rcx*8]
cmp qword ptr [rax+rcx*8], r8
jne abyss_actions_equal_bad
test ecx, ecx
jne abyss_actions_equal_loop
pop r8
stc
ret
abyss_actions_equal_bad:
pop r8
clc
ret
''',0x380),(gate(resources()),0x400)]
    # Keystone supports forward references only within a single assembly call.
    # Determine segment sizes with the unresolved local gate replaced by its
    # fixed absolute private address, then pad before joining the real labels.
    assembled=''; pos=0
    for asm,off in pieces:
        if pos>off:raise ValueError('Abyss helper fixed entry exceeds padding')
        assembled+='nop\n'*(off-pos)+asm
        test=deepcopy(plan);h=deepcopy(plan['hooks'][70]);h['asm']=assembled.replace('call abyss_actions_gate','call {data} + 0x20400').replace('call abyss_actions_equal','call {data} + 0x20380')
        h['code_offset']=HELPER_OFFSET;h['code_capacity']=0x5000;test['hooks']=[h]
        pos=len(assemble(test,0x140000000,0x150000000)[0]['payload'])
    if pos>0x3500:raise ValueError(f'Abyss executable helpers overlap static expected resources: {pos:X}')
    plan['abyss_helper_code_size']=pos
    assembled+='\n'+'.byte 0\n'*(0x3500-pos)
    blob=b''.join(TABLES)
    if len(blob)>0x1B00:raise ValueError('Abyss expected resources exceed carrier padding')
    assembled+=''.join(f'.byte {b}\n' for b in blob)
    return assembled

def apply_actions(previous, gate):
    if previous.get('tool_version') != '1.0.0-beta.5.4.2' or len(previous['hooks']) != 81:
        raise ValueError('Complete Beta5.4.2 source required')
    plan=deepcopy(previous)
    a,b,lookup,aura=(plan['hooks'][i] for i in CHANGED_INDICES)
    old=assemble(previous,0x140000000,0x150000000)
    for h,needle,replacement in (
        (a,'call {data} + 0x1300\n','call {data} + 0x20000\n'),
        (b,'call {data} - 0xCEF0\n','call {data} + 0x20040\n'),
        (lookup,'pushfq\npush rax\npush rcx\npush rdx\npush r8\n','jmp {data} + 0x20080\nnop\n')):
        if h['asm'].count(needle)!=1:raise ValueError('Expected fixed-width wrapper entry changed')
        h['asm']=h['asm'].replace(needle,replacement,1)
    if old[70]['code_offset']!=0x2D000 or old[70]['code_capacity']!=0x7000:
        raise ValueError('Declared aura carrier slot changed')
    padding=HELPER_OFFSET-old[70]['code_offset']-len(old[70]['payload'])
    if padding<0:raise ValueError('Existing aura prefix overlaps new helper')
    aura['asm']+='\n'+'.byte 0\n'*padding+helpers(plan, gate)
    return plan
