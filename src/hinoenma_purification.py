"""Emit native Ki Pulse VFX and an attack sphere during the observed dojo hint.

743E60 creates G1G VFX DB3; 7245E0 calls 916920 to create the actual attack
collider using shared attack row 59, 157 or 158. The legacy target aliases
are retained so previous compiled hooks remain identical. Both the VFX and
the attack sphere need a root anchor on Hino-Enma. Only the exact current
hint and captured player are eligible. Native hit decisions and native
Shot::AddTokoyoBreakCount remain responsible for success.
"""
from hinoenma_tutorial import player_guard

PURIFICATION_HINT_TEXT = '祓除常世：透过残心回复最大量的精力时发动。可消除周遭的常世'
PURIFICATION_TARGETS = {
    'purification_hint_hidden': 0xD4994B,
    'native_purification_wave': 0x743E60,
    'native_purification_visual': 0x7245E0,
    'native_purification_actor_manager': 0x189F3F8,
    'native_shot_resource_manager': 0x1871548,
    'native_controller_special_query': 0x73D2C0,
    'native_purification_set_collision_origin': 0x7DF9F0,
}


def hidden_hint_scope(prefix, widget='rdx'):
    """The inactive UI no longer ticks, so validate its retained lesson in-player."""
    return f'''mov rax, {{tutorial_ui_owner}}
mov rax, qword ptr [rax]
test rax, rax
je {prefix}_inactive
cmp {widget}, qword ptr [rax+0x338]
jne {prefix}_inactive
cmp qword ptr [{widget}+0xA0], 0
jne {prefix}_inactive
cmp {widget}, qword ptr [r11+0xFB0]
jne {prefix}_inactive
cmp r10, qword ptr [r11+0xF98]
jne {prefix}_inactive
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xFA0]
jne {prefix}_inactive
mov rax, {{tutorial_manager}}
mov rax, qword ptr [rax]
test rax, rax
je {prefix}_inactive
cmp rax, qword ptr [r11+0xF90]
jne {prefix}_inactive
mov eax, dword ptr [rax+0x264]
cmp eax, dword ptr [r11+0xE04]
jne {prefix}_inactive
'''


def hint_scope(prefix, widget='rbx'):
    raw = PURIFICATION_HINT_TEXT.encode('utf-16le')
    foreign = 'done' if widget == 'rbx' else 'inactive'
    lines = [f'mov rax, {{tutorial_ui_owner}}', 'mov rax, qword ptr [rax]',
             'test rax, rax', f'je {prefix}_{foreign}',
             f'cmp {widget}, qword ptr [rax+0x338]', f'jne {prefix}_{foreign}',
             f'cmp dword ptr [{widget}+0x60], 0', f'je {prefix}_hidden',
             f'cmp dword ptr [{widget}+0x60], 3', f'ja {prefix}_inactive',
             f'cmp qword ptr [{widget}+0xA0], {len(PURIFICATION_HINT_TEXT)}',
             f'jne {prefix}_inactive',
             f'cmp qword ptr [{widget}+0xA8], {len(PURIFICATION_HINT_TEXT)}',
             f'jb {prefix}_inactive', f'mov r9, qword ptr [{widget}+0x90]',
             'test r9, r9', f'je {prefix}_inactive']
    for offset in range(0, len(raw), 8):
        chunk = raw[offset:offset+8]
        if len(chunk) == 8:
            lines += [f'mov rax, 0x{int.from_bytes(chunk, "little"):X}',
                      f'cmp qword ptr [r9+{offset}], rax']
        else:
            width = 'word' if len(chunk) == 2 else 'dword'
            assert len(chunk) in (2, 4)
            lines += [f'cmp {width} ptr [r9+{offset}], 0x{int.from_bytes(chunk, "little"):X}']
        lines += [f'jne {prefix}_inactive']
    lines += [f'jmp {prefix}_scope_ready', f'{prefix}_hidden:',
              f'cmp qword ptr [{widget}+0xA0], 0', f'jne {prefix}_inactive',
              'cmp dword ptr [r11+0xE00], 1', f'jne {prefix}_inactive',
              f'cmp {widget}, qword ptr [r11+0xFB0]', f'jne {prefix}_inactive',
              'cmp r10, qword ptr [r11+0xF98]', f'jne {prefix}_inactive',
              'mov eax, dword ptr [r11+0x1C]',
              'cmp eax, dword ptr [r11+0xFA0]', f'jne {prefix}_inactive',
              'mov rax, {tutorial_manager}', 'mov rax, qword ptr [rax]',
              'test rax, rax', f'je {prefix}_inactive',
              'cmp rax, qword ptr [r11+0xF90]', f'jne {prefix}_inactive',
              'mov eax, dword ptr [rax+0x264]',
              'cmp eax, dword ptr [r11+0xE04]', f'jne {prefix}_inactive',
              f'{prefix}_scope_ready:']
    return '\n'.join(lines) + '\n'


PURIFICATION_INPUT = {
    'name': 'HE_PurificationHintSpace', 'rva': 0xD4982E, 'length': 6,
    'code_capacity': 0x800,
    'purpose': 'Queue one native purification pulse on fresh mapped Space during the identified current dojo lesson, retaining its scope after the hint timer hides its text',
    'asm': '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
mov r11, {data}
''' + player_guard('purify_hint') + hint_scope('purify_hint') + '''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je purify_hint_inactive
cmp dword ptr [r11+0xE00], 1
jne purify_hint_new_epoch
mov eax, dword ptr [r8+0x264]
cmp eax, dword ptr [r11+0xE04]
jne purify_hint_inactive
cmp dword ptr [r11+0xFB8], 1
jne purify_hint_new_epoch
cmp r8, qword ptr [r11+0xF90]
jne purify_hint_new_epoch
cmp r10, qword ptr [r11+0xF98]
jne purify_hint_new_epoch
cmp rbx, qword ptr [r11+0xFB0]
jne purify_hint_new_epoch
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xFA0]
je purify_hint_epoch_ready
purify_hint_new_epoch:
mov dword ptr [r11+0xE00], 1
mov eax, dword ptr [r8+0x264]
mov dword ptr [r11+0xE04], eax
mov qword ptr [r11+0xF90], r8
mov qword ptr [r11+0xF98], r10
mov qword ptr [r11+0xFB0], rbx
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0xFA0], eax
mov dword ptr [r11+0xFA4], 0
mov dword ptr [r11+0xFA8], 1
mov dword ptr [r11+0xFB8], 1
mov dword ptr [r11+0xFC0], 0
purify_hint_epoch_ready:
mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je purify_hint_block_input
cmp byte ptr [rax+0x4A], 1
jne purify_hint_block_input
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_hint_block_input
mov r9, qword ptr [rax+0x08]
test r9, r9
je purify_hint_block_input
cmp byte ptr [r9], 1
jne purify_hint_block_input
mov rax, {native_key_settings}
mov rax, qword ptr [rax]
test rax, rax
je purify_hint_block_input
mov edx, dword ptr [rax+0xC44]
cmp edx, 1
ja purify_hint_block_input
mov rax, {native_stance_key_vector}
cmp qword ptr [rax+0x08], 1
jb purify_hint_block_input
cmp qword ptr [rax+0x08], 128
ja purify_hint_block_input
mov rax, qword ptr [rax]
test rax, rax
je purify_hint_block_input
cmp dword ptr [rax+rdx*4+0x08], 0xFF
jne purify_hint_block_input
mov eax, dword ptr [rax+rdx*4]
cmp eax, 0xFF
jae purify_hint_block_input
cmp eax, dword ptr [r11+0xFBC]
je purify_hint_key_ready
mov dword ptr [r11+0xFBC], eax
mov dword ptr [r11+0xFA8], 1
mov dword ptr [r11+0xFC0], 0
purify_hint_key_ready:
test byte ptr [r9+rax+0x01], 0x80
je purify_hint_key_released
cmp dword ptr [r11+0xFA8], 0
jne purify_hint_done
mov dword ptr [r11+0xFA8], 1
cmp dword ptr [r11+0xFC0], 0
jne purify_hint_done
mov dword ptr [r11+0xFC0], 1
inc dword ptr [r11+0xFA4]
inc dword ptr [r11+0xFAC]
jmp purify_hint_done
purify_hint_key_released:
mov dword ptr [r11+0xFA8], 0
jmp purify_hint_done
purify_hint_block_input:
mov dword ptr [r11+0xFA8], 1
mov dword ptr [r11+0xFC0], 0
jmp purify_hint_done
purify_hint_inactive:
mov dword ptr [r11+0xE00], 0
mov dword ptr [r11+0xFA4], 0
mov dword ptr [r11+0xFA8], 1
mov dword ptr [r11+0xFB8], 0
mov dword ptr [r11+0xFC0], 0
purify_hint_done:
pop rbx
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
je {purification_hint_hidden}
jmp {return}
''',
}


PURIFICATION_TICK = {
    # 70ED15 is action initialization, not a frame tick. Its later 916A90
    # clears a sphere created there. The 714CE0 post-update epilogue runs
    # while idle (60 Hz observed), after that initialization and cleanup.
    'name': 'HE_PurificationPlayerTick', 'rva': 0x715D3B, 'length': 8,
    'code_capacity': 0x800,
    'purpose': 'Poll scoped fresh Space in the verified continuous controller post-update, including idle, and create native purification after action initialization has finished',
    'asm': '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
mov r11, {data}
''' + player_guard('purify_tick') + '''cmp r10, qword ptr [rsi+0x50]
jne purify_tick_done
inc dword ptr [r11+0xE08]
mov rcx, rsi
cmp dword ptr [r11+0xFC0], 1
je purify_tick_consume
cmp dword ptr [r11+0xE00], 1
jne purify_tick_done
mov rdx, qword ptr [r11+0xFB0]
test rdx, rdx
je purify_tick_inactive
cmp dword ptr [rdx+0x60], 0
jne purify_tick_done
''' + hidden_hint_scope('purify_tick') + '''mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_block_input
cmp byte ptr [rax+0x4A], 1
jne purify_tick_block_input
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_block_input
mov r9, qword ptr [rax+8]
test r9, r9
je purify_tick_block_input
cmp byte ptr [r9], 1
jne purify_tick_block_input
mov rax, {native_key_settings}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_block_input
mov edx, dword ptr [rax+0xC44]
cmp edx, 1
ja purify_tick_block_input
mov rax, {native_stance_key_vector}
cmp qword ptr [rax+8], 1
jb purify_tick_block_input
cmp qword ptr [rax+8], 128
ja purify_tick_block_input
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_block_input
cmp dword ptr [rax+rdx*4+8], 0xFF
jne purify_tick_block_input
mov eax, dword ptr [rax+rdx*4]
cmp eax, 0xFF
jae purify_tick_block_input
cmp eax, dword ptr [r11+0xFBC]
je purify_tick_key_ready
mov dword ptr [r11+0xFBC], eax
mov dword ptr [r11+0xFA8], 1
purify_tick_key_ready:
test byte ptr [r9+rax+1], 0x80
je purify_tick_key_released
cmp dword ptr [r11+0xFA8], 0
jne purify_tick_done
mov dword ptr [r11+0xFA8], 1
mov dword ptr [r11+0xFC0], 1
mov dword ptr [r11+0xFB8], 1
inc dword ptr [r11+0xFA4]
inc dword ptr [r11+0xFAC]
purify_tick_consume:
mov dword ptr [r11+0xFC0], 0
cmp dword ptr [r11+0xFB8], 1
jne purify_tick_done
cmp r10, qword ptr [r11+0xF98]
jne purify_tick_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xFA0]
jne purify_tick_done
mov rax, {tutorial_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_done
cmp rax, qword ptr [r11+0xF90]
jne purify_tick_done
mov rdx, qword ptr [r11+0xFB0]
test rdx, rdx
je purify_tick_done
''' + hint_scope('purify_tick', 'rdx') + '''mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_done
cmp byte ptr [rax+0x4A], 1
jne purify_tick_done
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_done
mov rax, qword ptr [rax+8]
test rax, rax
je purify_tick_done
cmp byte ptr [rax], 1
jne purify_tick_done
mov rax, qword ptr [r10+0x230]
test rax, rax
je purify_tick_done
mov r8, qword ptr [rax+8]
test r8, r8
je purify_tick_done
cmp r8, rcx
jne purify_tick_done
mov rax, qword ptr [r10+0xB8]
test rax, rax
je purify_tick_done
cmp r10, qword ptr [rax]
jne purify_tick_done
mov rax, qword ptr [r10+0x240]
test rax, rax
je purify_tick_done
cmp r10, qword ptr [rax]
jne purify_tick_done
mov rax, qword ptr [r8]
test rax, rax
je purify_tick_done
mov rdx, {native_controller_special_query}
cmp rdx, qword ptr [rax+0x180]
jne purify_tick_done
mov rax, {native_shot_resource_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_done
mov rax, qword ptr [rax]
test rax, rax
je purify_tick_done
mov rdx, qword ptr [rax+0x468]
test rdx, rdx
je purify_tick_done
mov rax, qword ptr [rax+0x470]
sub rax, rdx
cmp rax, 0x4F80
jb purify_tick_done
cmp rax, 0x100000
ja purify_tick_done
test eax, 0x7F
jne purify_tick_done
mov rax, {native_purification_actor_manager}
cmp qword ptr [rax], 0
je purify_tick_done
sub rsp, 0x80
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov rcx, r8
mov edx, 1
call {native_purification_wave}
mov r11, {data}
mov eax, dword ptr [rsp]
mov dword ptr [r11+0xFC8], eax
mov rcx, rsi
call {native_purification_visual}
mov r11, {data}
inc dword ptr [r11+0xFC4]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x80
jmp purify_tick_done
purify_tick_key_released:
mov dword ptr [r11+0xFA8], 0
jmp purify_tick_done
purify_tick_block_input:
mov dword ptr [r11+0xFA8], 1
jmp purify_tick_done
purify_tick_inactive:
mov dword ptr [r11+0xE00], 0
mov dword ptr [r11+0xFB8], 0
purify_tick_done:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
lea r11, [rsp+0xB0]
jmp {return}
''',
}

PURIFICATION_ORIGIN = {
    'name': 'HE_PurificationOrigin', 'rva': 0x7440A8, 'length': 10,
    'purpose': 'Use the current Hino-Enma player root for the scoped DB3 purification collision, instead of the human tenth-bone anchor; retain native creation, visual helper and success bookkeeping',
    'asm': '''movdqa xmmword ptr [rbp-0x29], xmm0
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0xFB8], 1
jne purify_origin_done
cmp r8d, 0xDB3
jne purify_origin_done
''' + player_guard('purify_origin') + '''cmp r10, r13
jne purify_origin_done
cmp r10, qword ptr [r11+0xF98]
jne purify_origin_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xFA0]
jne purify_origin_done
mov rax, qword ptr [r10+0x230]
test rax, rax
je purify_origin_done
cmp r15, qword ptr [rax+8]
jne purify_origin_done
cmp r10, qword ptr [r15+0x50]
jne purify_origin_done
mov rdx, qword ptr [r11+0xFB0]
test rdx, rdx
je purify_origin_done
''' + hint_scope('purify_origin', 'rdx') + '''mov dword ptr [rbp-0x49], -1
mov qword ptr [rbp-0x29], 0
mov qword ptr [rbp-0x21], 0
mov dword ptr [rbp-0x1D], 0x3F800000
inc dword ptr [r11+0xFCC]
jmp purify_origin_done
purify_origin_inactive:
purify_origin_done:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
mov qword ptr [rsp+0x20], r13
jmp {return}
''',
}

PURIFICATION_COLLISION_ORIGIN = {
    'name': 'HE_PurificationCollisionOrigin', 'rva': 0x7DDE35, 'length': 5,
    'purpose': 'Anchor only the current dojo Hino-Enma purification attack sphere to bone zero; retain native geometry, ownership, lifetime, hit decisions and success notification',
    'asm': '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0xFB8], 1
jne purify_collision_done
''' + player_guard('purify_collision') + '''cmp rbp, r10
jne purify_collision_done
test rdi, rdi
je purify_collision_done
cmp rcx, rdi
jne purify_collision_done
cmp qword ptr [rdi+8], r10
jne purify_collision_done
cmp r10, qword ptr [r11+0xF98]
jne purify_collision_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xFA0]
jne purify_collision_done
mov rax, {tutorial_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_collision_done
cmp rax, qword ptr [r11+0xF90]
jne purify_collision_done
mov rax, {native_shot_resource_manager}
mov rax, qword ptr [rax]
test rax, rax
je purify_collision_done
mov rax, qword ptr [rax]
test rax, rax
je purify_collision_done
mov rdx, qword ptr [rax+0x468]
test rdx, rdx
je purify_collision_done
mov rax, qword ptr [rax+0x470]
sub rax, rdx
cmp rax, 0x4F80
jb purify_collision_done
cmp rax, 0x100000
ja purify_collision_done
test eax, 0x7F
jne purify_collision_done
lea rax, [rdx+0x1D80]
cmp rbx, rax
je purify_collision_resource
lea rax, [rdx+0x4E80]
cmp rbx, rax
je purify_collision_resource
lea rax, [rdx+0x4F00]
cmp rbx, rax
jne purify_collision_done
purify_collision_resource:
test byte ptr [rbx+0x46], 0x10
je purify_collision_done
mov rdx, qword ptr [r11+0xFB0]
test rdx, rdx
je purify_collision_done
''' + hint_scope('purify_collision', 'rdx') + '''mov eax, dword ptr [rsp+0x20]
mov dword ptr [r11+0xFF0], eax
mov qword ptr [rsp+0x20], 0
inc dword ptr [r11+0xFD0]
mov dword ptr [r11+0xFD4], esi
mov qword ptr [r11+0xFD8], rdi
mov qword ptr [r11+0xFE0], rbx
mov qword ptr [r11+0xFE8], rbp
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
call {native_purification_set_collision_origin}
pushfq
push rax
push r11
mov r11, {data}
mov eax, dword ptr [rdi+0x20]
mov dword ptr [r11+0xFF4], eax
mov eax, dword ptr [rdi+0xF4]
mov dword ptr [r11+0xFF8], eax
mov eax, dword ptr [rdi+0xF8]
mov dword ptr [r11+0xFFC], eax
pop r11
pop rax
popfq
jmp {return}
purify_collision_inactive:
purify_collision_done:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
call {native_purification_set_collision_origin}
jmp {return}
''',
}

PURIFICATION_HOOKS = [PURIFICATION_INPUT, PURIFICATION_TICK, PURIFICATION_ORIGIN,
                      PURIFICATION_COLLISION_ORIGIN]
