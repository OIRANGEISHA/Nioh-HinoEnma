"""Attach a real native guardian component without changing the Boss actor type.

The game constructs this C0-byte component only for actor ID100. Its common
actor update and destructor, however, handle any non-null 2C0/2C8 component.
Use that same native allocator, vtable, defaults and paired owner fields.
The native update performs resource checks, creates the guardian's own actor,
requests its action and releases it. Never manufacture a guardian actor ID.
"""

GUARDIAN_TARGETS = {
    'native_guardian_allocator': 0xFA6FF0,
    'native_guardian_vtable': 0x11A5BB0,
    'native_default_vector': 0x752560,
    'native_identity_matrix': 0x6E9210,
    'native_guardian_set_mode': 0x77FB20,
}

GUARDIAN_START_ASM = '''living_weapon_guardian_start:
push rbx
push rdi
push rsi
sub rsp, 0x40
mov rsi, rcx
mov rdi, qword ptr [rsi+0x2C0]
test rdi, rdi
jne living_weapon_guardian_validate
cmp qword ptr [rsi+0x2C8], 0
jne living_weapon_guardian_done
call {native_guardian_allocator}
test rax, rax
je living_weapon_guardian_done
mov rbx, rax
mov rax, qword ptr [rbx]
test rax, rax
je living_weapon_guardian_done
cmp qword ptr [rax+0x28], 0
je living_weapon_guardian_done
cmp qword ptr [rax+0x58], 0
je living_weapon_guardian_done
mov dword ptr [rsp+0x20], 0x2D
mov dword ptr [rsp+0x24], 0
mov qword ptr [rsp+0x28], 0
lea r8, [rsp+0x20]
mov edx, 0xC0
mov rcx, rbx
call qword ptr [rax+0x28]
test rax, rax
je living_weapon_guardian_done
mov rdi, rax
test rdi, 0x0F
jne living_weapon_guardian_free_unaligned
mov rax, {native_guardian_vtable}
mov qword ptr [rdi], rax
mov qword ptr [rdi+0x10], rsi
xor eax, eax
mov qword ptr [rdi+0x18], rax
mov qword ptr [rdi+0x20], rax
mov qword ptr [rdi+0x28], rax
mov qword ptr [rdi+0x30], rax
mov qword ptr [rdi+0x38], rax
mov qword ptr [rdi+0x40], rax
mov qword ptr [rdi+0x48], rax
call {native_default_vector}
movaps xmm0, xmmword ptr [rax]
movups xmmword ptr [rdi+0x50], xmm0
call {native_identity_matrix}
movaps xmm0, xmmword ptr [rax]
movups xmmword ptr [rdi+0x60], xmm0
movaps xmm0, xmmword ptr [rax+0x10]
movups xmmword ptr [rdi+0x70], xmm0
movaps xmm0, xmmword ptr [rax+0x20]
movups xmmword ptr [rdi+0x80], xmm0
movaps xmm0, xmmword ptr [rax+0x30]
movups xmmword ptr [rdi+0x90], xmm0
call {native_default_vector}
movaps xmm0, xmmword ptr [rax]
movups xmmword ptr [rdi+0xA0], xmm0
mov dword ptr [rdi+0xB0], -1
mov qword ptr [rsi+0x2C0], rdi
mov qword ptr [rsi+0x2C8], rbx
living_weapon_guardian_validate:
mov rax, {native_guardian_vtable}
cmp qword ptr [rdi], rax
jne living_weapon_guardian_done
cmp qword ptr [rdi+0x10], rsi
jne living_weapon_guardian_done
call {native_guardian_allocator}
test rax, rax
je living_weapon_guardian_done
cmp qword ptr [rsi+0x2C8], rax
jne living_weapon_guardian_done
cmp qword ptr [rdi+0x48], 0
jne living_weapon_guardian_done
cmp qword ptr [rdi+0x18], 0
jne living_weapon_guardian_done
cmp qword ptr [rdi+0x30], 0
jne living_weapon_guardian_done
cmp dword ptr [rdi+0xB0], -1
jne living_weapon_guardian_done
movups xmm0, xmmword ptr [rsi+0xF0]
movups xmmword ptr [rdi+0x50], xmm0
movups xmm0, xmmword ptr [rsi+0x100]
movups xmmword ptr [rdi+0x60], xmm0
movups xmm0, xmmword ptr [rsi+0x110]
movups xmmword ptr [rdi+0x70], xmm0
movups xmm0, xmmword ptr [rsi+0x120]
movups xmmword ptr [rdi+0x80], xmm0
movups xmm0, xmmword ptr [rsi+0x130]
movups xmmword ptr [rdi+0x90], xmm0
mov rcx, rdi
mov edx, 5
call {native_guardian_set_mode}
jmp living_weapon_guardian_done
living_weapon_guardian_free_unaligned:
mov rax, qword ptr [rbx]
mov rdx, rdi
mov rcx, rbx
call qword ptr [rax+0x58]
living_weapon_guardian_done:
add rsp, 0x40
pop rsi
pop rdi
pop rbx
ret
'''


def guardian_living_weapon_hooks():
    from hinoenma_living_weapon import living_weapon_hooks
    hooks = living_weapon_hooks()
    first = dict(hooks[0])
    marker = 'inc dword ptr [r11+0xE48]\njmp living_weapon_done\n'
    if first['asm'].count(marker) != 1:
        raise ValueError('Native Living Weapon successful-start marker changed.')
    first['asm'] = first['asm'].replace(marker, 'inc dword ptr [r11+0xE48]\n'
        'mov rcx, qword ptr [rsi+0x50]\ncall living_weapon_guardian_start\n'
        'jmp living_weapon_done\n') + GUARDIAN_START_ASM
    first['purpose'] += '; after native successful start, request mode5 through a same-pool native guardian component, using its own actor/resources/update/cleanup'
    return [first, *hooks[1:]]
