"""Main digit9 starts the native Living Weapon state on an idle Hino player.

Use 7B5AE0's real initializer, not the 745A90 animation wrapper. The wrapper
sets animation-in-progress flags that require a later SetAction to release.
Here the existing native update drains duration and native 7B65F0 ends it.

During this captured player's active epoch only, skip weapon attachment VFX
installation at 7B5FC0. Its +55 applied latch stays zero, so the matching
native cleanup 7B66E0 does not remove resources this path never installed.
The native kind60 factory's suppress-visuals boolean also skips paired enchant
attachment creation/cleanup while preserving the element/power outputs.
No charge, duration, damage, life, equipment or action is written by the hooks.
"""
from hinoenma_attributes import VOLATILE_SAVE, VOLATILE_RESTORE
from hinoenma_manual_purification import menu_guard
from hinoenma_tutorial import player_guard

LIVING_WEAPON_TARGETS = {'native_living_weapon_start': 0x7B5AE0}
LIVING_WEAPON_KEY_SCAN = 0x0A

LIVING_WEAPON_DIGIT9 = {
    'name': 'HE_LivingWeaponDigitNine', 'rva': 0x715D4B, 'length': 9,
    'code_offset': 0xD000, 'code_capacity': 0x1000,
    'purpose': 'Fresh main digit9 starts native Living Weapon for the captured idle full-charge Hino player outside menus; native duration, effects and automatic ending retained',
    'asm': VOLATILE_SAVE.replace('{frame}', '0x80')+'''mov r11, {data}
mov r10, qword ptr [r11+0x10]
cmp r10, qword ptr [rsi+0x50]
jne living_weapon_done
'''+player_guard('living_weapon').replace('living_weapon_done','living_weapon_block_input')+'''test byte ptr [rax+0x04], 3
jne living_weapon_block_input
cmp dword ptr [r11+0x1C], 0
je living_weapon_block_input
mov rdx, qword ptr [r10+0x240]
test rdx, rdx
je living_weapon_block_input
cmp r10, qword ptr [rdx]
jne living_weapon_block_input
cmp r10, qword ptr [rdx+0x108]
jne living_weapon_block_input
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE4C]
je living_weapon_epoch_ready
mov dword ptr [r11+0xE4C], eax
mov dword ptr [r11+0xE44], 1
mov dword ptr [r11+0xE50], 0
mov dword ptr [r11+0xE5C], 0
living_weapon_epoch_ready:
cmp dword ptr [rdx+0xB0], 1
je living_weapon_keep_active
mov dword ptr [r11+0xE50], 0
living_weapon_keep_active:
mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je living_weapon_block_input
cmp byte ptr [rax+0x4A], 1
jne living_weapon_block_input
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je living_weapon_block_input
mov r9, qword ptr [rax+8]
test r9, r9
je living_weapon_block_input
cmp byte ptr [r9], 1
jne living_weapon_block_input
'''+menu_guard().replace('manual_purify_block_input','living_weapon_block_input').replace('manual_purify_aux_closed','living_weapon_menu_aux_closed')+'''test byte ptr [r9+0x0B], 0x80
je living_weapon_key_released
cmp dword ptr [r11+0xE44], 0
jne living_weapon_done
mov dword ptr [r11+0xE44], 1
cmp byte ptr [r9+0x10B], 0
je living_weapon_done
inc dword ptr [r11+0xE54]
mov rax, qword ptr [rsi+0x58]
test rax, rax
je living_weapon_done
cmp dword ptr [rax], 0
jne living_weapon_done
bt qword ptr [rsi+0x40], 40
jc living_weapon_done
mov rax, qword ptr [r10+0x230]
test rax, rax
je living_weapon_done
cmp r10, qword ptr [rax]
jne living_weapon_done
cmp rsi, qword ptr [rax+8]
jne living_weapon_done
mov rdx, qword ptr [r10+0x240]
cmp dword ptr [rdx+0xB0], 0
jne living_weapon_done
cmp byte ptr [rdx+0xB4], 0
jne living_weapon_done
cmp word ptr [rdx+0x104], 0
jne living_weapon_done
cmp qword ptr [rdx+0x110], 0
jne living_weapon_done
cmp qword ptr [rdx+0x118], 0
jne living_weapon_done
mov eax, dword ptr [rdx+0xB8]
sub eax, 1
cmp eax, 4
ja living_weapon_done
mov eax, dword ptr [rdx+0xC8]
test eax, eax
jle living_weapon_done
cmp dword ptr [rdx+0xC0], eax
jl living_weapon_done
xorps xmm0, xmm0
ucomiss xmm0, dword ptr [rdx+0xD0]
jae living_weapon_done
jp living_weapon_done
cmp dword ptr [rdx+0xD0], 0x7F800000
jae living_weapon_done
cmp r10, qword ptr [rdx+0x1218]
jne living_weapon_done
mov rax, qword ptr [rdx+0x1238]
test rax, rax
je living_weapon_done
cmp qword ptr [rax], 0
je living_weapon_done
cmp qword ptr [rax+8], 0
je living_weapon_done
mov dword ptr [r11+0xE50], 1
mov dword ptr [r11+0xE5C], 1
lea rcx, [rdx+0xB0]
call {native_living_weapon_start}
mov r11, {data}
mov dword ptr [r11+0xE5C], 0
mov rax, qword ptr [rsi+0x50]
mov rax, qword ptr [rax+0x240]
cmp dword ptr [rax+0xB0], 1
jne living_weapon_failed
inc dword ptr [r11+0xE48]
jmp living_weapon_done
living_weapon_failed:
mov dword ptr [r11+0xE50], 0
jmp living_weapon_done
living_weapon_key_released:
mov dword ptr [r11+0xE44], 0
jmp living_weapon_done
living_weapon_block_input:
mov dword ptr [r11+0xE44], 1
living_weapon_done:
'''+VOLATILE_RESTORE.replace('{frame}', '0x80')+'''mov rsi, qword ptr [r11+0x38]
movaps xmm6, xmmword ptr [r11-0x10]
jmp {return}
'''
}

LIVING_WEAPON_VISUAL_GUARD = {
    'name': 'HE_LivingWeaponBossAttachmentGuard', 'rva': 0x7B5FC0, 'length': 11,
    'code_offset': 0xE000, 'code_capacity': 0x400,
    'purpose': 'Keep uninstalled weapon-attachment resources and applied latch untouched only during digit9 Living Weapon on the captured current Hino player; native William and NPC visuals remain original',
    'asm': '''pushfq
push rax
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0xE50], 1
jne living_weapon_visual_original
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE4C]
jne living_weapon_visual_original
'''+player_guard('living_weapon_visual').replace('living_weapon_visual_done','living_weapon_visual_original')+'''cmp r10, qword ptr [rcx+0x58]
jne living_weapon_visual_original
mov rax, qword ptr [r10+0x240]
test rax, rax
je living_weapon_visual_original
add rax, 0xB0
cmp rax, rcx
jne living_weapon_visual_original
cmp dword ptr [rcx], 1
jne living_weapon_visual_original
cmp byte ptr [rcx+0x55], 0
jne living_weapon_visual_original
inc dword ptr [r11+0xE58]
pop r11
pop r10
pop rax
popfq
ret
living_weapon_visual_original:
pop r11
pop r10
pop rax
popfq
mov rax, rsp
push rbx
sub rsp, 0xB0
jmp {return}
'''
}

LIVING_WEAPON_ELEMENT_VISUAL_PARAMETER = {
    'name': 'HE_LivingWeaponElementVisualParameter', 'rva': 0x7B5BA7, 'length': 5,
    'code_offset': 0xE400, 'code_capacity': 0x400,
    'purpose': 'Use native kind60 suppress-visuals boolean only around the synchronous captured Hino digit9 initializer; preserve element/power output and native paired cleanup, other initializers retain original argument',
    'asm': '''pushfq
push rax
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0xE5C], 1
jne living_weapon_element_original
cmp dword ptr [r11+0xE50], 1
jne living_weapon_element_original
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE4C]
jne living_weapon_element_original
'''+player_guard('living_weapon_element').replace('living_weapon_element_done','living_weapon_element_original')+'''cmp r10, qword ptr [rbx+0x58]
jne living_weapon_element_original
mov rax, qword ptr [r10+0x240]
test rax, rax
je living_weapon_element_original
add rax, 0xB0
cmp rax, rbx
jne living_weapon_element_original
cmp dword ptr [rbx], 1
jne living_weapon_element_original
pop r11
pop r10
pop rax
popfq
mov byte ptr [rsp+0x20], 1
jmp {return}
living_weapon_element_original:
pop r11
pop r10
pop rax
popfq
mov byte ptr [rsp+0x20], sil
jmp {return}
'''
}


def living_weapon_hooks():
    return [LIVING_WEAPON_DIGIT9, LIVING_WEAPON_VISUAL_GUARD,
            LIVING_WEAPON_ELEMENT_VISUAL_PARAMETER]
