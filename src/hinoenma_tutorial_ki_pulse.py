"""Notify Ki Pulse teaching on a fresh native STANCE keyboard press.

The observed basic-dojo hint is the sole scope. Keyboard state comes from
the game's DirectInput buffer (E63180), with its own ready/focus flags. The
native STANCE keyboard binding is group 2, entry 0, currently scan code 57
(Space). No OS-wide keyboard polling, native calls, or actual Ki Pulse effects.
"""
from hinoenma_tutorial import player_guard

KI_PULSE_HINT_TEXT = '残心：攻击后，在蓝色的光芒朝身旁聚集而来的期间按下^08~STANCE~'
KI_PULSE_TARGETS = {'native_input_manager': 0x1B78658,
                    'native_window_owner': 0x1930090,
                    'native_key_settings': 0x189F420,
                    'native_stance_key_vector': 0x17F46D0}


def text_comparisons():
    raw = KI_PULSE_HINT_TEXT.encode('utf-16le')
    result = []
    for offset in range(0, len(raw), 8):
        chunk = raw[offset:offset + 8]
        if len(chunk) == 8:
            result += [f'mov rax, 0x{int.from_bytes(chunk, "little"):X}',
                       f'cmp qword ptr [r9+{offset}], rax']
        else:
            assert len(chunk) in (2, 4)
            width = 'word' if len(chunk) == 2 else 'dword'
            result += [f'cmp {width} ptr [r9+{offset}], 0x{int.from_bytes(chunk, "little"):X}']
        result += ['jne ki_pulse_hint_inactive']
    return '\n'.join(result) + '\n'


KI_PULSE_HINT_SPACE = {
    'name': 'HE_KiPulseHintSpace', 'rva': 0xD49820, 'length': 6,
    'purpose': 'Notify one ephemeral native Ki Pulse teaching count on a fresh game STANCE keyboard press only during the exact observed Ki Pulse hint; preserve all real combat and resource mechanics',
    'asm': '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
mov rbx, rcx
mov r11, {data}
mov rax, {tutorial_ui_owner}
mov rax, qword ptr [rax]
test rax, rax
je ki_pulse_hint_done
cmp rbx, qword ptr [rax+0x338]
jne ki_pulse_hint_done
cmp dword ptr [rbx+0x60], 2
jne ki_pulse_hint_inactive
cmp qword ptr [rbx+0xA0], HINT_LENGTH
jne ki_pulse_hint_inactive
cmp qword ptr [rbx+0xA8], HINT_LENGTH
jb ki_pulse_hint_inactive
mov r9, qword ptr [rbx+0x90]
test r9, r9
je ki_pulse_hint_inactive
'''.replace('HINT_LENGTH', str(len(KI_PULSE_HINT_TEXT))) + text_comparisons()
    + player_guard('ki_pulse_hint') + '''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je ki_pulse_hint_done
cmp dword ptr [r11+0xF88], 1
jne ki_pulse_hint_new_epoch
cmp r8, qword ptr [r11+0xF60]
jne ki_pulse_hint_new_epoch
cmp r10, qword ptr [r11+0xF68]
jne ki_pulse_hint_new_epoch
cmp rbx, qword ptr [r11+0xF80]
jne ki_pulse_hint_new_epoch
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xF70]
je ki_pulse_hint_epoch_ready
ki_pulse_hint_new_epoch:
mov qword ptr [r11+0xF60], r8
mov qword ptr [r11+0xF68], r10
mov qword ptr [r11+0xF80], rbx
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0xF70], eax
mov dword ptr [r11+0xF74], 0
mov dword ptr [r11+0xF78], 1
mov dword ptr [r11+0xF88], 1
ki_pulse_hint_epoch_ready:
mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je ki_pulse_hint_block_input
cmp byte ptr [rax+0x4A], 1
jne ki_pulse_hint_block_input
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je ki_pulse_hint_block_input
mov r9, qword ptr [rax+0x08]
test r9, r9
je ki_pulse_hint_block_input
cmp byte ptr [r9], 1
jne ki_pulse_hint_block_input
mov rax, {native_key_settings}
mov rax, qword ptr [rax]
test rax, rax
je ki_pulse_hint_block_input
mov edx, dword ptr [rax+0xC44]
cmp edx, 1
ja ki_pulse_hint_block_input
mov rax, {native_stance_key_vector}
cmp qword ptr [rax+0x08], 1
jb ki_pulse_hint_block_input
cmp qword ptr [rax+0x08], 128
ja ki_pulse_hint_block_input
mov rax, qword ptr [rax]
test rax, rax
je ki_pulse_hint_block_input
cmp dword ptr [rax+rdx*4+0x08], 0xFF
jne ki_pulse_hint_block_input
mov eax, dword ptr [rax+rdx*4]
cmp eax, 0xFF
jae ki_pulse_hint_block_input
cmp eax, dword ptr [r11+0xF8C]
je ki_pulse_hint_key_ready
mov dword ptr [r11+0xF8C], eax
mov dword ptr [r11+0xF78], 1
ki_pulse_hint_key_ready:
test byte ptr [r9+rax+0x01], 0x80
je ki_pulse_hint_key_released
cmp dword ptr [r11+0xF78], 0
jne ki_pulse_hint_done
mov dword ptr [r11+0xF78], 1
cmp dword ptr [r8+0x260], 0x7FFFFFFF
jae ki_pulse_hint_done
inc dword ptr [r8+0x260]
inc dword ptr [r11+0xF74]
inc dword ptr [r11+0xF7C]
jmp ki_pulse_hint_done
ki_pulse_hint_key_released:
mov dword ptr [r11+0xF78], 0
jmp ki_pulse_hint_done
ki_pulse_hint_block_input:
mov dword ptr [r11+0xF78], 1
jmp ki_pulse_hint_done
ki_pulse_hint_inactive:
mov dword ptr [r11+0xF74], 0
mov dword ptr [r11+0xF78], 1
mov dword ptr [r11+0xF88], 0
ki_pulse_hint_done:
pop rbx
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
push rbx
sub rsp, 0x30
jmp {return}
''',
}