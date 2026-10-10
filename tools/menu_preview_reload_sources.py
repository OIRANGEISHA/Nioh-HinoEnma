"""Pure copied-hash aura and current-generation camera assembly sources."""
import menu_preview_aura_source as frozen_aura
import menu_preview_camera_rev2_hooks as distance
import menu_preview_camera_height_hooks as height

def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Frozen source boundary changed')
    return source.replace(old, new)


def camera_guard(*, recheck=False):
    source = distance._guard(recheck=recheck)
    source = once(source, '''mov r11, {data}
cmp dword ptr [r11+0x10], r8d
jne camera_native
cmp dword ptr [r11+0x14], 1
jne camera_native
''', '')
    for offset, register in ((0x18, 'rcx'), (0x20, 'rdx'), (0x28, 'r9')):
        source = once(source, f'''mov rax, {{data}}
cmp qword ptr [rax+{hex(offset)}], {register}
jne camera_native
''', '')
    boundary = '''cmp dword ptr [r11+0x30], ecx
jne camera_native
'''
    generation = ('cmp dword ptr [rsp+0x20], ecx\njne camera_native\n'
        if recheck else 'mov dword ptr [rsp+0x20], ecx\n')
    source = once(source, boundary, boundary+generation)
    boundary = '''cmp dword ptr [r11+0x3C], 0
je camera_native
'''
    capture = 'mov eax, dword ptr [r11+0x3C]\n'
    capture += ('cmp dword ptr [rsp+0x24], eax\njne camera_native\n'
        if recheck else 'mov dword ptr [rsp+0x24], eax\n')
    return once(source, boundary, boundary+capture)


def camera_asm(*, raised=False):
    output, scalar = ('xmm6', '0xC2340000') if raised else ('xmm2', '0x44390000')
    native = '{native_height}' if raised else '{native_distance}'
    source = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0x30
mov r11, {data}
inc dword ptr [r11]
'''
    caller = height._caller_guard().replace('[rsp+0x98]', '[rsp+0xA8]') if raised else ''
    scale = '''mov eax, dword ptr [rdi+0x160]
test eax, eax
jle camera_native
cmp eax, 0x7F800000
jae camera_native
''' if raised else ''
    source += caller+camera_guard()+scale
    source += 'camera_recheck:\n'+caller+camera_guard(recheck=True)+scale
    source += f'''mov r11, {{data}}
inc dword ptr [r11+4]
mov dword ptr [rsp], {scalar}
movss {output}, dword ptr [rsp]
jmp camera_restore
camera_native:
mov r11, {{data}}
inc dword ptr [r11+8]
mov r11, {native}
movss {output}, dword ptr [r11]
camera_restore:
add rsp, 0x30
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {{return}}
'''
    if raised:
        source = source.replace('{data}', '{height_data}')
    return source


def aura_scope(rejected, *, capture=False, suffix):
    source = frozen_aura._scope(rejected, capture=capture)
    old = '''lea r12, [rax+0x2D8]
cmp qword ptr [r10+0x10], r12
jne '''+rejected+'\n'
    new = f'''mov r12, qword ptr [r10+0x10]
cmp r12, 0x10000
jb {rejected}
mov r14, 0x800000000000
lea r15, [r12+0x518]
cmp r15, r14
jae {rejected}
xor r15d, r15d
reload_pairs_{suffix}:
mov r14, qword ptr [r12+r15*8]
cmp qword ptr [rax+r15*8+0x2D8], r14
jne {rejected}
inc r15d
cmp r15d, 163
jb reload_pairs_{suffix}
'''
    new += ('mov qword ptr [rsp+0x68], r12\n' if capture
        else f'cmp qword ptr [rsp+0x68], r12\njne {rejected}\n')
    return once(source, old, new)


def aura_asm():
    source = frozen_aura.aura_asm()
    first = frozen_aura._scope('aura_restore', capture=True)
    source = once(source, first, aura_scope('aura_restore', capture=True, suffix='first'))
    later = frozen_aura._scope('aura_unlock')
    if source.count(later) != 2:
        raise ValueError('Require two native lookup scope rechecks')
    source = source.replace(later, aura_scope('aura_unlock', suffix='lookup'), 1)
    source = once(source, later, aura_scope('aura_unlock', suffix='final'))
    return source.replace('{data}', '{aura_data}')

