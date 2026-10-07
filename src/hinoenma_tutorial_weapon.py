"""Accept native melee/ranged switch chords in the observed basic-dojo hint.

703D40 changes actual Boss gear and effects; it is not a pure notification.
The existing native weapon-change teaching field is manager+270 (703DF8).
Within this exact combined lesson, acknowledge either requested switch once,
without changing Boss weapons, saved equipment, selected slots or attacks.
"""
import copy

from hinoenma_manual_purification import menu_guard
from hinoenma_tutorial import player_guard
from hinoenma_tutorial_ki_pulse import KI_PULSE_HINT_SPACE, KI_PULSE_HINT_TEXT
from hinoenma_tutorial_ki_pulse import text_comparisons as ki_text_comparisons

WEAPON_HINT_TEXT = ('切换近距离武器：^08~STANCE~+^08~LEFT_RIGHT~　'
                    '切换远距离武器：^08~STANCE~+^08~UP_DOWN~')
SWITCH_BINDINGS = ((7, 0xEC0), (8, 0xEC4), (9, 0xEC8), (10, 0xECC))
WEAPON_HINT_TARGETS = {'weapon_hint_state_one': 0xD49920}


def text_comparisons():
    raw = WEAPON_HINT_TEXT.encode('utf-16le')
    lines = []
    for offset in range(0, len(raw), 8):
        chunk = raw[offset:offset+8]
        if len(chunk) == 8:
            lines += [f'mov rax, 0x{int.from_bytes(chunk,"little"):X}',
                      f'cmp qword ptr [r9+{offset}], rax']
        else:
            width = {2:'word', 4:'dword'}[len(chunk)]
            lines += [f'cmp {width} ptr [r9+{offset}], 0x{int.from_bytes(chunk,"little"):X}']
        lines += ['jne weapon_hint_inactive']
    return '\n'.join(lines)+'\n'


def weapon_hint_hook():
    result = copy.deepcopy(KI_PULSE_HINT_SPACE)
    body = result['asm']
    original_guard = player_guard('ki_pulse_hint')
    assert body.count(original_guard) == 1
    body = body.replace(original_guard, original_guard.replace(
        'ki_pulse_hint_done', 'ki_pulse_hint_inactive'))
    prior_text = ki_text_comparisons()
    assert body.count(prior_text) == 1
    body = body.replace(prior_text, text_comparisons())
    for field in ('A0', 'A8'):
        body = body.replace(f'[rbx+0x{field}], {len(KI_PULSE_HINT_TEXT)}',
                            f'[rbx+0x{field}], {len(WEAPON_HINT_TEXT)}')
    body = body.replace('ki_pulse_hint', 'weapon_hint')
    # Earlier Ki Pulse/defense/purification hooks occupy the prologue. At
    # D49834, RBX already holds the widget and ECX its native state.
    assert body.count('mov rbx, rcx\n') == 1
    body = body.replace('mov rbx, rcx\n', '')
    body = body.replace('test r8, r8\nje weapon_hint_done\n',
                        'test r8, r8\nje weapon_hint_inactive\n')
    offsets = dict(F60='E90',F68='E98',F70='EA8',F74='EB4',F78='EAC',
                   F7C='EB8',F80='EA0',F88='EB0',F8C='EBC')
    for old, new in offsets.items():
        body = body.replace('0x'+old, '0x'+new)
    body = body.replace('[r8+0x260]', '[r8+0x270]')
    # The menu guard uses R8 for its UI owner; reload the lesson manager after it.
    menu = menu_guard().replace('manual_purify', 'weapon_menu').replace(
        'weapon_menu_block_input', 'weapon_hint_block_input')
    marker = 'mov rax, {native_input_manager}\n'
    assert body.count(marker) == 1
    body = body.replace(marker, menu + '''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je weapon_hint_block_input
''' + marker)
    body = body.replace('cmp qword ptr [rax+0x08], 1\n',
                        'cmp qword ptr [rax+0x08], 11\n')
    marker = 'mov eax, dword ptr [rax+rdx*4]\n'
    assert body.count(marker) == 1
    binding_checks = []
    for index, cached in SWITCH_BINDINGS:
        displacement = index * 24
        binding_checks += [f'cmp dword ptr [rax+rdx*4+0x{displacement+8:X}], 0xFF',
            'jne weapon_hint_block_input',
            f'mov ecx, dword ptr [rax+rdx*4+0x{displacement:X}]',
            'cmp ecx, 0xFF', 'jae weapon_hint_block_input',
            f'cmp ecx, dword ptr [r11+0x{cached:X}]',
            f'je weapon_hint_binding_{index}_ready',
            f'mov dword ptr [r11+0x{cached:X}], ecx',
            'mov dword ptr [r11+0xEAC], 1', f'weapon_hint_binding_{index}_ready:']
    body = body.replace(marker, '\n'.join(binding_checks)+'\n'+marker)
    original_test = ('test byte ptr [r9+rax+0x01], 0x80\n'
                     'je weapon_hint_key_released\n')
    chord_test = original_test
    for index, cached in SWITCH_BINDINGS:
        chord_test += (f'mov eax, dword ptr [r11+0x{cached:X}]\n'
                       'test byte ptr [r9+rax+0x01], 0x80\n'
                       'jne weapon_hint_chord_pressed\n')
    chord_test += 'jmp weapon_hint_key_released\nweapon_hint_chord_pressed:\n'
    assert body.count(original_test) == 1
    body = body.replace(original_test, chord_test)
    # One teaching credit per active lesson epoch. Repeated chords do not write
    # extra statistics while the script is still processing the first request.
    marker = 'cmp dword ptr [r8+0x270], 0x7FFFFFFF\n'
    body = body.replace(marker, 'cmp dword ptr [r11+0xEB4], 0\n'
        'jne weapon_hint_done\n'+marker)
    original_replay = 'push rbx\nsub rsp, 0x30\njmp {return}\n'
    assert body.count(original_replay) == 1
    body = body.replace(original_replay,
        'sub ecx, 1\nje {weapon_hint_state_one}\njmp {return}\n')
    result.update(name='HE_WeaponHintSwitch', rva=0xD49834, length=9,
        code_offset=0xA000, code_capacity=0xC00,
        purpose='One exact combined dojo teaching credit for a fresh native STANCE plus melee/ranged switch keyboard chord; real Boss gear, saved equipment and moves preserved',
        asm=body)
    return result
