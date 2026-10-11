"""Portable query86 protection during the owned Orochi execution windup.

The native Living Weapon readiness query returns false only while the bound
local actor is in action3491, the last ready head remains locked, and its
pending pair is either not yet committed or already points to that head.
No actor, pair, gauge, input, HP or mission state is written. Only the private
diagnostic counter is incremented. Runtime binding and activation are separate.
"""

from hinoenma_orochi_trial import SAVE, RESTORE, player_guard, resources_guard


NATIVE_QUERY_FRAME = (0x736CB0, 0x73AB00)
PRIVATE_COUNTER_OFFSET = 0x1F8
TARGETS = {'native_query_false_epilogue': 0x73AAB1}

PREFIX = 'wp'
SOURCE = SAVE+player_guard(PREFIX)+'''cmp dword ptr [r11+0x74], 1
jne wp_original
cmp rdi, r8
jne wp_original
cmp qword ptr [rsp+0xC0], r8
jne wp_original
test sil, sil
jne wp_original
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne wp_original
cmp dword ptr [rax], 3491
jne wp_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je wp_original
cmp qword ptr [r8+0x5B0], 0
jne wp_original
mov r9, qword ptr [r11+0x18]
test r9, r9
je wp_original
mov rax, qword ptr [r8+0x5D8]
test rax, rax
je wp_pair_not_committed
cmp rax, r9
jne wp_original
wp_pair_not_committed:
cmp qword ptr [r8+0x640], r9
jne wp_original
mov rax, qword ptr [r11+0x20]
cmp qword ptr [r9], rax
jne wp_original
mov rax, qword ptr [r11+0x128]
cmp qword ptr [r9+0x240], rax
jne wp_original
cmp qword ptr [rax], r9
jne wp_original
cmp qword ptr [rax+0x20], 1
jne wp_original
mov rax, qword ptr [r11+0xA8]
cmp qword ptr [rax+0x50], r9
jne wp_original
mov rax, qword ptr [rax+0x58]
test rax, rax
je wp_original
mov edx, dword ptr [r11+0x118]
cmp dword ptr [rax], edx
jne wp_original
mov rax, qword ptr [r11+0x130]
mov rdx, {mission_temp_owner}
cmp qword ptr [rdx], rax
jne wp_original
mov rax, qword ptr [r11+0x120]
cmp byte ptr [rax], 7
jne wp_original
cmp dword ptr [rax+4], 1
jne wp_original
'''+resources_guard(PREFIX)+'''inc dword ptr [r11+0x1F8]
'''+RESTORE+'''jmp {native_query_false_epilogue}
wp_original:
'''+RESTORE+'''mov rax, qword ptr [rcx+0x58]
mov rcx, qword ptr [rax+0x20]
jmp {return}
'''


def pending_weapon_hook():
    """Return unbound assembly and module-relative native entry metadata."""
    return dict(name='HE_OrochiPendingLivingWeaponGuard', rva=0x737769, length=8,
        original='488b4158488b4820', code_offset=0x38000, code_capacity=0x1000,
        asm=SOURCE, purpose='Suppress native query86 Living Weapon readiness only '
        'during the owned3491 Orochi windup before active pairing, with pending '
        'pair absent or equal to the bound last ready head; preserve gauge, input '
        'and all other queries')


def sources():
    """Return a fresh hook and native targets for optional runtime integration."""
    return [pending_weapon_hook()], dict(TARGETS)
