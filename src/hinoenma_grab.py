"""Scoped full life-drain pairing, with historical and automatic profiles.

Only Hino-Enma player action 62 / motion 1100 may bypass native condition 22.
Keep native hit acceptance, pairing, victim motion 44000, damage and healing.
Recheck the target's enabled reaction and loaded clip on every accepted grab.
Keep enemy categories intact; do not force unavailable paired animations.
"""

GRAB_TARGETS = {'grab_native_reject': 0x73AAB1}
YOKAI_GRAB = dict(
    name='HE_YokaiGrab', rva=0x738B93, length=10,
    code_offset=0x6000, code_capacity=0x800,
    purpose='Native full life-drain pairing for Gaki and dual-sword Yoki with verified loaded victim motion',
    asm='''
pushfq
push rax
push rdx
push r8
push r9
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+4], 0
je yokai_grab_native
cmp dword ptr [rax+0xC], 1
jne yokai_grab_native
mov r9, qword ptr [rcx+0x50]
test r9, r9
je yokai_grab_native
cmp r9, qword ptr [r11+0x10]
jne yokai_grab_native
mov r10, {player_slot}
cmp r9, qword ptr [r10]
jne yokai_grab_native
cmp word ptr [r9+6], 1
jne yokai_grab_native
cmp dword ptr [r9+0xEF0], 0
jne yokai_grab_native
cmp dword ptr [r9], 0x58E5E
je yokai_grab_player
cmp dword ptr [r9], 0x51BE1
jne yokai_grab_native
yokai_grab_player:
mov r10, qword ptr [rcx+0x58]
test r10, r10
je yokai_grab_native
cmp dword ptr [r10], 62
jne yokai_grab_native
mov r10, qword ptr [r10+0x20]
test r10, r10
je yokai_grab_native
cmp dword ptr [r10+0x20], 1100
jne yokai_grab_native
mov r9, qword ptr [rcx+0x5B0]
test r9, r9
je yokai_grab_native
cmp dword ptr [r9], 0x7D77D
je yokai_grab_target
cmp dword ptr [r9], 0xC1FC3
jne yokai_grab_native
yokai_grab_target:
cmp qword ptr [r9+0xE90], rax
jne yokai_grab_native
mov r10, qword ptr [r9+0x230]
test r10, r10
je yokai_grab_native
mov r10, qword ptr [r10+8]
test r10, r10
je yokai_grab_native
cmp qword ptr [r10+0x50], r9
jne yokai_grab_native
mov r10, qword ptr [r10+0x80]
test r10, r10
je yokai_grab_native
mov edx, dword ptr [r10+0x130]
test edx, edx
je yokai_grab_native
cmp edx, 4096
ja yokai_grab_native
mov r8, qword ptr [r10+0x128]
test r8, r8
je yokai_grab_native
yokai_grab_reaction_loop:
mov rax, qword ptr [r8]
test rax, rax
je yokai_grab_reaction_next
cmp dword ptr [rax], 858
je yokai_grab_reaction_found
yokai_grab_reaction_next:
add r8, 8
dec edx
jne yokai_grab_reaction_loop
jmp yokai_grab_native
yokai_grab_reaction_found:
cmp byte ptr [rax+0x40], 1
jne yokai_grab_native
mov rax, qword ptr [rax+0x20]
test rax, rax
je yokai_grab_native
cmp dword ptr [rax+0x20], 44000
jne yokai_grab_native
mov r10, qword ptr [r9+0x38]
test r10, r10
je yokai_grab_native
mov eax, dword ptr [r10+0x50]
cmp eax, 1
ja yokai_grab_native
shl eax, 5
mov r9, qword ptr [r10+rax+0x18]
test r9, r9
je yokai_grab_native
mov r10, qword ptr [r9+0x480]
test r10, r10
je yokai_grab_native
mov r8, qword ptr [r10+0x10]
test r8, r8
je yokai_grab_native
mov r10d, dword ptr [r10+8]
test r10d, r10d
je yokai_grab_native
cmp r10d, 65536
ja yokai_grab_native
mov eax, 0x5168A21
xor edx, edx
div r10d
mov eax, r10d
yokai_grab_motion_loop:
cmp dword ptr [r8+rdx*8], 44000
je yokai_grab_motion_found
cmp dword ptr [r8+rdx*8], -1
je yokai_grab_native
dec eax
je yokai_grab_native
inc edx
cmp edx, r10d
jb yokai_grab_motion_loop
xor edx, edx
jmp yokai_grab_motion_loop
yokai_grab_motion_found:
mov eax, dword ptr [r8+rdx*8+4]
cmp eax, r10d
jae yokai_grab_native
mov r8, qword ptr [r9+0x468]
test r8, r8
je yokai_grab_native
mov r8, qword ptr [r8+rax*8]
test r8, r8
je yokai_grab_native
cmp dword ptr [r8+0x1C], 0
je yokai_grab_native
lock inc dword ptr [r11+0xF00]
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rax
popfq
cmp eax, eax
jmp {return}
yokai_grab_native:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rax
popfq
cmp dword ptr [rax+0xC], 0
jne {grab_native_reject}
jmp {return}
''')


def onryoki_grab_hook():
    """Add the Onryoki template whose full pairing was confirmed in game."""
    hook = dict(YOKAI_GRAB)
    guard = '''cmp dword ptr [r9], 0xC1FC3
jne yokai_grab_native
yokai_grab_target:'''
    if hook['asm'].count(guard) != 1:
        raise ValueError('Unexpected base life-drain guard')
    hook['asm'] = hook['asm'].replace(guard, '''cmp dword ptr [r9], 0xC1FC3
je yokai_grab_target
cmp dword ptr [r9], 0x3ECF4
jne yokai_grab_native
yokai_grab_target:''')
    hook['purpose'] = 'Native full life-drain pairing for observed yokai and Onryoki with loaded victim motion'
    return hook


def automatic_grab_hook():
    """Resource-qualified pairing, with native effective-action precedence.

No template allowlist: the original hit/pair candidate must be an actual
non-player character of native kind 1. Its first enabled action 858 must be
the common group-2 motion 44000, whose selected-bank clip must be present.
Loaded animation is a prerequisite, not proof that every skeleton looks right.
"""
    hook = onryoki_grab_hook()
    template_guard = '''cmp dword ptr [r9], 0x7D77D
je yokai_grab_target
cmp dword ptr [r9], 0xC1FC3
je yokai_grab_target
cmp dword ptr [r9], 0x3ECF4
jne yokai_grab_native'''
    if hook['asm'].count(template_guard) != 1:
        raise ValueError('Unexpected template allowlist in life-drain guard')
    hook['asm'] = hook['asm'].replace(template_guard, '''cmp word ptr [r9+4], 0
jne yokai_grab_native
cmp r9, qword ptr [rcx+0x50]
je yokai_grab_native''')
    # Preserve the controller argument while using ECX as the bounded group
    # loop counter. Native 73FA40 selects the first enabled record in 0,1,2.
    hook['asm'] = hook['asm'].replace('push rax\npush rdx', 'push rax\npush rcx\npush rdx')
    hook['asm'] = hook['asm'].replace('pop rdx\npop rax', 'pop rdx\npop rcx\npop rax')
    start = hook['asm'].index('mov r10, qword ptr [r10+0x80]')
    end = hook['asm'].index('yokai_grab_reaction_found:', start)
    hook['asm'] = hook['asm'][:start] + '''lea r10, [r10+0x70]
mov ecx, 3
yokai_grab_group_loop:
mov rax, qword ptr [r10]
test rax, rax
je yokai_grab_group_next
mov edx, dword ptr [rax+0x130]
test edx, edx
je yokai_grab_group_next
cmp edx, 4096
ja yokai_grab_native
mov r8, qword ptr [rax+0x128]
test r8, r8
je yokai_grab_native
yokai_grab_reaction_loop:
mov rax, qword ptr [r8]
test rax, rax
je yokai_grab_reaction_next
cmp dword ptr [rax], 858
jne yokai_grab_reaction_next
cmp byte ptr [rax+0x40], 0
je yokai_grab_reaction_next
cmp ecx, 1
jne yokai_grab_native
jmp yokai_grab_reaction_found
yokai_grab_reaction_next:
add r8, 8
dec edx
jne yokai_grab_reaction_loop
yokai_grab_group_next:
add r10, 8
dec ecx
jne yokai_grab_group_loop
jmp yokai_grab_native
''' + hook['asm'][end:]
    hook['purpose'] = 'Automatic native full-grab eligibility using accepted collision candidate, effective common reaction and loaded clip'
    return hook
