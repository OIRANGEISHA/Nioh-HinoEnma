"""Candidate native ladder dispatcher and scoped common-action lookup.

This module is opt-in until gameplay confirmation. Request 8/9 comes
from the real queued interaction. Common dispatcher 170 evaluates native
queries 122/123 to select entry 56/63. Common actions keep their original
parameters, bone transforms, movement conditions and completion events.
Hino-Enma IDs collide with common ladder IDs; lookup is restricted to the
current local captured player and its live ladder reference. No shared action
records, motion slots, positions or completion flags are written by hooks.
"""
from copy import deepcopy

LADDER_TARGETS = {'native_ladder_set_action': 0x706070,
                  'native_ladder_motion_index': 0x917500}


def player_controller_guard(prefix, controller_register='rdi'):
    return f'''mov r11, {{data}}
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je {prefix}_original
cmp dword ptr [r11+0x04], 0
je {prefix}_original
mov rax, {{player_slot}}
cmp rdx, qword ptr [rax]
jne {prefix}_original
cmp word ptr [rdx+0x04], 0
jne {prefix}_original
cmp word ptr [rdx+0x06], 1
jne {prefix}_original
cmp dword ptr [rdx], 0x58E5E
je {prefix}_role
cmp dword ptr [rdx], 0x51BE1
jne {prefix}_original
{prefix}_role:
cmp dword ptr [rdx+0xEF0], 0
jne {prefix}_original
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je {prefix}_original
cmp dword ptr [rax+0x0C], 1
jne {prefix}_original
mov rax, qword ptr [rdx+0x230]
test rax, rax
je {prefix}_original
cmp qword ptr [rax], rdx
jne {prefix}_original
cmp qword ptr [rax+0x08], {controller_register}
jne {prefix}_original
cmp qword ptr [{controller_register}+0x50], rdx
jne {prefix}_original
'''


def interaction_guard(prefix, controller_register='rdi', *, climbing=False):
    active = (f'''cmp byte ptr [r10+0x08], 1
jne {prefix}_original
cmp byte ptr [r10+0x09], 1
ja {prefix}_original''' if climbing else f'''cmp word ptr [r10+0x08], 0x0101
jne {prefix}_original''')
    return f'''mov r9, qword ptr [{controller_register}+0x510]
test r9, r9
je {prefix}_original
cmp word ptr [r9+0x04], 2
jne {prefix}_original
mov r10, qword ptr [{controller_register}+0x528]
test r10, r10
je {prefix}_original
cmp qword ptr [r10], r9
jne {prefix}_original
{active}
cmp dword ptr [r10+0x4C], 0
jle {prefix}_original
cmp dword ptr [r10+0x4C], 0x1000
ja {prefix}_original
cmp dword ptr [r10+0x50], 0
jle {prefix}_original
cmp dword ptr [r10+0x50], 0x1000
ja {prefix}_original
mov eax, dword ptr [r10+0x48]
cmp eax, 8
je {prefix}_request_valid
cmp eax, 9
jne {prefix}_original
{prefix}_request_valid:
'''


def queued_ladder_hook(original):
    """Extend the existing queued-reference continuation, retain door behavior."""
    spec = deepcopy(original)
    needle = '''cmp dword ptr [rcx], 2
jne queued_door_done'''
    if spec['asm'].count(needle) != 1:
        raise ValueError('Existing queued door source changed.')
    # The original queued-door prefix already checked captured pointer, loaded
    # template, instance, role and controller+50. Add the current-player and
    # proxy ownership checks without duplicating that prefix.
    entry = '''mov rax, {player_slot}
cmp rdx, qword ptr [rax]
jne ladder_entry_original
cmp word ptr [rdx+0x04], 0
jne ladder_entry_original
cmp dword ptr [rdx+0xEF0], 0
jne ladder_entry_original
mov rax, qword ptr [rdx+0xE90]
test rax, rax
je ladder_entry_original
cmp dword ptr [rax+0x0C], 1
jne ladder_entry_original
mov rax, qword ptr [rdx+0x230]
test rax, rax
je ladder_entry_original
cmp qword ptr [rax], rdx
jne ladder_entry_original
cmp qword ptr [rax+0x08], rdi
jne ladder_entry_original
''' + interaction_guard('ladder_entry') + '''cmp byte ptr [r10+0x0A], 0
jne ladder_entry_original
mov rax, qword ptr [rdi+0x58]
test rax, rax
je ladder_entry_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je ladder_entry_original
test byte ptr [rax], 1
je ladder_entry_original
test byte ptr [rax+1], 8
jne ladder_entry_original
mov rax, qword ptr [rdx+0x38]
test rax, rax
je ladder_entry_original
cmp dword ptr [rax+0x50], 1
ja ladder_entry_original
sub rsp, 0xA0
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov qword ptr [rsp+0x80], rax
mov dword ptr [rsp+0x90], 250
cmp dword ptr [r10+0x48], 8
je ladder_entry_motion_selected
mov dword ptr [rsp+0x90], 257
ladder_entry_motion_selected:
mov dword ptr [rsp+0x98], 2
ladder_entry_resource_loop:
mov rax, qword ptr [rsp+0x80]
mov ecx, dword ptr [rsp+0x98]
mov rax, qword ptr [rax+rcx*8+0x08]
test rax, rax
je ladder_entry_restore
mov qword ptr [rsp+0x88], rax
mov rcx, qword ptr [rax+0x480]
test rcx, rcx
je ladder_entry_restore
cmp dword ptr [rcx+0x08], 0
je ladder_entry_restore
cmp dword ptr [rcx+0x08], 0x10000
ja ladder_entry_restore
cmp qword ptr [rcx+0x10], 0
je ladder_entry_restore
mov edx, dword ptr [rsp+0x90]
mov r8d, -1
call {native_ladder_motion_index}
test eax, eax
js ladder_entry_restore
cmp eax, 0x10000
jae ladder_entry_restore
mov rcx, qword ptr [rsp+0x88]
mov r10, qword ptr [rcx+0x468]
test r10, r10
je ladder_entry_restore
mov rcx, qword ptr [rcx+0x470]
cmp rcx, r10
jbe ladder_entry_restore
sub rcx, r10
test cl, 7
jne ladder_entry_restore
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae ladder_entry_restore
cmp qword ptr [r10+rdx], 0
je ladder_entry_restore
cmp dword ptr [rsp+0x98], 2
jne ladder_entry_start
mov dword ptr [rsp+0x98], 6
jmp ladder_entry_resource_loop
ladder_entry_start:
mov rcx, rdi
mov edx, 170
call {native_ladder_set_action}
ladder_entry_restore:
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xA0
jmp queued_door_done
ladder_entry_original:
mov rcx, qword ptr [rdi+0x510]
'''
    spec['asm'] = spec['asm'].replace(needle, entry + needle)
    spec['purpose'] += '; candidate native common170 ladder dispatch after configured request8/9, with real motion clips checked'
    return spec


def common_ladder_lookup_hook():
    pushes = '''pushfq
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
'''
    pops = '''pop rdi
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
    return dict(name='HE_LadderCommonLookup', rva=0x73FA40, length=5,
                code_offset=0xE800, code_capacity=0x800,
                purpose='Candidate common170/250..267 action selection for the current captured Hino-Enma player live native ladder; preserve default lookup outside ladder and restore boss idle naturally',
                asm=pushes + '''mov ebx, edx
mov rsi, r8
mov r11, {data}
mov rax, qword ptr [r11+0x10]
test rax, rax
je ladder_lookup_original
cmp dword ptr [r11+0x04], 0
je ladder_lookup_original
mov rdx, {player_slot}
cmp rax, qword ptr [rdx]
jne ladder_lookup_original
mov rdi, qword ptr [rax+0x230]
test rdi, rdi
je ladder_lookup_original
mov rdi, qword ptr [rdi+0x08]
test rdi, rdi
je ladder_lookup_original
lea rax, [rdi+0x70]
cmp rcx, rax
jne ladder_lookup_original
''' + player_controller_guard('ladder_lookup') + interaction_guard('ladder_lookup', climbing=True) + '''mov r9, qword ptr [rdi+0x80]
test r9, r9
je ladder_lookup_original
cmp byte ptr [r10+0x0A], 1
ja ladder_lookup_original
mov rax, qword ptr [rdi+0x58]
test rax, rax
je ladder_lookup_original
cmp qword ptr [rax+0x38], r9
jne ladder_lookup_entry
mov rax, qword ptr [rax+0x20]
test rax, rax
je ladder_lookup_original
cmp dword ptr [rax+0x20], 250
jl ladder_lookup_entry
cmp dword ptr [rax+0x20], 267
jg ladder_lookup_entry
cmp ebx, 56
jb ladder_lookup_extra
cmp ebx, 70
jbe ladder_lookup_find
ladder_lookup_extra:
cmp ebx, 180
je ladder_lookup_find
cmp ebx, 208
je ladder_lookup_find
cmp ebx, 209
je ladder_lookup_find
cmp ebx, 1005
jb ladder_lookup_original
cmp ebx, 1007
jbe ladder_lookup_find
jmp ladder_lookup_original
ladder_lookup_entry:
cmp word ptr [r10+0x08], 0x0101
jne ladder_lookup_original
cmp byte ptr [r10+0x0A], 0
jne ladder_lookup_original
mov rax, qword ptr [rdi+0x58]
mov rax, qword ptr [rax+0x20]
test rax, rax
je ladder_lookup_original
test byte ptr [rax], 1
je ladder_lookup_original
test byte ptr [rax+1], 8
jne ladder_lookup_original
cmp ebx, 170
je ladder_lookup_find
cmp dword ptr [r10+0x48], 8
jne ladder_lookup_top
cmp ebx, 56
je ladder_lookup_find
jmp ladder_lookup_original
ladder_lookup_top:
cmp ebx, 63
jne ladder_lookup_original
ladder_lookup_find:
mov ecx, dword ptr [r9+0x130]
test ecx, ecx
je ladder_lookup_original
cmp ecx, 0x1000
ja ladder_lookup_original
mov r10, qword ptr [r9+0x128]
test r10, r10
je ladder_lookup_original
xor edx, edx
ladder_lookup_loop:
mov rax, qword ptr [r10+rdx*8]
test rax, rax
je ladder_lookup_next
cmp byte ptr [rax+0x40], 0
je ladder_lookup_next
cmp dword ptr [rax], ebx
jne ladder_lookup_next
cmp qword ptr [rax+0x38], r9
jne ladder_lookup_original
mov r11, qword ptr [rax+0x20]
test r11, r11
je ladder_lookup_original
cmp ebx, 170
jne ladder_lookup_motion
cmp dword ptr [r11+0x20], -1
jne ladder_lookup_original
jmp ladder_lookup_found
ladder_lookup_motion:
cmp dword ptr [r11+0x20], 250
jl ladder_lookup_original
cmp dword ptr [r11+0x20], 267
jg ladder_lookup_original
ladder_lookup_found:
test rsi, rsi
je ladder_lookup_return
mov dword ptr [rsi], 2
ladder_lookup_return:
mov qword ptr [rsp+0x48], rax
''' + pops + '''ret
ladder_lookup_next:
inc edx
cmp edx, ecx
jb ladder_lookup_loop
ladder_lookup_original:
''' + pops + '''mov qword ptr [rsp+0x08], rbx
jmp {return}
''')
