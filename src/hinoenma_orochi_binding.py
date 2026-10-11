"""Bounded current-instance discovery on the original heavy lookup path.

Helpers read already loaded native owners; only the private512-byte binding is
written. The original SAVE owns all registers used here. Helpers call only
local labels and return before a rejected binding takes the native fallback.
"""


# VM_READ placement lookup and mission CreateWithChimi/death branches agree on
# these exact pairs. Evidence: research/orochi-head-placement-proof-20261011.json.
# Three independent placements intentionally use the same native 9D1CC bank.
HEAD_IDENTITIES = ((0x9D1CC, 0x2913), (0x9D1CC, 0x3038),
                   (0xA09C8, 0x4255), (0x1DC1C, 0x4C71),
                   (0xD16C1, 0x2D97), (0xD294C, 0x44F0),
                   (0x8F795, 0x4361), (0x9D1CC, 0x31AA))


def pointer(register, bad, scratch='rax', alignment=8):
    if scratch == register:
        scratch = 'rcx'
    return f'''cmp {register}, 0x10000
jb {bad}
mov {scratch}, 0x800000000000
cmp {register}, {scratch}
jae {bad}
test {register}, {alignment-1}
jne {bad}
'''


def head_identity(prefix, bad):
    """Keep the grouping/order identical to the verified private candidate."""
    groups = {}
    for template, instance in HEAD_IDENTITIES:
        groups.setdefault(template, []).append(instance)
    source = 'mov eax, dword ptr [r9]\nmovzx ecx, word ptr [r9+6]\n'
    for index, (template, instances) in enumerate(groups.items()):
        next_label = f'{prefix}_head_scope_next_{index}'
        source += f'cmp eax, {hex(template)}\njne {next_label}\n'
        for instance in instances[:-1]:
            source += f'cmp ecx, {hex(instance)}\nje {prefix}_head\n'
        source += (f'cmp ecx, {hex(instances[-1])}\njne {bad}\n'
                   f'jmp {prefix}_head\n{next_label}:\n')
    return source+f'jmp {bad}\n{prefix}_head:\n'


def bootstrap(prefix='od'):
    p = prefix
    bad = 'oh_original'
    s = f'''mov r11, {{orochi_data}}
mov r9, {{production_data}}
mov r10, qword ptr [r9+0x10]
'''+pointer('r10', bad, 'rax')+f'''mov rax, {{player_slot}}
cmp r10, qword ptr [rax]
jne {bad}
cmp dword ptr [r10], 0x58E5E
jne {bad}
cmp dword ptr [r11], 0x4643524F
jne {p}_discover
cmp dword ptr [r11+0x74], 1
jne {p}_discover
mov eax, dword ptr [r9+0x1C]
cmp eax, dword ptr [r11+4]
jne {p}_discover
cmp r10, qword ptr [r11+8]
jne {p}_discover
mov rax, qword ptr [r10]
cmp rax, qword ptr [r11+0xA0]
je {p}_done
{p}_discover:
mov dword ptr [r11], 0
mov dword ptr [r11+0x74], 0
cmp dword ptr [r10+0xEF0], 0
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
'''+pointer('r9', bad)+head_identity(p, bad)+f'''
mov qword ptr [r11+0x18], r9
mov rax, qword ptr [r9]
mov qword ptr [r11+0x20], rax
mov rdx, qword ptr [r9+0x230]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r9
jne {bad}
mov r8, qword ptr [rdx+8]
'''+pointer('r8', bad)+f'''cmp qword ptr [r8+0x50], r9
jne {bad}
mov qword ptr [r11+0xA8], r8
mov rdx, qword ptr [r8+0x58]
'''+pointer('rdx', bad)+f'''mov eax, dword ptr [rdx]
cmp eax, 3203
je {p}_ready
cmp eax, 3205
je {p}_ready
cmp eax, 3204
jne {bad}
{p}_ready:
mov dword ptr [r11+0x118], eax
mov rdx, qword ptr [rdx+0x20]
'''+pointer('rdx', bad)+f'''test byte ptr [rdx+0x19], 1
je {bad}
mov rdx, qword ptr [r9+0xE90]
'''+pointer('rdx', bad, alignment=4)+f'''mov eax, dword ptr [r9]
cmp dword ptr [rdx], eax
jne {bad}
cmp dword ptr [rdx+0xC], 1
jne {bad}
mov rdx, qword ptr [r9+0x240]
'''+pointer('rdx', bad)+f'''cmp qword ptr [rdx], r9
jne {bad}
cmp qword ptr [rdx+0x20], 1
jne {bad}
mov qword ptr [r11+0x128], rdx
mov rdx, {{mission_temp_owner}}
mov rdx, qword ptr [rdx]
'''+pointer('rdx', bad)+f'''mov qword ptr [r11+0x130], rdx
lea rdx, [rdx+0x158184]
cmp byte ptr [rdx], 7
jne {bad}
cmp dword ptr [rdx+4], 1
jne {bad}
mov qword ptr [r11+0x120], rdx
mov rdx, {{loaded_package_tree}}
mov rdx, qword ptr [rdx]
'''+pointer('rdx', bad)+f'''mov rdx, qword ptr [rdx+8]
mov ecx, 64
{p}_tree:
'''+pointer('rdx', bad, 'rax')+f'''cmp byte ptr [rdx+0x19], 0
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
    for ident, off in ((3008, 0x60), (3491, 0x68), (4000, 0x1A8)):
        s += f'''mov rdx, qword ptr [r11+0x38]
mov eax, {ident}
call {p}_action
test rax, rax
je {bad}
mov qword ptr [r11+{off:#x}], rax
'''
    for off, motion in ((0x68, 1200), (0x1A8, 1201)):
        s += f'''mov rdx, qword ptr [r11+{off:#x}]
mov rdx, qword ptr [rdx+0x20]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x20], {motion}
jne {bad}
'''
        if motion == 1201:
            s += f'''cmp dword ptr [rdx+0x34], -1
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
    # Current Hino idle58 belongs to her bank. The common human idle1F0 owns
    # the original heavy transition; their action IDs match, their owners do not.
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
    for pkg_off, offsets in ((0x198, (0xB8, 0xC8, 0xD8, 0xE8, 0xF8, 0x1B0, 0x108)),
                             (0x1A0, (0xC0, 0xD0, 0xE0, 0xF0, 0x100, 0x1B8, 0x10C))):
        s += f'''mov rdx, qword ptr [r11+0x28]
mov rdx, qword ptr [rdx+{pkg_off:#x}]
mov qword ptr [r11+{offsets[0]:#x}], rdx
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
mov r8, qword ptr [r11+0x10]
mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x640], r9
jne {bad}
mov rax, qword ptr [r9]
cmp rax, qword ptr [r11+0x20]
jne {bad}
mov rax, qword ptr [r11+0x128]
cmp qword ptr [r9+0x240], rax
jne {bad}
cmp qword ptr [rax], r9
jne {bad}
cmp qword ptr [rax+0x20], 1
jne {bad}
mov rax, {{mission_temp_owner}}
mov rax, qword ptr [rax]
cmp rax, qword ptr [r11+0x130]
jne {bad}
mov rax, qword ptr [r11+0x120]
cmp byte ptr [rax], 7
jne {bad}
cmp dword ptr [rax+4], 1
jne {bad}
mov dword ptr [r11+0x1C0], 42
mov dword ptr [r11+0x1C4], 19
mov dword ptr [r11+0x74], 0
mov dword ptr [r11], 0x4643524F
jmp {p}_done
'''
    s += helpers(p)
    return s+f'''{p}_done:
mov rcx, qword ptr [rsp+0xC0]
mov rdx, qword ptr [rsp+0xB8]
'''


def helpers(p):
    """Local-only subroutines; each rejected helper returns zero normally."""
    s = f'''{p}_action:
'''+pointer('rdx', f'{p}_false', 'rdi')+f'''mov r8, qword ptr [rdx+0x128]
mov ecx, dword ptr [rdx+0x130]
test ecx, ecx
je {p}_false
cmp ecx, 4096
ja {p}_false
'''+pointer('r8', f'{p}_false', 'rdi')+f'''xor esi, esi
{p}_action_loop:
mov r9, qword ptr [r8]
test r9, r9
je {p}_action_next
'''+pointer('r9', f'{p}_false', 'rdi')+f'''cmp dword ptr [r9], eax
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
'''+pointer('r8', f'{p}_false', 'rdi')+f'''lea r8, [r8+rdx*8]
xor esi, esi
{p}_transition_loop:
mov r9, qword ptr [r8]
'''+pointer('r9', f'{p}_false', 'rdi')+f'''test eax, eax
je {p}_trans_heavy
cmp eax, 1
je {p}_trans_dispatch
cmp eax, 2
je {p}_trans_windup
cmp word ptr [r9+0x14], 3000
jne {p}_trans_next
cmp word ptr [r9], -1
jne {p}_trans_next
jmp {p}_trans_found
{p}_trans_windup:
cmp word ptr [r9], 208
jne {p}_trans_next
cmp word ptr [r9+0x14], 4000
jne {p}_trans_next
jmp {p}_trans_found
{p}_trans_dispatch:
cmp dword ptr [r9], 0x017D017C
jne {p}_trans_next
cmp word ptr [r9+0x14], 3491
jne {p}_trans_next
cmp byte ptr [r9+0x17], 3
jne {p}_trans_next
cmp byte ptr [r9+0x18], 0
jne {p}_trans_next
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
    bad=f'{p}_false'
    s=f'''{p}_motion:
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
cmp dword ptr [rdx], 1200
je {p}_motion1200
cmp dword ptr [rdx], 1201
jne {p}_motion_next
cmp edi, -1
jne {bad}
mov edi, dword ptr [rdx+4]
jmp {p}_motion_next
{p}_motion1200:
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
cmp word ptr [rdx+0x1C], 95
jne {bad}
mov rdx, qword ptr [r8+rdi*8]
'''+pointer('rdx', bad)+f'''cmp dword ptr [rdx+0x18], 0x42700000
jne {bad}
cmp word ptr [rdx+0x1C], 409
jne {bad}
mov eax, 1
ret
'''
    return s


def event_helper(p):
    bad=f'{p}_false'
    s=f'''{p}_events:
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
cmp dword ptr [rdx], 1200
je {p}_event1200
cmp dword ptr [rdx], 1201
jne {p}_event_next
cmp edi, -1
jne {bad}
mov edi, dword ptr [rdx+4]
jmp {p}_event_next
{p}_event1200:
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
mov edx, 95
call {p}_descriptor
test rax, rax
je {bad}
mov qword ptr [r11+0x158], rax
mov eax, dword ptr [r11+0x17C]
mov edx, 409
call {p}_descriptor
test rax, rax
je {bad}
mov qword ptr [r11+0x160], rax
mov eax, 1
ret
{p}_descriptor:
mov ebx, edx
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
mov edi, 19
cmp ebx, 95
je {p}_schedule_count
mov edi, 42
{p}_schedule_count:
cmp ecx, edi
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
cmp dword ptr [rdx], ebx
jae {bad}
add rdx, 12
dec ecx
jne {p}_schedule_loop
mov rax, r8
ret
'''
    return s
