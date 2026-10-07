"""Record completed recovery only while the current defense/evade hint shows.

The basic dojo does not call Tutorial::GetCountGuard at the stalled step. Its
displayed hint is the native widget's string at +0x90. Compare that exact
observed string and notify the same ephemeral guard counter used by native
successful guard events. No guard, hit reaction, damage or input flags change.
"""
from hinoenma_tutorial import player_guard

DEFENSE_HINT_TEXT = '防御：^08~GUARD~\u3000闪避：^08~DASH~'
DEFENSE_HINT_TARGETS = {'tutorial_ui_owner': 0x189F400}


def text_comparisons():
    raw = DEFENSE_HINT_TEXT.encode('utf-16le')
    result = []
    for offset in range(0, len(raw), 8):
        chunk = raw[offset:offset + 8]
        if len(chunk) == 8:
            result.extend((f'mov rax, 0x{int.from_bytes(chunk, "little"):X}',
                           f'cmp qword ptr [r9+{offset}], rax'))
        else:
            assert len(chunk) == 4
            result.append(f'cmp dword ptr [r9+{offset}], 0x{int.from_bytes(chunk, "little"):X}')
        result.append('jne defense_hint_inactive')
    return '\n'.join(result) + '\n'


DEFENSE_HINT_GUARD = {
    'name': 'HE_DefenseHintRecovery', 'rva': 0xD49829, 'length': 5,
    'purpose': 'Notify native tutorial guard credit after Hino-Enma recovery completes, only while the exact defense/evade teaching hint is displayed',
    'asm': '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
mov r11, {data}
mov rax, {tutorial_ui_owner}
mov rax, qword ptr [rax]
test rax, rax
je defense_hint_done
cmp rbx, qword ptr [rax+0x338]
jne defense_hint_done
cmp dword ptr [rbx+0x60], 2
jne defense_hint_inactive
cmp qword ptr [rbx+0xA0], 26
jne defense_hint_inactive
cmp qword ptr [rbx+0xA8], 26
jb defense_hint_inactive
mov r9, qword ptr [rbx+0x90]
test r9, r9
je defense_hint_inactive
''' + text_comparisons() + player_guard('defense_hint') + '''mov r8, {tutorial_manager}
mov r8, qword ptr [r8]
test r8, r8
je defense_hint_done
cmp dword ptr [r11+0xF58], 1
jne defense_hint_new_epoch
cmp r8, qword ptr [r11+0xF30]
jne defense_hint_new_epoch
cmp r10, qword ptr [r11+0xF38]
jne defense_hint_new_epoch
cmp rbx, qword ptr [r11+0xF50]
jne defense_hint_new_epoch
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xF40]
je defense_hint_epoch_ready
defense_hint_new_epoch:
mov qword ptr [r11+0xF30], r8
mov qword ptr [r11+0xF38], r10
mov qword ptr [r11+0xF50], rbx
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0xF40], eax
mov dword ptr [r11+0xF44], 0
mov dword ptr [r11+0xF48], 1
mov dword ptr [r11+0xF58], 1
defense_hint_epoch_ready:
mov rax, qword ptr [r10+0x230]
test rax, rax
je defense_hint_done
mov rax, qword ptr [rax+0x08]
test rax, rax
je defense_hint_done
cmp r10, qword ptr [rax+0x50]
jne defense_hint_done
mov rax, qword ptr [rax+0x58]
test rax, rax
je defense_hint_not_recovering
cmp dword ptr [rax], 61
jne defense_hint_not_recovering
mov rax, qword ptr [r10+0x38]
test rax, rax
je defense_hint_done
cmp dword ptr [rax+0xEC], 1051
jne defense_hint_not_recovering
cmp dword ptr [r11+0xF48], 0
jne defense_hint_done
mov rdx, qword ptr [r10+0x240]
test rdx, rdx
je defense_hint_done
cmp r10, qword ptr [rdx]
jne defense_hint_done
mov eax, dword ptr [rdx+0x44]
test eax, eax
je defense_hint_done
cmp eax, 0x7F800000
jae defense_hint_done
mov edx, dword ptr [rdx+0x40]
cmp edx, 0x7F800000
jae defense_hint_done
cmp edx, eax
jb defense_hint_done
mov dword ptr [r11+0xF48], 1
cmp dword ptr [r8+0x268], 0x7FFFFFFF
jae defense_hint_done
inc dword ptr [r8+0x268]
inc dword ptr [r11+0xF44]
inc dword ptr [r11+0xF4C]
jmp defense_hint_done
defense_hint_not_recovering:
mov dword ptr [r11+0xF48], 0
jmp defense_hint_done
defense_hint_inactive:
mov dword ptr [r11+0xF44], 0
mov dword ptr [r11+0xF48], 1
mov dword ptr [r11+0xF58], 0
defense_hint_done:
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
mov ecx, dword ptr [rcx+0x60]
test ecx, ecx
jmp {return}
''',
}
