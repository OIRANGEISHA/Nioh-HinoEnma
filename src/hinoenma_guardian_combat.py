"""Candidate: digit9 dispatches the native Living Weapon child summon.

William action4008 local44 calls724790 with a selected guardian model, the
pointer-free common spawn descriptor, slot0 and the child's action1505.
The child's controller receives its real owner through the native holder.
No William action, direct damage, gauge or actor-stat write is requested.
This module is not selected by the builder until its review and tests pass.
"""
import struct

from hinoenma_guardian_repeat import guardian_repeat_hooks
from hinoenma_guardian_spirit import GUARDIAN_START_ASM

GUARDIAN_COMBAT_TARGETS = {
    'native_guardian_selected_model': 0x7327B0,
    'native_guardian_combat_spawn': 0x724790,
    'native_guardian_database_manager': 0x1871720,
    'native_guardian_database_hash': 0x18BACD0,
}

# Native common action4008 event44; it contains no heap or module pointers.
# Bone0 is the native root; action1505 belongs to the guardian, not the player.
NATIVE_COMBAT_DESCRIPTOR = bytes.fromhex(
    '0000ffff000000000000ffffffffffff00000000ffffff07ffffffff00000000'
    '00006aff000000000000ffffff00ffffffffffff00000000000000000000ffff'
    'ffff6464646464646464ffffffffffffffffe105ffffffffffffffffffffffff'
    'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'
)


def _descriptor_asm():
    if (len(NATIVE_COMBAT_DESCRIPTOR) != 0x80 or
            NATIVE_COMBAT_DESCRIPTOR[0x17] != 7 or
            struct.unpack_from('<h', NATIVE_COMBAT_DESCRIPTOR, 0x1C)[0] != 0 or
            struct.unpack_from('<h', NATIVE_COMBAT_DESCRIPTOR, 0x22)[0] != -150 or
            struct.unpack_from('<H', NATIVE_COMBAT_DESCRIPTOR, 0x52)[0] != 1505):
        raise ValueError('Native guardian combat descriptor layout changed.')
    return ''.join(f'mov rax, 0x{int.from_bytes(NATIVE_COMBAT_DESCRIPTOR[at:at+8],"little"):016X}\n'
                   f'mov qword ptr [rsp+0x{0x40+at:X}], rax\n'
                   for at in range(0, 0x80, 8))


GUARDIAN_COMBAT_ASM = '''living_weapon_guardian_start:
push rbx
push rdi
push rsi
sub rsp, 0xC0
mov rdi, rcx
mov rax, qword ptr [rdi+0x230]
test rax, rax
je living_weapon_guardian_done
cmp qword ptr [rax], rdi
jne living_weapon_guardian_done
mov rsi, qword ptr [rax+8]
test rsi, rsi
je living_weapon_guardian_done
cmp qword ptr [rsi+0x50], rdi
jne living_weapon_guardian_done
cmp qword ptr [rsi+0x730], 0
jne living_weapon_guardian_done
cmp qword ptr [rsi+0x720], 0
je living_weapon_guardian_done
cmp qword ptr [rdi+0x18], 0
je living_weapon_guardian_done
mov rax, qword ptr [rdi+0xA8]
test rax, rax
je living_weapon_guardian_done
cmp dword ptr [rax+0x10], 0
jne living_weapon_guardian_done
mov rax, qword ptr [rdi+0x240]
test rax, rax
je living_weapon_guardian_done
cmp qword ptr [rax], rdi
jne living_weapon_guardian_done
cmp qword ptr [rax+0x108], rdi
jne living_weapon_guardian_done
mov rcx, qword ptr [rax+0xB98]
test rcx, rcx
jne living_weapon_guardian_stats_ready
lea rcx, [rax+0x9D8]
living_weapon_guardian_stats_ready:
mov rax, qword ptr [rcx+0x1A8]
test rax, rax
je living_weapon_guardian_done
cmp dword ptr [rax+0x28], 0
jle living_weapon_guardian_done
mov rax, {native_guardian_database_manager}
mov rax, qword ptr [rax]
test rax, rax
je living_weapon_guardian_done
mov rax, qword ptr [rax+0x70]
test rax, rax
je living_weapon_guardian_done
mov rax, qword ptr [rax+0x428]
test rax, rax
je living_weapon_guardian_done
cmp dword ptr [rax+4], 0
je living_weapon_guardian_done
cmp dword ptr [rax+4], 4096
ja living_weapon_guardian_done
mov rax, {native_guardian_database_hash}
mov rax, qword ptr [rax]
test rax, rax
je living_weapon_guardian_done
mov rdx, qword ptr [rax+8]
test rdx, rdx
je living_weapon_guardian_done
mov rax, qword ptr [rax+0x10]
sub rax, rdx
jbe living_weapon_guardian_done
cmp rax, 0x8000
ja living_weapon_guardian_done
test eax, 7
jne living_weapon_guardian_done
mov rcx, rsi
call {native_guardian_selected_model}
test eax, eax
jle living_weapon_guardian_done
mov ebx, eax
''' + _descriptor_asm() + '''mov dword ptr [rsp+0x20], 0
mov dword ptr [rsp+0x28], 1505
xor r9d, r9d
lea r8, [rsp+0x40]
mov edx, ebx
mov rcx, rsi
call {native_guardian_combat_spawn}
living_weapon_guardian_done:
add rsp, 0xC0
pop rsi
pop rdi
pop rbx
ret
'''


def guardian_combat_hooks():
    hooks = guardian_repeat_hooks()
    first = dict(hooks[0])
    if first['asm'].count(GUARDIAN_START_ASM) != 1:
        raise ValueError('Native guardian display helper changed.')
    first['asm'] = first['asm'].replace(GUARDIAN_START_ASM, GUARDIAN_COMBAT_ASM)
    marker = ('cmp qword ptr [r10+0x2C0], 0\nje living_weapon_done\n'
              'cmp qword ptr [r10+0x2C8], 0\nje living_weapon_done\n')
    if first['asm'].count(marker) != 1:
        raise ValueError('Active display component requirement changed.')
    first['asm'] = first['asm'].replace(marker, '')
    first['purpose'] = ('Fresh main digit9 starts native Living Weapon or requests its selected '
        'guardian native combat child when idle; current player/controller/epoch/input/menu '
        'guards retained; busy native summon slot0 is never overwritten; no player action '
        'or direct damage/charge/gauge/stat write; native child owner, stat calculation and '
        'retirement retained')
    return [first, *hooks[1:]]
