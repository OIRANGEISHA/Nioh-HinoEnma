"""Bounded discovery for the native C9AAF Nine Tails execution chain.

Only the private 512-byte binding is written. Native input, query474/381,
pairing, damage and mission handling remain authoritative. An active binding
is never rediscovered; a changed player generation invalidates private state.
"""
from hinoenma_orochi_binding import pointer


BIND_SIZE = 0x200
TEMPLATE = 0xC9AAF
READY_ACTION, READY_MOTION = 3174, 31001
WINDUP_ACTION, PAIRED_ACTION = 4026, 1273
WINDUP_MOTION, PAIRED_MOTION = 1210, 1211
TARGET_PAIRED_ACTION, TARGET_PAIRED_MOTION = 1274, 31010


def bootstrap(prefix='np_od', original_label='np_oh_original'):
    """Discover loaded owners on the saved original heavy-lookup frame.

    The caller owns SAVE/RESTORE. The runtime converts the two private MOV
    tokens to its separate core and Nine Tails data locations. All helpers
    call local labels, bound their loops and return zero on rejected data.
    """
    p, bad = prefix, original_label
    invalid = p+'_invalidate'
    s = f'''mov r11, {{ninetails_data}}
mov r9, {{production_data}}
mov r10, qword ptr [r9+0x10]
'''+pointer('r10', invalid)+f'''mov rax, {{player_slot}}
cmp r10, qword ptr [rax]
jne {invalid}
cmp dword ptr [r10], 0x58E5E
jne {invalid}
cmp dword ptr [r11], 0x4643524F
jne {p}_discover
mov eax, dword ptr [r9+0x1C]
cmp eax, dword ptr [r11+4]
jne {invalid}
cmp r10, qword ptr [r11+8]
jne {invalid}
mov rax, qword ptr [r10]
cmp rax, qword ptr [r11+0xA0]
jne {invalid}
cmp dword ptr [r11+0x74], 1
je {p}_done
cmp dword ptr [r11+0x74], 0
jne {invalid}
{p}_discover:
cmp dword ptr [r11+0x74], 0
jne {invalid}
mov dword ptr [r11], 0
cmp dword ptr [r10+0xEF0], 0
jne {bad}
cmp word ptr [r9+0x28], 0
jne {bad}
mov rdx, qword ptr [r10+0x240]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r10
jne {bad}
cmp qword ptr [rdx+0x20], 0
jle {bad}
mov rdx, qword ptr [r10+0x230]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r10
jne {bad}
mov r8, qword ptr [rdx+8]
'''+pointer('r8', bad)+f'''cmp r8, qword ptr [rsp+0xC0]
jne {bad}
cmp qword ptr [r8+0x50], r10
jne {bad}
cmp qword ptr [r8+0x5B0], 0
jne {bad}
cmp qword ptr [r8+0x5D8], 0
jne {bad}
cmp qword ptr [r8+0x510], 0
jne {bad}
mov rdx, qword ptr [r8+0x58]
'''+pointer('rdx', bad)+f'''cmp rdx, qword ptr [rsp+0xB8]
jne {bad}
cmp dword ptr [rdx], 0
jne {bad}
cmp byte ptr [rdx+0x40], 1
jne {bad}
mov rax, qword ptr [rdx+0x38]
cmp rax, qword ptr [r8+0x70]
je {p}_idle_owned
cmp rax, qword ptr [r8+0x78]
je {p}_idle_owned
cmp rax, qword ptr [r8+0x80]
jne {bad}
{p}_idle_owned:
mov qword ptr [r11+8], r10
mov qword ptr [r11+0x10], r8
mov qword ptr [r11+0x58], rdx
mov rax, qword ptr [r10]
mov qword ptr [r11+0xA0], rax
mov eax, dword ptr [r9+0x1C]
test eax, eax
je {bad}
mov dword ptr [r11+4], eax
mov r9, qword ptr [r8+0x640]
'''+pointer('r9', bad)+f'''cmp dword ptr [r9], 0xC9AAF
jne {bad}
mov qword ptr [r11+0x18], r9
mov rax, qword ptr [r9]
mov qword ptr [r11+0x20], rax
mov rdx, qword ptr [r9+0x230]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r9
jne {bad}
mov r8, qword ptr [rdx+8]
'''+pointer('r8', bad)+f'''cmp qword ptr [r8+0x50], r9
jne {bad}
cmp qword ptr [r8+0x5B0], 0
jne {bad}
cmp qword ptr [r8+0x5D8], 0
jne {bad}
mov qword ptr [r11+0xA8], r8
mov rdx, qword ptr [r8+0x58]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx], 3174
jne {bad}
cmp byte ptr [rdx+0x40], 1
jne {bad}
mov qword ptr [r11+0x180], rdx
mov rax, qword ptr [rdx+0x38]
'''+pointer('rax', bad, 'rcx')+f'''cmp rax, qword ptr [r8+0x70]
je {p}_ready_owned
cmp rax, qword ptr [r8+0x78]
je {p}_ready_owned
cmp rax, qword ptr [r8+0x80]
jne {bad}
{p}_ready_owned:
mov qword ptr [r11+0x188], rax
mov dword ptr [r11+0x118], 3174
mov rdx, qword ptr [rdx+0x20]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x20], 31001
jne {bad}
test byte ptr [rdx+0x19], 1
je {bad}
mov rdx, qword ptr [r9+0xE90]
'''+pointer('rdx', bad, alignment=4)+f'''cmp dword ptr [rdx], 0xC9AAF
jne {bad}
cmp dword ptr [rdx+0xC], 1
jne {bad}
mov rdx, qword ptr [r9+0x240]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r9
jne {bad}
cmp qword ptr [rdx+0x20], 1
jne {bad}
mov qword ptr [r11+0x128], rdx
mov rdx, qword ptr [r11+0x188]
mov eax, 1274
call {p}_action
test rax, rax
je {bad}
mov rdx, qword ptr [rax+0x20]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x20], 31010
jne {bad}
mov rdx, {{loaded_package_tree}}
mov rdx, qword ptr [rdx]
'''+pointer('rdx', bad)+f'''mov rdx, qword ptr [rdx+8]
mov ecx, 64
{p}_tree:
'''+pointer('rdx', bad)+f'''cmp byte ptr [rdx+0x19], 0
jne {bad}
cmp dword ptr [rdx+0x20], 1
je {p}_package
jb {p}_tree_right
mov rdx, qword ptr [rdx]
jmp {p}_tree_next
{p}_tree_right:
mov rdx, qword ptr [rdx+0x10]
{p}_tree_next:
dec ecx
jne {p}_tree
jmp {bad}
{p}_package:
mov rdx, qword ptr [rdx+0x28]
'''+pointer('rdx', bad)+f'''mov rax, {{weapon_package_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov qword ptr [r11+0x28], rdx
mov rdx, qword ptr [rdx+0x1B8]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x30], rdx
mov rdx, qword ptr [rdx+0x468]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x38], rdx
'''
    for ident, off in ((3008, 0x60), (4026, 0x68), (1273, 0x1A8)):
        s += f'''mov rdx, qword ptr [r11+0x38]
mov eax, {ident}
call {p}_action
test rax, rax
je {bad}
mov qword ptr [r11+{off:#x}], rax
'''
    for off, motion in ((0x68, 1210), (0x1A8, 1211)):
        s += f'''mov rdx, qword ptr [r11+{off:#x}]
mov rdx, qword ptr [rdx+0x20]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x20], {motion}
jne {bad}
cmp dword ptr [rdx+0x34], -1
jne {bad}
'''
    s += f'''mov r8, qword ptr [r11+0x10]
mov rdx, qword ptr [r8+0x80]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x90], rdx
xor eax, eax
call {p}_action
test rax, rax
je {bad}
mov qword ptr [r11+0x1F0], rax
'''
    for off, kind in ((0x1F0, 0), (0x60, 1), (0x68, 2), (0x1A8, 3)):
        s += f'''mov rdx, qword ptr [r11+{off:#x}]
mov eax, {kind}
call {p}_transition
test rax, rax
je {bad}
'''
        if kind == 0:
            s += 'mov qword ptr [r11+0x50], rax\n'
    for pkg_off, off in ((0x188, 0x40), (0x190, 0x48)):
        s += f'''mov rdx, qword ptr [r11+0x28]
mov rdx, qword ptr [rdx+{pkg_off:#x}]
mov qword ptr [r11+{off:#x}], rdx
call {p}_motion
test eax, eax
je {bad}
'''
    for pkg_off, pair_count, offsets in (
            (0x198, 56, (0xB8, 0xC8, 0xD8, 0xE8, 0xF8, 0x1B0, 0x108)),
            (0x1A0, 48, (0xC0, 0xD0, 0xE0, 0xF0, 0x100, 0x1B8, 0x10C))):
        s += f'''mov rdx, qword ptr [r11+0x28]
mov rdx, qword ptr [rdx+{pkg_off:#x}]
mov qword ptr [r11+{offsets[0]:#x}], rdx
mov ecx, {pair_count}
call {p}_events
test eax, eax
je {bad}
'''
        for dest, source in zip(offsets[1:6], (0x140, 0x148, 0x150, 0x158, 0x160)):
            s += f'mov rax, qword ptr [r11+{source:#x}]\nmov qword ptr [r11+{dest:#x}], rax\n'
        s += f'mov eax, dword ptr [r11+0x168]\nmov dword ptr [r11+{offsets[6]:#x}], eax\n'
    s += f'''mov r10, qword ptr [r11+8]
mov rdx, qword ptr [r10+0x68]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx+8], r10
jne {bad}
mov qword ptr [r11+0xB0], rdx
mov rdx, qword ptr [rdx+0x40]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx+8], r10
jne {bad}
cmp dword ptr [rdx+0x18], 0
jne {bad}
mov qword ptr [r11+0x1A0], rdx
mov r9, {{production_data}}
mov eax, dword ptr [r9+0x1C]
cmp eax, dword ptr [r11+4]
jne {bad}
cmp qword ptr [r9+0x10], r10
jne {bad}
mov rax, {{player_slot}}
cmp qword ptr [rax], r10
jne {bad}
mov rax, qword ptr [r10]
cmp rax, qword ptr [r11+0xA0]
jne {bad}
mov rdx, qword ptr [r10+0x230]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r10
jne {bad}
mov r8, qword ptr [r11+0x10]
cmp qword ptr [rdx+8], r8
jne {bad}
cmp qword ptr [r8+0x50], r10
jne {bad}
mov rax, qword ptr [r11+0x58]
cmp qword ptr [r8+0x58], rax
jne {bad}
cmp qword ptr [r8+0x5B0], 0
jne {bad}
cmp qword ptr [r8+0x5D8], 0
jne {bad}
cmp qword ptr [r8+0x510], 0
jne {bad}
mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x640], r9
jne {bad}
mov rax, qword ptr [r11+0x20]
cmp qword ptr [r9], rax
jne {bad}
mov rdx, qword ptr [r9+0x230]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r9
jne {bad}
mov r8, qword ptr [r11+0xA8]
cmp qword ptr [rdx+8], r8
jne {bad}
cmp qword ptr [r8+0x50], r9
jne {bad}
mov rax, qword ptr [r11+0x180]
cmp qword ptr [r8+0x58], rax
jne {bad}
mov rax, qword ptr [rax+0x20]
'''+pointer('rax', bad, 'rdx')+f'''test byte ptr [rax+0x19], 1
je {bad}
cmp dword ptr [rax+0x20], 31001
jne {bad}
mov rax, qword ptr [r11+0x128]
cmp qword ptr [r9+0x240], rax
jne {bad}
cmp qword ptr [rax], r9
jne {bad}
cmp qword ptr [rax+0x20], 1
jne {bad}
mov dword ptr [r11+0x1C0], 56
mov dword ptr [r11+0x1C4], 38
mov dword ptr [r11], 0x4643524F
jmp {p}_done
{invalid}:
mov dword ptr [r11], 0
mov dword ptr [r11+0x74], 0
jmp {bad}
'''
    return s+helpers(p)+f'''{p}_done:
mov rcx, qword ptr [rsp+0xC0]
mov rdx, qword ptr [rsp+0xB8]
'''


def helpers(p):
    """Unique enabled actions and bounded original native transitions."""
    s = f'''{p}_action:
'''+pointer('rdx', p+'_false', 'rdi')+f'''mov r8, qword ptr [rdx+0x128]
mov ecx, dword ptr [rdx+0x130]
test ecx, ecx
je {p}_false
cmp ecx, 4096
ja {p}_false
'''+pointer('r8', p+'_false', 'rdi')+f'''xor esi, esi
{p}_action_loop:
mov r9, qword ptr [r8]
test r9, r9
je {p}_action_next
'''+pointer('r9', p+'_false', 'rdi')+f'''cmp dword ptr [r9], eax
jne {p}_action_next
cmp byte ptr [r9+0x40], 1
jne {p}_false
cmp qword ptr [r9+0x38], rdx
jne {p}_false
test rsi, rsi
jne {p}_false
mov rsi, r9
{p}_action_next:
add r8, 8
dec ecx
jne {p}_action_loop
mov rax, rsi
ret
{p}_transition:
mov r8, qword ptr [rdx+0x78]
movzx ecx, word ptr [rdx+0x82]
test ecx, ecx
je {p}_false
cmp ecx, 256
ja {p}_false
movzx edx, word ptr [rdx+0x80]
mov edi, edx
add edi, ecx
cmp edi, 65536
ja {p}_false
'''+pointer('r8', p+'_false', 'rdi')+f'''lea r8, [r8+rdx*8]
mov r9, qword ptr [r8]
mov qword ptr [r11+0x188], r9
xor esi, esi
{p}_transition_loop:
mov r9, qword ptr [r8]
'''+pointer('r9', p+'_false', 'rdi')+f'''test eax, eax
je {p}_trans_heavy
cmp eax, 1
je {p}_trans_dispatch
cmp eax, 2
je {p}_trans_windup
cmp word ptr [r9+0x14], 3000
jne {p}_trans_next
cmp word ptr [r9], -1
jne {p}_trans_next
cmp byte ptr [r9+0xA], 1
jne {p}_trans_next
jmp {p}_trans_found
{p}_trans_windup:
cmp word ptr [r9], 208
jne {p}_trans_next
cmp word ptr [r9+0x14], 1273
jne {p}_trans_next
jmp {p}_trans_found
{p}_trans_dispatch:
cmp dword ptr [r9], 0x017D01DA
jne {p}_trans_next
cmp word ptr [r9+0x14], 4026
jne {p}_trans_next
cmp byte ptr [r9+0x17], 3
jne {p}_trans_next
cmp byte ptr [r9+0x18], 0
jne {p}_trans_next
cmp r9, qword ptr [r11+0x188]
jne {p}_false
jmp {p}_trans_found
{p}_trans_heavy:
cmp qword ptr [r9], -1
jne {p}_trans_next
cmp word ptr [r9+8], -1
jne {p}_trans_next
cmp byte ptr [r9+0xA], 0
jne {p}_trans_next
cmp dword ptr [r9+0xB], 0xFFFF0101
jne {p}_trans_next
cmp word ptr [r9+0x14], 3008
jne {p}_trans_next
{p}_trans_found:
test rsi, rsi
jne {p}_false
mov rsi, r9
{p}_trans_next:
add r8, 8
dec ecx
jne {p}_transition_loop
mov rax, rsi
ret
'''
    return s+motion_helper(p)+event_helper(p)+f'''{p}_false:
xor eax, eax
ret
'''


def motion_helper(p):
    bad = p+'_false'
    return f'''{p}_motion:
'''+pointer('rdx', bad)+f'''mov rax, {{motion_resource_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov r8, qword ptr [rdx+0x468]
'''+pointer('r8', bad)+f'''mov qword ptr [r11+0x140], r8
mov r9, qword ptr [rdx+0x470]
sub r9, r8
jbe {bad}
test r9, 7
jne {bad}
cmp r9, 0x80000
ja {bad}
shr r9, 3
mov dword ptr [r11+0x148], r9d
mov r8, qword ptr [rdx+0x480]
'''+pointer('r8', bad)+f'''mov ecx, dword ptr [r8+8]
test ecx, ecx
je {bad}
cmp ecx, 65536
ja {bad}
mov rdx, qword ptr [r8+0x10]
'''+pointer('rdx', bad)+f'''mov esi, -1
mov edi, -1
{p}_motion_loop:
cmp dword ptr [rdx], 1210
je {p}_motion1210
cmp dword ptr [rdx], 1211
jne {p}_motion_next
cmp edi, -1
jne {bad}
mov edi, dword ptr [rdx+4]
jmp {p}_motion_next
{p}_motion1210:
cmp esi, -1
jne {bad}
mov esi, dword ptr [rdx+4]
{p}_motion_next:
add rdx, 8
dec ecx
jne {p}_motion_loop
cmp esi, dword ptr [r11+0x148]
jae {bad}
cmp edi, dword ptr [r11+0x148]
jae {bad}
mov r8, qword ptr [r11+0x140]
mov rdx, qword ptr [r8+rsi*8]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x18], 0x42700000
jne {bad}
cmp word ptr [rdx+0x1C], 114
jne {bad}
mov rdx, qword ptr [r8+rdi*8]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x18], 0x42700000
jne {bad}
cmp word ptr [rdx+0x1C], 569
jne {bad}
mov eax, 1
ret
'''


def event_helper(p):
    """Validate each layer's descriptors, including native late 1210 markers."""
    bad = p+'_false'
    return f'''{p}_events:
mov dword ptr [r11+0x194], ecx
'''+pointer('rdx', bad)+f'''mov rax, {{event_wrapper_vtable}}
cmp qword ptr [rdx], rax
jne {bad}
mov rdx, qword ptr [rdx+0x468]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x140], rdx
mov r8, qword ptr [rdx]
'''+pointer('r8', bad)+f'''mov qword ptr [r11+0x148], r8
mov rax, 0x4B4341505F474D54
cmp qword ptr [r8], rax
jne {bad}
mov eax, dword ptr [r8+0x10]
cmp eax, 0x30
jb {bad}
cmp eax, 0x100000
ja {bad}
mov dword ptr [r11+0x170], eax
mov ecx, dword ptr [r8+0x14]
test ecx, ecx
je {bad}
cmp ecx, 4096
ja {bad}
mov dword ptr [r11+0x174], ecx
mov ebx, dword ptr [r8+0x20]
cmp ebx, 0x30
jb {bad}
cmp ebx, eax
ja {bad}
mov dword ptr [r11+0x178], ebx
lea ebx, [rbx+rcx*4]
cmp ebx, eax
ja {bad}
mov rdx, qword ptr [rdx+8]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x150], rdx
mov ecx, dword ptr [rdx+8]
test ecx, ecx
je {bad}
cmp ecx, 65536
ja {bad}
mov dword ptr [r11+0x168], ecx
mov rdx, qword ptr [rdx+0x10]
'''+pointer('rdx', bad)+f'''mov esi, -1
mov edi, -1
{p}_event_loop:
cmp dword ptr [rdx], 1210
je {p}_event1210
cmp dword ptr [rdx], 1211
jne {p}_event_next
cmp edi, -1
jne {bad}
mov edi, dword ptr [rdx+4]
jmp {p}_event_next
{p}_event1210:
cmp esi, -1
jne {bad}
mov esi, dword ptr [rdx+4]
{p}_event_next:
add rdx, 8
dec ecx
jne {p}_event_loop
cmp esi, dword ptr [r11+0x174]
jae {bad}
cmp edi, dword ptr [r11+0x174]
jae {bad}
mov dword ptr [r11+0x17C], edi
mov eax, esi
mov edx, 38
mov ecx, 65536
call {p}_descriptor
test rax, rax
je {bad}
mov qword ptr [r11+0x158], rax
mov eax, dword ptr [r11+0x17C]
mov edx, dword ptr [r11+0x194]
mov ecx, 569
call {p}_descriptor
test rax, rax
je {bad}
mov qword ptr [r11+0x160], rax
mov eax, 1
ret
{p}_descriptor:
mov ebx, edx
mov dword ptr [r11+0x198], ecx
mov r8, qword ptr [r11+0x148]
mov ecx, dword ptr [r11+0x178]
lea rdx, [r8+rcx]
mov edi, dword ptr [rdx+rax*4]
cmp edi, 0x30
jb {bad}
cmp edi, dword ptr [r11+0x170]
jae {bad}
mov esi, dword ptr [r11+0x170]
mov ecx, dword ptr [r11+0x174]
{p}_span_loop:
mov eax, dword ptr [rdx]
cmp eax, edi
jbe {p}_span_next
cmp eax, esi
jae {p}_span_next
mov esi, eax
{p}_span_next:
add rdx, 4
dec ecx
jne {p}_span_loop
sub esi, edi
cmp esi, 0x24
jb {bad}
cmp esi, 0x10000
ja {bad}
lea r8, [r8+rdi]
mov ecx, dword ptr [r8+4]
cmp ecx, ebx
jne {bad}
mov eax, dword ptr [r8+8]
cmp eax, 0x24
jb {bad}
mov edx, ecx
imul edx, edx, 12
add edx, eax
jc {bad}
cmp edx, esi
ja {bad}
lea rdx, [r8+rax]
{p}_schedule_loop:
mov eax, dword ptr [rdx]
cmp eax, dword ptr [r11+0x198]
jae {bad}
add rdx, 12
dec ecx
jne {p}_schedule_loop
mov rax, r8
ret
'''
