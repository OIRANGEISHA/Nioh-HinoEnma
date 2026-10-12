"""Uninstalled portable LW startup discovery; pure source, no process access.

The helper writes only its private workspace and the independent 512B binding.
All native discovery, SetAction, scheduler, initializer and spawn calls belong
to the separate R4 input/native chain. This module must not replace that chain.
"""
from copy import deepcopy
from living_weapon_start_views import FIELDS, FIELD_WIDTHS, MAGIC

CORE_OFFSET = 0xF000
BIND_OFFSET, BIND_SIZE = 0x44200, 0x200
WORKSPACE_OFFSET, WORKSPACE_END = 0x55000, 0x61000
CODE_OFFSET, CODE_END = 0x62000, 0x69000
ALLOCATION_SIZE = 0x69000
STAGE_A, STAGE_B = 0x200, 0x400
JOURNAL_FIRST, JOURNAL_END = 0x600, 0x2000
SORT_OFFSET, SORT_SIZE = 0x2000, 0x4000
LONG_SCHEDULE, SHORT_SCHEDULE = 0x6000, 0x9000
ITERATION_BUDGET = 4000000


def targets():
    return dict(lw_item_hash_manager=0x18BACE0, lw_item_database=0x1871720,
                lw_item_family_keys=0x11A1880)


def layout():
    return dict(core_offset=CORE_OFFSET, binding_offset=BIND_OFFSET, binding_size=BIND_SIZE,
                workspace_offset=WORKSPACE_OFFSET, workspace_size=WORKSPACE_END-WORKSPACE_OFFSET,
                code_offset=CODE_OFFSET, code_capacity=CODE_END-CODE_OFFSET,
                allocation_size=ALLOCATION_SIZE, stage_a=WORKSPACE_OFFSET+STAGE_A,
                stage_b=WORKSPACE_OFFSET+STAGE_B, journal=(WORKSPACE_OFFSET+JOURNAL_FIRST,WORKSPACE_OFFSET+JOURNAL_END),
                sort=(WORKSPACE_OFFSET+SORT_OFFSET,WORKSPACE_OFFSET+SORT_OFFSET+SORT_SIZE),
                schedules=((WORKSPACE_OFFSET+LONG_SCHEDULE,WORKSPACE_OFFSET+SHORT_SCHEDULE),
                           (WORKSPACE_OFFSET+SHORT_SCHEDULE,WORKSPACE_END)),
                entry_abi='RCX actor,RDX ctl,R8 core,R9 binding; EAX bool; nonvolatile/allXMM/MXCSR/EFLAGS/DF preserved',
                native_calls=0, phase_on_success=0, magic_published_last=True)


def ptr(reg, bad, scratch='rax', alignment=8):
    if reg == scratch:
        raise ValueError('Pointer scratch must differ from source')
    s=f'''cmp {reg}, 0x10000
jb {bad}
mov {scratch}, 0x800000000000
cmp {reg}, {scratch}
jae {bad}
'''
    if alignment > 1:
        s+=f'test {reg}, {alignment-1}\njne {bad}\n'
    return s


def span(reg, size, bad, scratch='rax', limit='r11'):
    """Validate derived canonical end before reading a bounded native vector."""
    return f'''mov {limit}, {reg}
add {limit}, {size}
jc {bad}
mov {scratch}, 0x800000000000
cmp {limit}, {scratch}
jae {bad}
'''


def pin(p, address, size, bad):
    return f'''mov rcx, {address}
mov edx, {size}
call {p}_pin
test eax, eax
je {bad}
'''


def budget(bad):
    return f'sub dword ptr [rsi+0xC], 1\nje {bad}\n'


def bootstrap_source(prefix='lwbs'):
    """Win64 entry; discover/revalidate first99 resources and publish phase0.

    Volatile GPRs may change. All nonvolatile GPRs, EFLAGS/DF, XMMs and MXCSR
    are preserved. Caller must retain R4's actual empty-queue and first native
    scheduler flush guards. No native routine is called from this source.
    """
    if not prefix.replace('_','').isalnum() or not prefix[0].isalpha():
        raise ValueError('ASM label prefix required')
    p=prefix; bad=p+'_entry_bad'; unlock=p+'_unlock_bad'; finish=p+'_finish'
    s=f'''{p}_entry:
pushfq
push rbx
push rbp
push rsi
push rdi
push r12
push r13
push r14
push r15
sub rsp, 0x20
mov r12, rcx
mov r13, rdx
mov r14, {{data}}
cmp r8, r14
jne {bad}
mov r15, r14
add r15, 0x{BIND_OFFSET-CORE_OFFSET:X}
cmp r9, r15
jne {bad}
mov rsi, r14
add rsi, 0x{WORKSPACE_OFFSET-CORE_OFFSET:X}
xor eax, eax
mov ecx, 1
lock cmpxchg dword ptr [rsi], ecx
jne {bad}
mov dword ptr [rsi+4], 1
mov dword ptr [rsi+0xC], {ITERATION_BUDGET}
mov dword ptr [rsi+0x50], 0
mov dword ptr [rsi+0x54], 0
mov qword ptr [rsi+0x10], r12
mov qword ptr [rsi+0x18], r13
mov dword ptr [rsi+8], 1
lea rdi, [rsi+0x{STAGE_A:X}]
call {p}_scope
test eax, eax
je {p}_unlock_keep
mov dword ptr [r15], 0
mov dword ptr [r15+0x18], 0
mov dword ptr [rsi+8], 1
lea rdi, [rsi+0x{STAGE_A:X}]
call {p}_discover
test eax, eax
je {unlock}
mov dword ptr [rsi+8], 2
lea rdi, [rsi+0x{STAGE_B:X}]
call {p}_discover
test eax, eax
je {unlock}
mov eax, dword ptr [rsi+0x50]
cmp eax, dword ptr [rsi+0x54]
jne {unlock}
lea r8, [rsi+0x{STAGE_A:X}]
lea r9, [rsi+0x{STAGE_B:X}]
mov ecx, 64
{p}_compare:
mov rax, qword ptr [r8]
cmp rax, qword ptr [r9]
jne {unlock}
add r8, 8
add r9, 8
dec ecx
jne {p}_compare
call {p}_replay
test eax, eax
je {unlock}
call {p}_roots
test eax, eax
je {unlock}
lea r8, [rsi+0x{STAGE_B:X}]
mov r9, r15
mov ecx, 64
{p}_publish:
mov rax, qword ptr [r8]
mov qword ptr [r9], rax
add r8, 8
add r9, 8
dec ecx
jne {p}_publish
mov dword ptr [r15], 0x{MAGIC:X}
mov dword ptr [rsi+4], 0
mov dword ptr [rsi], 0
mov eax, 1
jmp {finish}
{unlock}:
mov dword ptr [r15], 0
mov dword ptr [r15+0x18], 0
{p}_unlock_keep:
mov dword ptr [rsi], 0
{bad}:
xor eax, eax
{finish}:
add rsp, 0x20
pop r15
pop r14
pop r13
pop r12
pop rdi
pop rsi
pop rbp
pop rbx
popfq
ret
'''
    return s+discover_source(p)+scope_source(p)+equipment_source(p)+package_source(p)+\
        catalog_source(p)+action_source(p)+start_source(p)+motion_source(p)+events_source(p)+\
        hash_source(p)+sort_source(p)+pin_source(p)+roots_source(p)+f'''{p}_false:
xor eax, eax
ret
'''


def discover_source(p):
    bad=p+'_false'
    s=f'''{p}_discover:
push rbp
push rbx
sub rsp, 0x28
mov r8, rdi
mov ecx, 64
xor eax, eax
{p}_stage_clear:
mov qword ptr [r8], rax
add r8, 8
dec ecx
jne {p}_stage_clear
call {p}_scope
test eax, eax
je {p}_discover_bad
call {p}_equipment
test eax, eax
je {p}_discover_bad
call {p}_package
test eax, eax
je {p}_discover_bad
mov rdx, qword ptr [rdi+0x190]
call {p}_catalog
test eax, eax
je {p}_discover_bad
mov rdx, qword ptr [rdi+0x190]
xor eax, eax
call {p}_action
test eax, eax
je {p}_discover_bad
mov rax, qword ptr [rsi+0xA0]
cmp rax, qword ptr [rdi+0x58]
jne {p}_discover_bad
mov rax, qword ptr [rsi+0xA8]
cmp dword ptr [rax+0x20], 0
jne {p}_discover_bad
mov qword ptr [rdi+0x120], rax
mov rax, qword ptr [rsi+0xB0]
mov qword ptr [rdi+0x198], rax
mov rdx, qword ptr [rdi+0x30]
call {p}_catalog
test eax, eax
je {p}_discover_bad
mov rdx, qword ptr [rdi+0x30]
mov eax, 169
call {p}_action
test eax, eax
je {p}_discover_bad
mov rax, qword ptr [rsi+0xA0]
mov qword ptr [rdi+0x60], rax
mov rax, qword ptr [rsi+0xA8]
cmp dword ptr [rax+0x20], -1
jne {p}_discover_bad
mov qword ptr [rdi+0x118], rax
mov rax, qword ptr [rsi+0xB0]
mov qword ptr [rdi+0x188], rax
mov rdx, qword ptr [rdi+0x30]
mov rax, qword ptr [rdx+0x128]
mov qword ptr [rdi+0x168], rax
mov eax, dword ptr [rdx+0x130]
mov dword ptr [rdi+0x170], eax
xor eax, eax
call {p}_start
test eax, eax
je {p}_discover_bad
mov eax, 1
call {p}_start
test eax, eax
je {p}_discover_bad
mov eax, dword ptr [rdi+0x78]
cmp eax, dword ptr [rdi+0x7C]
je {p}_discover_bad
mov rdx, qword ptr [rdi+0x30]
mov eax, 3000
call {p}_action
test eax, eax
je {p}_discover_bad
mov rax, qword ptr [rsi+0xA8]
cmp dword ptr [rax+0x20], -1
jne {p}_discover_bad
xor eax, eax
call {p}_motion
test eax, eax
je {p}_discover_bad
mov eax, 1
call {p}_motion
test eax, eax
je {p}_discover_bad
xor eax, eax
call {p}_events
test eax, eax
je {p}_discover_bad
mov eax, 1
call {p}_events
test eax, eax
je {p}_discover_bad
mov eax, 1
jmp {p}_discover_done
{p}_discover_bad:
xor eax, eax
{p}_discover_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def scope_source(p):
    bad=p+'_false'
    s=f'''{p}_scope:
'''+ptr('r12',bad,'rax')+ptr('r13',bad,'rax')+f'''mov rax, {{player_slot}}
cmp qword ptr [rax], r12
jne {bad}
cmp qword ptr [r14+0x10], r12
jne {bad}
cmp dword ptr [r14+0x20], 1
jne {bad}
mov eax, dword ptr [r14+0x1C]
test eax, eax
je {bad}
mov dword ptr [rdi+4], eax
mov dword ptr [rsi+0x20], eax
mov qword ptr [rdi+8], r12
mov qword ptr [rdi+0x10], r13
mov rax, qword ptr [r12]
mov qword ptr [rdi+0x90], rax
cmp dword ptr [r12+4], 0x10000
jne {bad}
mov eax, dword ptr [r12]
cmp eax, 0x58E5E
je {p}_scope_role
cmp eax, 0x51BE1
jne {bad}
{p}_scope_role:
cmp eax, dword ptr [r14+4]
jne {bad}
cmp dword ptr [r12+0xEF0], 0
jne {bad}
mov rdx, qword ptr [r12+0xE90]
'''+ptr('rdx',bad,'rax',4)+f'''cmp dword ptr [rdx], eax
'''
    # Pointer guard clobbers RAX; reload template explicitly.
    s=s.rsplit('cmp dword ptr [rdx], eax\n',1)[0]+f'''mov eax, dword ptr [r12]
cmp dword ptr [rdx], eax
jne {bad}
cmp dword ptr [rdx+0xC], 1
jne {bad}
mov rdx, qword ptr [r12+0x240]
'''+ptr('rdx',bad,'rax')+span('rdx','0x9CD',bad)+f'''cmp qword ptr [rdx], r12
jne {bad}
cmp qword ptr [rdx+0x108], r12
jne {bad}
cmp qword ptr [rdx+0x20], 0
jle {bad}
cmp dword ptr [rdx+0xB0], 0
jne {bad}
mov qword ptr [rdi+0x88], rdx
mov rdx, qword ptr [r12+0x230]
'''+ptr('rdx',bad,'rax')+f'''cmp qword ptr [rdx], r12
jne {bad}
cmp qword ptr [rdx+8], r13
jne {bad}
cmp qword ptr [r13+0x50], r12
jne {bad}
cmp qword ptr [r13+0x510], 0
jne {bad}
cmp qword ptr [r13+0x5B0], 0
jne {bad}
cmp qword ptr [r13+0x5D8], 0
jne {bad}
mov rdx, qword ptr [r12+0x38]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rdi+0x80], rdx
mov rdx, qword ptr [r12+0x68]
'''+ptr('rdx',bad,'rax')+f'''cmp qword ptr [rdx+8], r12
jne {bad}
mov qword ptr [rdi+0x1A0], rdx
mov rdx, qword ptr [rdx+0x40]
'''+ptr('rdx',bad,'rax')+f'''cmp qword ptr [rdx+8], r12
jne {bad}
cmp dword ptr [rdx+0x18], 0
jne {bad}
mov qword ptr [rdi+0x1A8], rdx
mov rdx, qword ptr [r13+0x58]
'''+ptr('rdx',bad,'rax')+f'''cmp dword ptr [rdx], 0
jne {bad}
cmp byte ptr [rdx+0x40], 1
jne {bad}
mov qword ptr [rdi+0x58], rdx
mov rdx, qword ptr [rdx+0x38]
'''+ptr('rdx',bad,'rax')+f'''cmp rdx, qword ptr [r13+0x70]
je {p}_scope_idle
cmp rdx, qword ptr [r13+0x78]
je {p}_scope_idle
cmp rdx, qword ptr [r13+0x80]
jne {bad}
{p}_scope_idle:
mov qword ptr [rdi+0x190], rdx
mov eax, 1
ret
'''
    return s


def catalog_source(p):
    bad=p+'_false'
    return f'''{p}_catalog:
mov rbp, rdx
'''+ptr('rbp',bad,'rax')+f'''mov r8, qword ptr [rbp+0x128]
'''+ptr('r8',bad,'rax')+f'''mov ecx, dword ptr [rbp+0x130]
test ecx, ecx
je {bad}
cmp ecx, 4096
ja {bad}
mov r11d, ecx
shl r11, 3
'''+span('r8','r11',bad,limit='r10')+f'''
lea r9, [rsi+0x{SORT_OFFSET:X}]
xor r10d, r10d
{p}_catalog_scan:
'''+budget(bad)+f'''mov rdx, qword ptr [r8]
test rdx, rdx
je {p}_catalog_next
'''+ptr('rdx',bad,'rax')+f'''mov eax, dword ptr [rdx]
mov dword ptr [r9+r10*4], eax
inc r10d
{p}_catalog_next:
add r8, 8
dec ecx
jne {p}_catalog_scan
mov edx, r10d
lea rcx, [rsi+0x{SORT_OFFSET:X}]
jmp {p}_sort_unique
'''


def action_source(p):
    bad=p+'_action_bad'
    s=f'''{p}_action:
push rbp
push rbx
sub rsp, 0x28
mov rbp, rdx
mov ebx, eax
'''+ptr('rbp',bad,'rax')+f'''mov r8, qword ptr [rbp+0x128]
'''+ptr('r8',bad,'rax')+f'''mov ecx, dword ptr [rbp+0x130]
test ecx, ecx
je {bad}
cmp ecx, 4096
ja {bad}
xor r9d, r9d
xor r10d, r10d
{p}_action_scan:
'''+budget(bad)+f'''mov rdx, qword ptr [r8]
test rdx, rdx
je {p}_action_next
'''+ptr('rdx',bad,'rax')+f'''cmp dword ptr [rdx], ebx
jne {p}_action_next
test r9, r9
jne {bad}
mov r9, rdx
mov r10, r8
{p}_action_next:
add r8, 8
dec ecx
jne {p}_action_scan
test r9, r9
je {bad}
'''+span('r9','0x84',bad)+f'''
cmp byte ptr [r9+0x40], 1
jne {bad}
cmp qword ptr [r9+0x38], rbp
jne {bad}
mov qword ptr [rsi+0xA0], r9
mov qword ptr [rsi+0xB0], r10
'''+pin(p,'r9',0x41,bad)+f'''mov r9, qword ptr [rsi+0xA0]
mov rdx, qword ptr [r9+0x20]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0xA8], rdx
'''+pin(p,'rdx',0xA0,bad)+f'''mov r9, qword ptr [rsi+0xA0]
mov r8, qword ptr [r9+0x78]
'''+ptr('r8',bad,'rax')+f'''cmp qword ptr [rbp+0x50], r8
jne {bad}
movzx eax, word ptr [r9+0x80]
movzx edx, word ptr [r9+0x82]
test edx, edx
je {bad}
cmp edx, 512
ja {bad}
add eax, edx
movzx ecx, word ptr [rbp+0x5A]
cmp eax, ecx
ja {bad}
movzx eax, word ptr [rbp+0x58]
cmp ecx, eax
ja {bad}
lea rcx, [r9+0x78]
mov edx, 12
call {p}_pin
test eax, eax
je {bad}
mov r8, qword ptr [rbp+0x80]
'''+ptr('r8',bad,'rax')+f'''movzx ecx, word ptr [rbp+0x88]
test ecx, ecx
je {bad}
cmp ecx, 4096
ja {bad}
mov r10, qword ptr [rsi+0xA8]
add r10, 0x40
mov ebx, 16
{p}_action_refs:
movsx edx, word ptr [r10]
test edx, edx
js {p}_action_refs_next
movzx ecx, word ptr [rbp+0x88]
cmp edx, ecx
jae {bad}
mov rdx, qword ptr [r8+rdx*8]
'''+ptr('rdx',bad,'rax')+pin(p,'rdx',0x80,bad)+f'''{p}_action_refs_next:
add r10, 6
dec ebx
jne {p}_action_refs
mov eax, 1
jmp {p}_action_done
{bad}:
xor eax, eax
{p}_action_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def equipment_source(p):
    bad=p+'_equipment_bad'
    s=f'''{p}_equipment:
push rbp
push rbx
sub rsp, 0x28
mov rdx, qword ptr [rdi+0x88]
movzx ebx, byte ptr [rdx+0x9CC]
cmp ebx, 1
ja {bad}
mov dword ptr [rsi+0x30], ebx
mov rax, {{mission_temp_owner}}
mov rbp, qword ptr [rax]
'''+ptr('rbp',bad,'rax')+f'''mov qword ptr [rsi+0x28], rbp
mov qword ptr [rdi+0x1F0], rbp
'''+span('rbp','0xB52BC',bad)+f'''mov eax, dword ptr [rbp+0xB52B4]
cmp eax, 700
ja {bad}
mov edx, dword ptr [rbp+0xB52B8]
cmp edx, 700
ja {bad}
mov ecx, 1
sub ecx, ebx
mov eax, dword ptr [rbp+rcx*4+0xB52B4]
cmp eax, 700
jne {p}_equipment_slot
xor ecx, 1
mov eax, dword ptr [rbp+rcx*4+0xB52B4]
cmp eax, 700
je {bad}
{p}_equipment_slot:
mov dword ptr [rsi+0x34], ecx
mov dword ptr [rsi+0x38], eax
mov edx, eax
shl ebx, 10
or edx, ebx
shl ecx, 11
or edx, ecx
mov dword ptr [rdi+0x1FC], edx
imul rax, rax, 0xD0
add rax, rbp
add rax, 0x210
mov eax, dword ptr [rax]
test eax, eax
js {bad}
mov dword ptr [rsi+0x3C], eax
mov dword ptr [rdi+0x1F8], eax
mov rax, {{lw_item_hash_manager}}
mov rax, qword ptr [rax]
'''+ptr('rax',bad,'rcx')+f'''mov qword ptr [rsi+0x100], rax
mov rdx, qword ptr [rax+8]
'''+ptr('rdx',bad,'rcx')+f'''mov rcx, qword ptr [rax+0x10]
cmp rcx, rdx
jbe {bad}
sub rcx, rdx
test rcx, 7
jne {bad}
cmp rcx, 0x200000
ja {bad}
shr rcx, 3
mov r8d, dword ptr [rax+4]
mov eax, dword ptr [rsi+0x3C]
mov r9d, 262144
call {p}_hash
test eax, eax
je {bad}
mov ebx, dword ptr [rsi+0x110]
test ebx, ebx
js {bad}
mov rax, {{lw_item_database}}
mov rax, qword ptr [rax]
'''+ptr('rax',bad,'rcx')+f'''mov rax, qword ptr [rax+0x20]
'''+ptr('rax',bad,'rcx')+f'''mov rbp, qword ptr [rax+0x428]
'''+ptr('rbp',bad,'rax',4)+f'''mov eax, dword ptr [rbp+4]
test eax, eax
je {bad}
cmp eax, 262144
ja {bad}
cmp ebx, eax
jae {bad}
imul rbx, rbx, 0x130
add rbx, rbp
add rbx, 0xC
'''+span('rbx',1,bad)+f'''movzx ebx, byte ptr [rbx]
sub ebx, 9
cmp ebx, 6
ja {bad}
cmp ebx, 5
jb {p}_equipment_family_index
inc ebx
{p}_equipment_family_index:
mov rdx, {{lw_item_family_keys}}
mov rax, 0x0000000300000001
cmp qword ptr [rdx], rax
jne {bad}
mov rax, 0x0000000400000002
cmp qword ptr [rdx+8], rax
jne {bad}
mov rax, 0x0000000800000005
cmp qword ptr [rdx+0x10], rax
jne {bad}
mov rax, 0x0000000700000006
cmp qword ptr [rdx+0x18], rax
jne {bad}
mov eax, dword ptr [rdx+rbx*4]
mov dword ptr [rsi+0x40], eax
mov eax, 1
jmp {p}_equipment_done
{bad}:
xor eax, eax
{p}_equipment_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def package_source(p):
    bad=p+'_false'
    s=f'''{p}_package:
mov rax, {{loaded_package_tree}}
mov rdx, qword ptr [rax]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x48], rdx
mov rdx, qword ptr [rdx+8]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x58], rdx
mov r8, -1
mov r9, 0x100000000
mov ebx, dword ptr [rsi+0x40]
mov ebp, 64
{p}_package_tree:
'''+budget(bad)+ptr('rdx',bad,'rax')+f'''cmp byte ptr [rdx+0x19], 0
jne {bad}
mov eax, dword ptr [rdx+0x20]
cmp rax, r8
jle {bad}
cmp rax, r9
jge {bad}
cmp eax, ebx
je {p}_package_found
jb {p}_package_right
mov r9, rax
mov rdx, qword ptr [rdx]
jmp {p}_package_next
{p}_package_right:
mov r8, rax
mov rdx, qword ptr [rdx+0x10]
{p}_package_next:
dec ebp
jne {p}_package_tree
jmp {bad}
{p}_package_found:
mov qword ptr [rsi+0x60], rdx
mov rdx, qword ptr [rdx+0x28]
'''+ptr('rdx',bad,'rax')+f'''mov rax, {{weapon_package_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov qword ptr [rdi+0x20], rdx
mov rdx, qword ptr [rdx+0x1B8]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rdi+0x28], rdx
mov rdx, qword ptr [rdx+0x468]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rdi+0x30], rdx
mov r8, qword ptr [rdi+0x20]
'''
    for source,dest in ((0x188,0x38),(0x190,0x40),(0x198,0x48),(0x1A0,0x50)):
        s+=f'mov rdx, qword ptr [r8+0x{source:X}]\n'+ptr('rdx',bad,'rax')+f'mov qword ptr [rdi+0x{dest:X}], rdx\n'
    s+=f'''mov eax, 1
ret
'''
    return s


def hash_source(p):
    """Native integer hash/probe with whole-map uniqueness; pin exact hit."""
    bad=p+'_hash_bad'
    return f'''{p}_hash:
push rbx
push rbp
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0x28
mov ebx, eax
mov rbp, rdx
test ecx, ecx
je {bad}
cmp ecx, r9d
ja {bad}
cmp ecx, 262144
ja {bad}
'''+ptr('rbp',bad,'rax')+f'''mov r10d, ecx
shl r10, 3
'''+span('rbp','r10',bad)+f'''mov r9d, ecx
mov r10, rbp
xor r11d, r11d
{p}_hash_unique_scan:
'''+budget(bad)+f'''cmp dword ptr [r10], ebx
jne {p}_hash_unique_next
inc r11d
cmp r11d, 1
ja {bad}
{p}_hash_unique_next:
add r10, 8
dec r9d
jne {p}_hash_unique_scan
cmp r11d, 1
jne {bad}
lea eax, [rbx+rbx*8]
and eax, 0x7FFFFFFF
mov edx, eax
shr edx, 11
xor eax, edx
and eax, 0x7FFFFFFF
imul eax, eax, 0x8001
mov edx, ebx
shr edx, 16
add eax, edx
and eax, 0x7FFFFFFF
xor edx, edx
div ecx
mov r11d, edx
mov r9d, ecx
{p}_hash_probe:
'''+budget(bad)+f'''lea r10, [rbp+r11*8]
mov eax, dword ptr [r10]
cmp eax, ebx
je {p}_hash_hit
cmp eax, r8d
je {bad}
inc r11d
cmp r11d, ecx
jb {p}_hash_no_wrap
xor r11d, r11d
{p}_hash_no_wrap:
dec r9d
jne {p}_hash_probe
jmp {bad}
{p}_hash_hit:
mov eax, dword ptr [r10+4]
mov dword ptr [rsi+0x110], eax
mov qword ptr [rsi+0x118], r10
'''+pin(p,'r10',8,bad)+f'''mov eax, 1
jmp {p}_hash_done
{bad}:
xor eax, eax
{p}_hash_done:
add rsp, 0x28
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rbp
pop rbx
ret
'''


def sort_source(p):
    """In-place private max-heapsort; native arrays remain read-only."""
    bad=p+'_false'
    return f'''{p}_sort_unique:
test edx, edx
je {bad}
cmp edx, 4096
ja {bad}
mov r8, rcx
mov r9d, edx
mov r10d, edx
shr r10d, 1
mov r11d, edx
{p}_sort_build:
test r10d, r10d
je {p}_sort_extract
dec r10d
mov ebx, r10d
call {p}_sort_sift
test eax, eax
je {bad}
jmp {p}_sort_build
{p}_sort_extract:
cmp r11d, 1
jbe {p}_sort_check
dec r11d
mov eax, dword ptr [r8]
mov edx, dword ptr [r8+r11*4]
mov dword ptr [r8], edx
mov dword ptr [r8+r11*4], eax
xor ebx, ebx
call {p}_sort_sift
test eax, eax
je {bad}
jmp {p}_sort_extract
{p}_sort_check:
mov ecx, 1
{p}_sort_check_loop:
cmp ecx, r9d
jae {p}_sort_success
mov eax, dword ptr [r8+rcx*4-4]
cmp eax, dword ptr [r8+rcx*4]
je {bad}
inc ecx
jmp {p}_sort_check_loop
{p}_sort_success:
mov eax, 1
ret
{p}_sort_sift:
{p}_sort_sift_loop:
'''+budget(bad)+f'''lea ecx, [rbx+rbx+1]
cmp ecx, r11d
jae {p}_sort_sift_done
lea edx, [rcx+1]
cmp edx, r11d
jae {p}_sort_sift_selected
mov eax, dword ptr [r8+rdx*4]
cmp eax, dword ptr [r8+rcx*4]
jbe {p}_sort_sift_selected
mov ecx, edx
{p}_sort_sift_selected:
mov eax, dword ptr [r8+rcx*4]
mov edx, dword ptr [r8+rbx*4]
cmp eax, edx
jbe {p}_sort_sift_done
mov dword ptr [r8+rbx*4], eax
mov dword ptr [r8+rcx*4], edx
mov ebx, ecx
jmp {p}_sort_sift_loop
{p}_sort_sift_done:
mov eax, 1
ret
'''


def start_source(p):
    bad=p+'_start_bad'
    s=f'''{p}_start:
push rbp
push rbx
sub rsp, 0x28
mov dword ptr [rsi+0xC0], eax
mov rax, qword ptr [rdi+0x60]
movzx ebx, word ptr [rax+0x82]
movzx ecx, word ptr [rax+0x80]
mov rbp, qword ptr [rax+0x78]
lea rbp, [rbp+rcx*8]
mov qword ptr [rsi+0xC8], 0
{p}_start_branches:
'''+budget(bad)+f'''mov rdx, qword ptr [rbp]
'''+ptr('rdx',bad,'rax')+f'''cmp byte ptr [rdx+0xA], 0
jne {p}_start_branch_next
cmp word ptr [rdx+0xB], -1
jne {p}_start_branch_next
cmp byte ptr [rdx+0x17], 0
jne {p}_start_branch_next
cmp word ptr [rdx+8], -1
jne {p}_start_branch_next
cmp dword ptr [rsi+0xC0], 0
jne {p}_start_short_query
cmp qword ptr [rdx], -1
jne {p}_start_branch_next
jmp {p}_start_branch_found
{p}_start_short_query:
mov rax, 0xFFFFFFFFFFFF0059
cmp qword ptr [rdx], rax
jne {p}_start_branch_next
{p}_start_branch_found:
cmp qword ptr [rsi+0xC8], 0
jne {bad}
mov qword ptr [rsi+0xC8], rdx
{p}_start_branch_next:
add rbp, 8
dec ebx
jne {p}_start_branches
mov rdx, qword ptr [rsi+0xC8]
test rdx, rdx
je {bad}
'''+pin(p,'rdx',0x30,bad)+f'''mov rdx, qword ptr [rsi+0xC8]
movzx eax, word ptr [rdx+0x14]
mov dword ptr [rsi+0xCC], eax
mov rdx, qword ptr [rdi+0x30]
call {p}_action
test eax, eax
je {bad}
mov r8, qword ptr [rsi+0xA0]
mov r9, qword ptr [rsi+0xA8]
mov edx, dword ptr [rsi+0xC0]
lea eax, [rdx+9000]
cmp dword ptr [r9+0x20], eax
jne {bad}
cmp dword ptr [r9+0x34], -1
jne {bad}
mov eax, dword ptr [rsi+0xCC]
mov dword ptr [rdi+rdx*4+0x78], eax
mov qword ptr [rdi+rdx*8+0x68], r8
mov qword ptr [rdi+rdx*8+0x108], r9
mov rax, qword ptr [rsi+0xB0]
mov qword ptr [rdi+rdx*8+0x178], rax
mov qword ptr [rsi+0xC8], 0
movzx ebx, word ptr [r8+0x82]
movzx ecx, word ptr [r8+0x80]
mov rbp, qword ptr [r8+0x78]
lea rbp, [rbp+rcx*8]
{p}_start_terminals:
'''+budget(bad)+f'''mov rdx, qword ptr [rbp]
'''+ptr('rdx',bad,'rax')+f'''cmp byte ptr [rdx+0xA], 1
jne {p}_start_terminal_next
cmp qword ptr [rdx], -1
jne {p}_start_terminal_next
cmp word ptr [rdx+8], -1
jne {p}_start_terminal_next
cmp word ptr [rdx+0x14], 3000
jne {p}_start_terminal_next
cmp byte ptr [rdx+0x17], 0
jne {p}_start_terminal_next
cmp qword ptr [rsi+0xC8], 0
jne {bad}
mov qword ptr [rsi+0xC8], rdx
{p}_start_terminal_next:
add rbp, 8
dec ebx
jne {p}_start_terminals
mov rdx, qword ptr [rsi+0xC8]
test rdx, rdx
je {bad}
'''+pin(p,'rdx',0x30,bad)+f'''mov r8, qword ptr [rsi+0xA8]
add r8, 0x40
mov ebx, 16
xor ebp, ebp
{p}_start_schema:
movsx eax, word ptr [r8]
test eax, eax
js {p}_start_schema_next
cmp eax, 13
je {p}_start_ref13
cmp eax, 37
je {p}_start_ref37
cmp dword ptr [rsi+0xC0], 0
je {p}_start_long_schema
cmp eax, 34
jne {bad}
cmp word ptr [r8+2], 0
jne {bad}
mov edx, 1
jmp {p}_start_schema_set
{p}_start_long_schema:
cmp eax, 12
je {p}_start_long_init
cmp eax, 35
jne {bad}
cmp word ptr [r8+2], 65
jne {bad}
mov edx, 8
jmp {p}_start_schema_set
{p}_start_long_init:
cmp word ptr [r8+2], 0
jne {bad}
mov edx, 1
jmp {p}_start_schema_set
{p}_start_ref13:
mov eax, 130
cmp dword ptr [rsi+0xC0], 0
je {p}_start_ref13_check
mov eax, 45
{p}_start_ref13_check:
cmp word ptr [r8+2], ax
jne {bad}
mov edx, 2
jmp {p}_start_schema_set
{p}_start_ref37:
mov eax, 171
cmp dword ptr [rsi+0xC0], 0
je {p}_start_ref37_check
mov eax, 10
{p}_start_ref37_check:
cmp word ptr [r8+2], ax
jne {bad}
mov edx, 4
{p}_start_schema_set:
test ebp, edx
jne {bad}
or ebp, edx
{p}_start_schema_next:
add r8, 6
dec ebx
jne {p}_start_schema
mov eax, 15
cmp dword ptr [rsi+0xC0], 0
je {p}_start_schema_mask
mov eax, 7
{p}_start_schema_mask:
cmp ebp, eax
jne {bad}
mov rax, qword ptr [rdi+0x30]
mov rax, qword ptr [rax+0x80]
mov edx, 12
mov ecx, 1503
cmp dword ptr [rsi+0xC0], 0
je {p}_start_init_descriptor
mov edx, 34
mov ecx, 1504
{p}_start_init_descriptor:
mov rdx, qword ptr [rax+rdx*8]
'''+ptr('rdx',bad,'rax')+f'''cmp byte ptr [rdx+0x16], 1
jne {bad}
cmp byte ptr [rdx+0x17], 7
jne {bad}
cmp word ptr [rdx+0x52], cx
jne {bad}
mov eax, 1
jmp {p}_start_done
{bad}:
xor eax, eax
{p}_start_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def motion_source(p):
    bad=p+'_motion_bad'
    s=f'''{p}_motion:
push rbp
push rbx
sub rsp, 0x28
mov dword ptr [rsi+0x120], eax
mov rdx, qword ptr [rdi+rax*8+0x38]
mov qword ptr [rsi+0x128], rdx
mov rax, {{motion_resource_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov r8, qword ptr [rdx+0x468]
'''+ptr('r8',bad,'rax')+f'''mov r9, qword ptr [rdx+0x470]
'''+ptr('r9',bad,'rax')+f'''cmp r9, r8
jbe {bad}
mov rax, r9
sub rax, r8
test rax, 7
jne {bad}
cmp rax, 0x80000
ja {bad}
mov qword ptr [rsi+0x130], r8
mov qword ptr [rsi+0x138], r9
mov rdx, qword ptr [rdx+0x480]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x140], rdx
mov ecx, dword ptr [rdx+8]
test ecx, ecx
je {bad}
cmp ecx, 65536
ja {bad}
mov dword ptr [rsi+0x148], ecx
mov rdx, qword ptr [rdx+0x10]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x150], rdx
xor ebp, ebp
{p}_motion_id:
mov rdx, qword ptr [rsi+0x150]
mov ecx, dword ptr [rsi+0x148]
lea eax, [rbp+9000]
mov r8d, -1
mov r9d, 65536
call {p}_hash
test eax, eax
je {bad}
mov eax, dword ptr [rsi+0x110]
test eax, eax
js {bad}
mov r8, qword ptr [rsi+0x130]
lea rbx, [r8+rax*8]
cmp rbx, qword ptr [rsi+0x138]
jae {bad}
mov rdx, qword ptr [rbx]
'''+ptr('rdx',bad,'rax')+f'''cmp dword ptr [rdx+0x18], 0x42700000
jne {bad}
mov eax, dword ptr [rdx+0x1C]
sub eax, 1
cmp eax, 4095
ja {bad}
mov r8d, dword ptr [rsi+0x120]
shl r8d, 1
add r8d, ebp
mov qword ptr [rdi+r8*8+0x128], rbx
mov qword ptr [rdi+r8*8+0x148], rdx
mov rax, qword ptr [rsi+0x118]
mov qword ptr [rdi+r8*8+0x1D0], rax
'''+pin(p,'rdx',0x30,bad)+f'''cmp dword ptr [rsi+0x120], 0
je {p}_motion_next
mov rax, qword ptr [rdi+rbp*8+0x148]
mov rdx, qword ptr [rdi+rbp*8+0x158]
mov eax, dword ptr [rax+0x1C]
cmp eax, dword ptr [rdx+0x1C]
jne {bad}
{p}_motion_next:
inc ebp
cmp ebp, 2
jb {p}_motion_id
mov ecx, dword ptr [rsi+0x120]
mov rax, qword ptr [rsi+0x140]
mov qword ptr [rdi+rcx*8+0xA8], rax
mov eax, dword ptr [rsi+0x148]
mov dword ptr [rdi+rcx*4+0xE0], eax
mov rax, qword ptr [rsi+0x150]
mov qword ptr [rdi+rcx*8+0x1B0], rax
shl ecx, 1
mov rax, qword ptr [rsi+0x130]
mov qword ptr [rdi+rcx*8+0xE8], rax
mov rax, qword ptr [rsi+0x138]
mov qword ptr [rdi+rcx*8+0xF0], rax
mov eax, 1
jmp {p}_motion_done
{bad}:
xor eax, eax
{p}_motion_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def events_source(p):
    bad=p+'_events_bad'
    s=f'''{p}_events:
push rbp
push rbx
sub rsp, 0x28
mov dword ptr [rsi+0x120], eax
mov rdx, qword ptr [rdi+rax*8+0x48]
mov rax, {{weapon_event_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov rdx, qword ptr [rdx+0x468]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x130], rdx
mov r8, qword ptr [rdx]
'''+ptr('r8',bad,'rax')+f'''mov qword ptr [rsi+0x138], r8
mov rax, 0x4B4341505F474D54
cmp qword ptr [r8], rax
jne {bad}
mov eax, dword ptr [r8+0x10]
cmp eax, 0x30
jb {bad}
cmp eax, 0x100000
ja {bad}
mov dword ptr [rsi+0x140], eax
'''+span('r8','rax',bad,scratch='rdx',limit='r11')+f'''
mov ecx, dword ptr [r8+0x14]
test ecx, ecx
je {bad}
cmp ecx, 4096
ja {bad}
mov dword ptr [rsi+0x144], ecx
mov ebx, dword ptr [r8+0x20]
cmp ebx, 0x30
jb {bad}
mov dword ptr [rsi+0x148], ebx
lea ebx, [rbx+rcx*4]
cmp ebx, eax
ja {bad}
mov rdx, qword ptr [rsi+0x130]
mov rdx, qword ptr [rdx+8]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x150], rdx
mov ecx, dword ptr [rdx+8]
test ecx, ecx
je {bad}
cmp ecx, 65536
ja {bad}
mov dword ptr [rsi+0x158], ecx
mov rdx, qword ptr [rdx+0x10]
'''+ptr('rdx',bad,'rax')+f'''mov qword ptr [rsi+0x160], rdx
mov r8, qword ptr [rsi+0x138]
mov eax, dword ptr [rsi+0x148]
add r8, rax
mov ecx, dword ptr [rsi+0x144]
lea r9, [rsi+0x{SORT_OFFSET:X}]
{p}_events_offsets:
'''+budget(bad)+f'''mov eax, dword ptr [r8]
cmp eax, 0x30
jb {bad}
cmp eax, dword ptr [rsi+0x140]
jae {bad}
mov dword ptr [r9], eax
add r8, 4
add r9, 4
dec ecx
jne {p}_events_offsets
lea rcx, [rsi+0x{SORT_OFFSET:X}]
mov edx, dword ptr [rsi+0x144]
call {p}_sort_unique
test eax, eax
je {bad}
mov rdx, qword ptr [rsi+0x138]
'''+pin(p,'rdx',0x30,bad)+f'''xor ebp, ebp
{p}_events_id:
mov rdx, qword ptr [rsi+0x160]
mov ecx, dword ptr [rsi+0x158]
lea eax, [rbp+9000]
mov r8d, -1
mov r9d, 65536
call {p}_hash
test eax, eax
je {bad}
mov eax, dword ptr [rsi+0x110]
cmp eax, dword ptr [rsi+0x144]
jae {bad}
mov r8, qword ptr [rsi+0x138]
mov ecx, dword ptr [rsi+0x148]
add r8, rcx
lea rdx, [r8+rax*4]
mov qword ptr [rsi+0x190], rdx
'''+pin(p,'rdx',4,bad)+f'''mov rdx, qword ptr [rsi+0x190]
mov eax, dword ptr [rdx]
mov dword ptr [rsi+0x170], eax
cmp eax, 0x30
jb {bad}
cmp eax, dword ptr [rsi+0x140]
jae {bad}
mov ebx, dword ptr [rsi+0x140]
mov ecx, dword ptr [rsi+0x144]
{p}_events_span:
'''+budget(bad)+f'''mov edx, dword ptr [r8]
cmp edx, eax
jbe {p}_events_span_next
cmp edx, ebx
jae {p}_events_span_next
mov ebx, edx
{p}_events_span_next:
add r8, 4
dec ecx
jne {p}_events_span
sub ebx, eax
cmp ebx, 0x24
jb {bad}
cmp ebx, 0x10000
ja {bad}
mov r8, qword ptr [rsi+0x138]
add r8, rax
mov qword ptr [rsi+0x178], r8
mov ecx, dword ptr [r8+4]
test ecx, ecx
je {bad}
cmp ecx, 1024
ja {bad}
mov dword ptr [rsi+0x180], ecx
mov eax, dword ptr [r8+8]
cmp eax, 0x24
jb {bad}
cmp eax, ebx
ja {bad}
mov edx, ecx
imul edx, edx, 12
sub ebx, eax
cmp edx, ebx
ja {bad}
add r8, rax
mov qword ptr [rsi+0x188], r8
mov rdx, qword ptr [rsi+0x178]
'''+pin(p,'rdx',0x24,bad)+f'''mov edx, dword ptr [rsi+0x120]
shl edx, 1
add edx, ebp
shl edx, 4
mov r8, qword ptr [rsi+0x188]
mov qword ptr [rsi+rdx+0x1C0], r8
mov eax, dword ptr [rsi+0x180]
mov dword ptr [rsi+rdx+0x1C8], eax
cmp dword ptr [rsi+0x120], 0
je {p}_events_count_ok
mov edx, ebp
shl edx, 4
cmp eax, dword ptr [rsi+rdx+0x1C8]
jne {bad}
{p}_events_count_ok:
lea r9, [rsi+0x{LONG_SCHEDULE:X}]
test ebp, ebp
je {p}_events_buffer
lea r9, [rsi+0x{SHORT_SCHEDULE:X}]
{p}_events_buffer:
mov ecx, dword ptr [rsi+0x180]
xor r10d, r10d
{p}_events_schedule:
'''+budget(bad)+f'''mov eax, dword ptr [r8]
cmp eax, 65535
ja {bad}
cmp eax, r10d
jb {bad}
mov r10d, eax
cmp dword ptr [rsi+8], 1
jne {p}_events_compare_triple
cmp dword ptr [rsi+0x120], 0
jne {p}_events_compare_triple
mov rax, qword ptr [r8]
mov qword ptr [r9], rax
mov eax, dword ptr [r8+8]
mov dword ptr [r9+8], eax
jmp {p}_events_schedule_next
{p}_events_compare_triple:
mov rax, qword ptr [r8]
cmp rax, qword ptr [r9]
jne {bad}
mov eax, dword ptr [r8+8]
cmp eax, dword ptr [r9+8]
jne {bad}
{p}_events_schedule_next:
add r8, 12
add r9, 12
dec ecx
jne {p}_events_schedule
inc ebp
cmp ebp, 2
jb {p}_events_id
mov ecx, dword ptr [rsi+0x120]
mov rax, qword ptr [rsi+0x130]
mov qword ptr [rdi+rcx*8+0x98], rax
mov rax, qword ptr [rsi+0x138]
mov qword ptr [rdi+rcx*8+0xB8], rax
mov rax, qword ptr [rsi+0x150]
mov qword ptr [rdi+rcx*8+0xC8], rax
mov eax, dword ptr [rsi+0x158]
mov dword ptr [rdi+rcx*4+0xD8], eax
mov rax, qword ptr [rsi+0x160]
mov qword ptr [rdi+rcx*8+0x1C0], rax
mov eax, 1
jmp {p}_events_done
{bad}:
xor eax, eax
{p}_events_done:
add rsp, 0x28
pop rbx
pop rbp
ret
'''
    return s


def pin_source(p):
    """Two-pass exact semantic reads; address includes width tag in high byte.

    RCX address/RDX byte length1..256. Only those bytes are read, including
    non-qword tails. All GPRs except RAX are preserved inside this helper.
    """
    bad=p+'_pin_bad'
    s=f'''{p}_pin:
push rbx
push rcx
push rdx
push r8
push r9
push r10
push r11
test edx, edx
je {bad}
cmp edx, 0x100
ja {bad}
'''+ptr('rcx',bad,'rax',1)+f'''mov r8, rcx
add r8, rdx
jc {bad}
mov rax, 0x800000000000
cmp r8, rax
jae {bad}
{p}_pin_chunk:
'''+budget(bad)+f'''mov r11d, 8
cmp edx, 8
jae {p}_pin_read8
mov r11d, 4
cmp edx, 4
jae {p}_pin_read4
mov r11d, 2
cmp edx, 2
jae {p}_pin_read2
mov r11d, 1
movzx ebx, byte ptr [rcx]
jmp {p}_pin_read_done
{p}_pin_read2:
movzx ebx, word ptr [rcx]
jmp {p}_pin_read_done
{p}_pin_read4:
mov ebx, dword ptr [rcx]
jmp {p}_pin_read_done
{p}_pin_read8:
mov rbx, qword ptr [rcx]
{p}_pin_read_done:
mov r10, r11
shl r10, 56
or r10, rcx
cmp dword ptr [rsi+8], 1
jne {p}_pin_compare
mov eax, dword ptr [rsi+0x50]
cmp eax, {(JOURNAL_END-JOURNAL_FIRST)//16}
jae {bad}
shl eax, 4
lea r9, [rsi+rax+0x{JOURNAL_FIRST:X}]
mov qword ptr [r9], r10
mov qword ptr [r9+8], rbx
inc dword ptr [rsi+0x50]
jmp {p}_pin_next
{p}_pin_compare:
mov eax, dword ptr [rsi+0x54]
cmp eax, dword ptr [rsi+0x50]
jae {bad}
shl eax, 4
lea r9, [rsi+rax+0x{JOURNAL_FIRST:X}]
cmp qword ptr [r9], r10
jne {bad}
cmp qword ptr [r9+8], rbx
jne {bad}
inc dword ptr [rsi+0x54]
{p}_pin_next:
add rcx, r11
sub edx, r11d
jne {p}_pin_chunk
mov eax, 1
jmp {p}_pin_done
{bad}:
xor eax, eax
{p}_pin_done:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rbx
ret
{p}_replay:
mov ecx, dword ptr [rsi+0x50]
cmp ecx, {(JOURNAL_END-JOURNAL_FIRST)//16}
ja {p}_false
lea r8, [rsi+0x{JOURNAL_FIRST:X}]
{p}_replay_chunk:
test ecx, ecx
je {p}_replay_schedules
'''+budget(p+'_false')+f'''mov rdx, qword ptr [r8]
mov r9, rdx
shr r9, 56
mov rax, 0x00FFFFFFFFFFFFFF
and rdx, rax
'''+ptr('rdx',p+'_false','rax',1)+f'''cmp r9d, 8
je {p}_replay_read8
cmp r9d, 4
je {p}_replay_read4
cmp r9d, 2
je {p}_replay_read2
cmp r9d, 1
jne {p}_false
movzx eax, byte ptr [rdx]
jmp {p}_replay_compare
{p}_replay_read2:
movzx eax, word ptr [rdx]
jmp {p}_replay_compare
{p}_replay_read4:
mov eax, dword ptr [rdx]
jmp {p}_replay_compare
{p}_replay_read8:
mov rax, qword ptr [rdx]
{p}_replay_compare:
cmp rax, qword ptr [r8+8]
jne {p}_false
add r8, 16
dec ecx
jmp {p}_replay_chunk
{p}_replay_schedules:
xor ebp, ebp
{p}_replay_schedule_side:
mov eax, ebp
shl eax, 4
mov r8, qword ptr [rsi+rax+0x1C0]
'''+ptr('r8',p+'_false','rax',4)+f'''mov eax, ebp
shl eax, 4
mov ecx, dword ptr [rsi+rax+0x1C8]
test ecx, ecx
je {p}_false
cmp ecx, 1024
ja {p}_false
lea r9, [rsi+0x{LONG_SCHEDULE:X}]
test ebp, 1
je {p}_replay_schedule_triple
lea r9, [rsi+0x{SHORT_SCHEDULE:X}]
{p}_replay_schedule_triple:
'''+budget(p+'_false')+f'''mov rax, qword ptr [r8]
cmp rax, qword ptr [r9]
jne {p}_false
mov eax, dword ptr [r8+8]
cmp eax, dword ptr [r9+8]
jne {p}_false
add r8, 12
add r9, 12
dec ecx
jne {p}_replay_schedule_triple
inc ebp
cmp ebp, 4
jb {p}_replay_schedule_side
mov eax, 1
ret
'''
    return s


def roots_source(p):
    bad=p+'_false'
    s=f'''{p}_roots:
mov rax, {{player_slot}}
cmp qword ptr [rax], r12
jne {bad}
cmp qword ptr [r14+0x10], r12
jne {bad}
mov eax, dword ptr [r14+0x1C]
cmp eax, dword ptr [rdi+4]
jne {bad}
mov rax, qword ptr [r12]
cmp rax, qword ptr [rdi+0x90]
jne {bad}
cmp qword ptr [r12+0x240], 0
je {bad}
mov rax, qword ptr [r12+0x240]
cmp rax, qword ptr [rdi+0x88]
jne {bad}
movzx ecx, byte ptr [rax+0x9CC]
cmp ecx, dword ptr [rsi+0x30]
jne {bad}
mov rax, qword ptr [r12+0x230]
'''+ptr('rax',bad,'rcx')+f'''cmp qword ptr [rax], r12
jne {bad}
cmp qword ptr [rax+8], r13
jne {bad}
cmp qword ptr [r13+0x50], r12
jne {bad}
mov rax, qword ptr [r13+0x58]
cmp rax, qword ptr [rdi+0x58]
jne {bad}
mov rax, {{mission_temp_owner}}
mov rdx, qword ptr [rdi+0x1F0]
cmp qword ptr [rax], rdx
jne {bad}
mov ecx, dword ptr [rsi+0x34]
mov eax, dword ptr [rsi+0x38]
cmp dword ptr [rdx+rcx*4+0xB52B4], eax
jne {bad}
imul rax, rax, 0xD0
mov ecx, dword ptr [rdi+0x1F8]
cmp dword ptr [rdx+rax+0x210], ecx
jne {bad}
mov rax, {{loaded_package_tree}}
mov rdx, qword ptr [rsi+0x48]
cmp qword ptr [rax], rdx
jne {bad}
mov rax, qword ptr [rdx+8]
cmp rax, qword ptr [rsi+0x58]
jne {bad}
mov rdx, qword ptr [rsi+0x60]
'''+ptr('rdx',bad,'rax')+f'''cmp byte ptr [rdx+0x19], 0
jne {bad}
mov eax, dword ptr [rsi+0x40]
cmp dword ptr [rdx+0x20], eax
jne {bad}
mov rax, qword ptr [rdx+0x28]
cmp rax, qword ptr [rdi+0x20]
jne {bad}
mov r8, rax
mov rax, {{weapon_package_vtable}}
cmp qword ptr [r8], rax
jne {bad}
mov rax, qword ptr [r8+0x1B8]
cmp rax, qword ptr [rdi+0x28]
jne {bad}
mov rax, qword ptr [rax+0x468]
cmp rax, qword ptr [rdi+0x30]
jne {bad}
'''
    for native,field in ((0x188,0x38),(0x190,0x40),(0x198,0x48),(0x1A0,0x50)):
        s+=f'''mov rax, qword ptr [r8+0x{native:X}]
cmp rax, qword ptr [rdi+0x{field:X}]
jne {bad}
'''
    for side in range(2):
        motion=0x38+side*8; mp=0xA8+side*8; mt=0x1B0+side*8
        vec=0xE8+side*16; end=0xF0+side*16; cap=0xE0+side*4
        s+=f'''mov r8, qword ptr [rdi+0x{motion:X}]
mov rax, qword ptr [rdi+0x{vec:X}]
cmp qword ptr [r8+0x468], rax
jne {bad}
mov rax, qword ptr [rdi+0x{end:X}]
cmp qword ptr [r8+0x470], rax
jne {bad}
mov rax, qword ptr [rdi+0x{mp:X}]
cmp qword ptr [r8+0x480], rax
jne {bad}
mov ecx, dword ptr [rdi+0x{cap:X}]
cmp dword ptr [rax+8], ecx
jne {bad}
mov rcx, qword ptr [rdi+0x{mt:X}]
cmp qword ptr [rax+0x10], rcx
jne {bad}
'''
        for family in range(2):
            index=side*2+family
            entry=0x1D0+index*8;slot=0x128+index*8;clip=0x148+index*8
            s+=f'''mov rax, qword ptr [rdi+0x{entry:X}]
cmp dword ptr [rax], {9000+family}
jne {bad}
mov eax, dword ptr [rax+4]
test eax, eax
js {bad}
mov rcx, qword ptr [rdi+0x{vec:X}]
lea rcx, [rcx+rax*8]
cmp rcx, qword ptr [rdi+0x{slot:X}]
jne {bad}
mov rax, qword ptr [rdi+0x{clip:X}]
cmp qword ptr [rcx], rax
jne {bad}
'''
        ew=0x48+side*8;eo=0x98+side*8;eh=0xB8+side*8
        em=0xC8+side*8;ec=0xD8+side*4;et=0x1C0+side*8
        s+=f'''mov r8, qword ptr [rdi+0x{ew:X}]
mov rax, qword ptr [rdi+0x{eo:X}]
cmp qword ptr [r8+0x468], rax
jne {bad}
mov rcx, qword ptr [rdi+0x{eh:X}]
cmp qword ptr [rax], rcx
jne {bad}
mov rcx, qword ptr [rdi+0x{em:X}]
cmp qword ptr [rax+8], rcx
jne {bad}
mov eax, dword ptr [rdi+0x{ec:X}]
cmp dword ptr [rcx+8], eax
jne {bad}
mov rax, qword ptr [rdi+0x{et:X}]
cmp qword ptr [rcx+0x10], rax
jne {bad}
'''
    s+=f'''mov rax, qword ptr [r12+0x38]
cmp rax, qword ptr [rdi+0x80]
jne {bad}
mov rax, qword ptr [r12+0x68]
cmp rax, qword ptr [rdi+0x1A0]
jne {bad}
mov rax, qword ptr [rax+0x40]
cmp rax, qword ptr [rdi+0x1A8]
jne {bad}
mov eax, 1
ret
'''
    return s
