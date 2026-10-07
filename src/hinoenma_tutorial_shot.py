"""Acknowledge the observed shooting lesson with aim plus left mouse.

This is an explicit teaching substitute, not a projectile or damage event.
Only the exact current Chinese hint may credit manager+274 once per epoch.
The aim key follows native group2 entry11 (currently Alt). Left mouse is
the fixed teaching companion, read from the game's E65430 buffer (+1).
No native shooting calls, ammo, damage, gear or Boss skills are changed.
"""
import copy

from hinoenma_manual_purification import menu_guard
from hinoenma_tutorial import player_guard
from hinoenma_tutorial_ki_pulse import KI_PULSE_HINT_SPACE, KI_PULSE_HINT_TEXT
from hinoenma_tutorial_ki_pulse import text_comparisons as ki_text_comparisons

SHOT_HINT_TEXT = ('射击：按住^08~TPS~时 ^08~SHOT~（切换箭弹：^08~NORMAL_BULLET~'
                  '或^08~SPECIAL_BULLET~ 缩放视角：^08~R3~）')
SHOT_HINT_TARGETS = {'shot_hint_state_two': 0xD498C0,
                     'native_mouse_pointer': 0x1B78648}
AIM_BINDING_INDEX = 11


def text_comparisons():
    raw = SHOT_HINT_TEXT.encode('utf-16le')
    lines = []
    for offset in range(0, len(raw), 8):
        chunk = raw[offset:offset+8]
        if len(chunk) == 8:
            lines += [f'mov rax, 0x{int.from_bytes(chunk,"little"):X}',
                      f'cmp qword ptr [r9+{offset}], rax']
        else:
            width = {2: 'word', 4: 'dword'}[len(chunk)]
            lines += [f'cmp {width} ptr [r9+{offset}], 0x{int.from_bytes(chunk,"little"):X}']
        lines += ['jne shot_hint_inactive']
    return '\n'.join(lines)+'\n'


def shot_hint_hook():
    result = copy.deepcopy(KI_PULSE_HINT_SPACE)
    body = result['asm']
    guard = player_guard('ki_pulse_hint')
    assert body.count(guard) == 1
    body = body.replace(guard, guard.replace('ki_pulse_hint_done', 'ki_pulse_hint_inactive'))
    assert body.count(ki_text_comparisons()) == 1
    body = body.replace(ki_text_comparisons(), text_comparisons())
    for field in ('A0', 'A8'):
        body = body.replace(f'[rbx+0x{field}], {len(KI_PULSE_HINT_TEXT)}',
                            f'[rbx+0x{field}], {len(SHOT_HINT_TEXT)}')
    body = body.replace('ki_pulse_hint', 'shot_hint')
    # D4983D is after the native widget load and first state subtraction.
    assert body.count('mov rbx, rcx\n') == 1
    body = body.replace('mov rbx, rcx\n', '')
    body = body.replace('test r8, r8\nje shot_hint_done\n',
                        'test r8, r8\nje shot_hint_inactive\n')
    for old, new in dict(F60='ED0', F68='ED8', F70='EE8', F74='EF4',
                         F78='EEC', F7C='EF8', F80='EE0', F88='EF0', F8C='EFC').items():
        body = body.replace('0x'+old, '0x'+new)
    body = body.replace('[r8+0x260]', '[r8+0x274]')
    menu = menu_guard().replace('manual_purify', 'shot_menu').replace(
        'shot_menu_block_input', 'shot_hint_block_input')
    marker = 'mov rax, {native_input_manager}\n'
    assert body.count(marker) == 1
    body = body.replace(marker, menu + '''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je shot_hint_block_input
''' + marker)
    body = body.replace('cmp qword ptr [rax+0x08], 1\n',
                        'cmp qword ptr [rax+0x08], 12\n')
    # Six dwords per native binding; select primary/alternate with the native
    # keyboard mode. Unsupported modifier bindings fail closed.
    body = body.replace('[rax+rdx*4+0x08]', '[rax+rdx*4+0x110]')
    body = body.replace('[rax+rdx*4]', '[rax+rdx*4+0x108]')
    marker = 'test byte ptr [r9+rax+0x01], 0x80\n'
    assert body.count(marker) == 1
    body = body.replace(marker, '''mov rcx, {native_mouse_pointer}
mov rcx, qword ptr [rcx]
test rcx, rcx
je shot_hint_block_input
test byte ptr [r9+rax+0x01], 0x80
''')
    marker = 'je shot_hint_key_released\ncmp dword ptr [r11+0xEEC], 0\n'
    assert body.count(marker) == 1
    body = body.replace(marker, '''je shot_hint_key_released
cmp byte ptr [rcx+0x01], 0
je shot_hint_key_released
cmp dword ptr [r11+0xEEC], 0
''')
    marker = 'cmp dword ptr [r8+0x274], 0x7FFFFFFF\n'
    assert body.count(marker) == 1
    body = body.replace(marker, 'cmp dword ptr [r11+0xEF4], 0\n'
                        'jne shot_hint_done\n'+marker)
    replay = 'push rbx\nsub rsp, 0x30\njmp {return}\n'
    assert body.count(replay) == 1
    body = body.replace(replay, 'sub ecx, 1\nje {shot_hint_state_two}\njmp {return}\n')
    result.update(name='HE_ShotHintAimLeftMouse', rva=0xD4983D, length=5,
        code_offset=0xAC00, code_capacity=0xC00,
        purpose='One exact shooting lesson teaching substitute on a fresh game aim-key plus left-mouse chord; no actual projectile, ammo, damage or Boss skill changes',
        asm=body)
    return result
