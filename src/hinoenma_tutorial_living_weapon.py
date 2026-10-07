"""A T press acknowledges only the observed full-charge Living Weapon lesson.

Hino-Enma has no Living Weapon start event in her loaded action table. This
explicit teaching substitute preserves her native actions and all resources.
It never calls the native initializer or installs William's weapon models.
The existing script getter consumes manager+280; this hook credits it once
per exact hint/player/spawn epoch, after a released then pressed main T key.
"""
import copy

from hinoenma_manual_purification import menu_guard
from hinoenma_tutorial import player_guard
from hinoenma_tutorial_ki_pulse import KI_PULSE_HINT_SPACE, KI_PULSE_HINT_TEXT
from hinoenma_tutorial_ki_pulse import text_comparisons as ki_text_comparisons

LIVING_WEAPON_HINT_TEXT = ('九十九武器：（在守护灵的精华量表全满的状态下）'
                          '^08~INTERACT~＋^08~HARD_ATTACK~')
LIVING_WEAPON_HINT_TARGETS = {}
LIVING_WEAPON_KEY_SCAN = 0x14  # Main keyboard T in the game's DirectInput buffer.


def text_comparisons():
    raw = LIVING_WEAPON_HINT_TEXT.encode('utf-16le')
    lines = []
    offset = 0
    while offset < len(raw):
        width = next(size for size in (8, 4, 2) if size <= len(raw)-offset)
        value = int.from_bytes(raw[offset:offset+width], 'little')
        if width == 8:
            lines += [f'mov rax, 0x{value:X}', f'cmp qword ptr [r9+{offset}], rax']
        else:
            operand = 'dword' if width == 4 else 'word'
            lines += [f'cmp {operand} ptr [r9+{offset}], 0x{value:X}']
        lines += ['jne living_weapon_hint_inactive']
        offset += width
    return '\n'.join(lines)+'\n'


def living_weapon_hint_hook():
    result = copy.deepcopy(KI_PULSE_HINT_SPACE)
    body = result['asm']
    guard = player_guard('ki_pulse_hint')
    assert body.count(guard) == 1
    body = body.replace(guard, guard.replace('ki_pulse_hint_done', 'ki_pulse_hint_inactive'))
    assert body.count(ki_text_comparisons()) == 1
    body = body.replace(ki_text_comparisons(), text_comparisons())
    for field in ('A0', 'A8'):
        body = body.replace(f'[rbx+0x{field}], {len(KI_PULSE_HINT_TEXT)}',
                            f'[rbx+0x{field}], {len(LIVING_WEAPON_HINT_TEXT)}')
    body = body.replace('ki_pulse_hint', 'living_weapon_hint')
    assert body.count('mov rbx, rcx\n') == 1
    body = body.replace('mov rbx, rcx\n', '')
    body = body.replace('test r8, r8\nje living_weapon_hint_done\n',
                        'test r8, r8\nje living_weapon_hint_inactive\n')
    for old, new in dict(F60='E18', F68='E20', F80='E28', F70='E30',
                         F74='E34', F78='E38', F7C='E3C', F88='E40', F8C='E44').items():
        body = body.replace('0x'+old, '0x'+new)
    body = body.replace('[r8+0x260]', '[r8+0x280]')
    menu = menu_guard().replace('manual_purify', 'living_weapon_menu').replace(
        'living_weapon_menu_block_input', 'living_weapon_hint_block_input')
    marker = 'mov rax, {native_input_manager}\n'
    assert body.count(marker) == 1
    body = body.replace(marker, menu+'''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je living_weapon_hint_block_input
'''+marker)
    first = body.index('mov rax, {native_key_settings}\n')
    last = body.index('cmp dword ptr [r11+0xE38], 0\n', first)
    body = body[:first]+'''test byte ptr [r9+0x15], 0x80
je living_weapon_hint_key_released
'''+body[last:]
    marker = 'cmp dword ptr [r8+0x280], 0x7FFFFFFF\njae living_weapon_hint_done\n'
    assert body.count(marker) == 1
    body = body.replace(marker, '''cmp dword ptr [r11+0xE34], 0
jne living_weapon_hint_done
cmp byte ptr [r9+0x115], 0
je living_weapon_hint_done
mov rdx, qword ptr [r10+0x240]
test rdx, rdx
je living_weapon_hint_done
cmp r10, qword ptr [rdx]
jne living_weapon_hint_done
cmp r10, qword ptr [rdx+0x108]
jne living_weapon_hint_done
cmp dword ptr [rdx+0xB0], 0
jne living_weapon_hint_done
mov eax, dword ptr [rdx+0xC8]
test eax, eax
jle living_weapon_hint_done
cmp dword ptr [rdx+0xC0], eax
jl living_weapon_hint_done
cmp dword ptr [r8+0x280], 0
jne living_weapon_hint_done
''')
    replay = 'push rbx\nsub rsp, 0x30\njmp {return}\n'
    assert body.count(replay) == 1
    # This is the visible-state branch, reached by D49840 when state==2.
    # The later switch tail at D49842 is unreachable for that state.
    body = body.replace(replay, 'cmp qword ptr [rbx+0xC8], 0\njmp {return}\n')
    result.update(name='HE_LivingWeaponHintT', rva=0xD498C0, length=8,
        code_offset=0xC400, code_capacity=0xC00,
        purpose='One exact full-charge dojo Living Weapon teaching credit on fresh main T; native Boss attacks, charge, active state, equipment and save progression untouched',
        asm=body)
    return result
