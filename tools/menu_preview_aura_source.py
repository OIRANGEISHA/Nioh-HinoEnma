"""Pure, uninstalled BaseMode aura candidate; never opens a process.

At the verified BaseMode FX CALL, RSI is still the BaseMode owner. Queue the
native, bank-local 99048 action once per completed visual generation, then
restore the exact machine state and execute the displaced FX update once.
The candidate writes only its own generation ledger and private stack.
"""
from __future__ import annotations

import hashlib
import struct

ALLOCATION_SIZE, DATA_OFFSET, CODE_CAPACITY, OWN_DATA_SIZE = 0x5000, 0x4000, 0x4000, 0x30
HOOK_RVA, ORIGINAL = 0x8C59AF, 'E8 CC BB F7 FF'
HOOKS = (('HE_MapPreviewAuraCandidate', HOOK_RVA, ORIGINAL, 0),)
ACTION_ID, EFFECT_ID = 99048, 8040
TARGET_RVAS = dict(base_mode_vtable=0x11FB588, timing_vtable=0x12155B0, playback_vtable=0x12155C0,
    player_slot=0x18A0490, effect_manager=0x189F3F8,
    timing_lookup=0x968230, timing_queue=0x969070, original_update=0x841580)
NATIVE_SPANS = ((HOOK_RVA, 5), (0x8C5330, 0xEC3), (0x969070, 0x20),
    (0x968230, 0xE9), (0x968E10, 0x253), (0x969130, 0x223),
    (0x967AC0, 0x352), (0x966000, 0xAB5), (0x841580, 0x1000),
    (0x11FB5A8, 8))
LEDGER = dict(owner=0, actor=8, body=0x10, swap_count=0x18, once=0x1C,
    lock=0x20, queues=0x24, generations=0x28, lookups=0x2C)
FRAME_SIZE, SAVE_SIZE = 0x270, 0x2F0
# Exact immutable source contract, from the verified Hino TMG_PACK capture.
# No gameplay pointer or gameplay descriptor is copied into the candidate.
BANK_SIZE, DESCRIPTOR_OFFSET, DESCRIPTOR_SIZE = 0x14490, 0x14160, 0x140
HEADER_WORDS = (0, 2, 0x24, 0x3C, 0x134, 0x134, 0x134, 0x134, 0)
EVENT_WORDS = (0, 0, 0, 0, 0, 1)
RECORD0 = (0x1F68, 0, 0, 0, 0, 0, 0, 0x3F800000,
    0x3F19999A, 0x3F19999A, 0x3F19999A, 0x10, 0,
    *([0xFFFFFFFF]*10), 0, 0, 0, 0, 0x400, 0xFFFFFFFF, 0, 0xFFFFFFFF)
RECORD1 = (0x1F68, 0x40434008, 0x36000000, 0x4113C4FA, 0, 0, 0,
    0x3F800000, 0x3F19999A, 0x3F19999A, 0x3F19999A, 9, 0,
    *([0xFFFFFFFF]*10), 0, 0, 0, 0, 0x400, 0xFFFFFFFF, 1, 0xFFFFFFFF)
CONTRACT_WORDS = HEADER_WORDS + EVENT_WORDS + RECORD0 + RECORD1
CONTRACT_BYTES = struct.pack('<' + 'I'*len(CONTRACT_WORDS), *CONTRACT_WORDS)
CONTRACT_SHA256 = '6f3d39061f1407d9167058a94c438a81b5eec7451d4f656711785af25b0e134b'


def _pointer(register, rejected):
    return f'''cmp {register}, 0x10000
jb {rejected}
mov r10, 0x800000000000
cmp {register}, r10
jae {rejected}
'''


def _scope(rejected, *, capture=False):
    # Reload entry RSI from the complete machine save even after a stub or
    # helper has clobbered nonvolatile registers. Shadow space is +00..+1F.
    source = 'mov rsi, qword ptr [rsp+0x2B8]\n' + _pointer('rsi', rejected)
    source += f'''mov rax, {{base_mode_vtable}}
cmp qword ptr [rsi], rax
jne {rejected}
cmp dword ptr [rsi+0x1C], 1
jne {rejected}
mov rax, {{production_data}}
cmp dword ptr [rax], 0x58E5E
jne {rejected}
mov r11, {{visual_data}}
cmp qword ptr [r11], rsi
jne {rejected}
cmp dword ptr [r11+8], 0x58E5E
jne {rejected}
cmp dword ptr [r11+0x18], 232
jne {rejected}
cmp dword ptr [r11+0x14], 7
jne {rejected}
cmp dword ptr [r11+0x20], 0
jne {rejected}
cmp dword ptr [r11+0x28], 0
je {rejected}
cmp dword ptr [r11+0x38], 1
jne {rejected}
mov r9d, dword ptr [r11+0x2C]
test r9d, r9d
je {rejected}
cmp dword ptr [r11+0x30], r9d
jne {rejected}
mov rax, {{effect_manager}}
mov rax, qword ptr [rax]
''' + _pointer('rax', rejected) + f'''
cmp qword ptr [rsp+0x2D8], rax
jne {rejected}
mov rax, {{player_slot}}
mov rdx, qword ptr [rax]
''' + _pointer('rdx', rejected)
    source += f'''cmp dword ptr [rdx], 100
jne {rejected}
cmp dword ptr [rdx+4], 0x10000
jne {rejected}
cmp byte ptr [rdx+0x434], 0
jne {rejected}
cmp byte ptr [rdx+0x435], 0
jne {rejected}
cmp byte ptr [rdx+0x430], 1
jne {rejected}
cmp byte ptr [rdx+0x453], 0
jne {rejected}
cmp dword ptr [rdx+0x460], 1
je {rejected}
mov r11, {{appearance_data}}
cmp dword ptr [r11+0x3C], 0
je {rejected}
cmp qword ptr [r11+0x10], rdx
jne {rejected}
mov r8, qword ptr [r11+0x18]
''' + _pointer('r8', rejected)
    source += 'mov rax, qword ptr [rdx+0x18]\n' + _pointer('rax', rejected)
    source += f'''cmp qword ptr [rax], rdx
jne {rejected}
cmp qword ptr [rax+0x188], r8
jne {rejected}
mov rcx, qword ptr [rdx+0x68]
''' + _pointer('rcx', rejected)
    source += f'''mov rax, {{timing_vtable}}
cmp qword ptr [rcx], rax
jne {rejected}
cmp qword ptr [rcx+8], rdx
jne {rejected}
mov r13, qword ptr [rcx+0x40]
''' + _pointer('r13', rejected) + f'''
mov r14, {{playback_vtable}}
cmp qword ptr [r13], r14
jne {rejected}
cmp qword ptr [r13+8], rdx
jne {rejected}
cmp dword ptr [r13+0x14], 0
jne {rejected}
mov r11, qword ptr [rcx+0x10]
''' + _pointer('r11', rejected)
    # Bank0 only: the getter DIV executes before its own capacity-zero test.
    source += 'mov rax, qword ptr [r11]\n' + _pointer('rax', rejected)
    source += f'''mov r10, 0x4B4341505F474D54
cmp qword ptr [rax], r10
jne {rejected}
cmp dword ptr [rax+0x10], 0x14490
jne {rejected}
cmp dword ptr [rax+0x14], 81
jne {rejected}
cmp dword ptr [rax+0x20], 0x30
jne {rejected}
cmp dword ptr [rax+0x28], 0x2D0
jne {rejected}
cmp dword ptr [rax+0x2D0], 163
jne {rejected}
mov r10, qword ptr [r11+8]
cmp r10, 0x10000
jb {rejected}
mov r12, 0x800000000000
cmp r10, r12
jae {rejected}
cmp dword ptr [r10+8], 163
jne {rejected}
lea r12, [rax+0x2D8]
cmp qword ptr [r10+0x10], r12
jne {rejected}
'''
    for off, register, width in ((0x20,'rsi','qword'),(0x28,'rdx','qword'),
            (0x30,'r8','qword'),(0x38,'rcx','qword'),(0x40,'r11','qword'),
            (0x48,'rax','qword'),(0x50,'r9d','dword'),(0x60,'r13','qword')):
        if capture:
            source += f'mov {width} ptr [rsp+{hex(off)}], {register}\n'
        else:
            source += f'cmp {width} ptr [rsp+{hex(off)}], {register}\njne {rejected}\n'
    return source


def _descriptor():
    source = '''mov rax, qword ptr [rsp+0x58]
mov rdx, qword ptr [rsp+0x48]
lea rcx, [rdx+0x14160]
cmp rax, rcx
jne aura_unlock
lea rcx, [rax+0x140]
lea rdx, [rdx+0x14490]
cmp rcx, rdx
ja aura_unlock
'''
    for i, value in enumerate(CONTRACT_WORDS):
        source += f'cmp dword ptr [rax+{hex(4*i)}], {hex(value)}\njne aura_unlock\n'
    return source


def aura_asm():
    gprs = ('rax','rcx','rdx','rbx','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')
    source = 'pushfq\n' + ''.join(f'push {r}\n' for r in gprs)
    source += 'sub rsp, 0x270\nfxsave64 [rsp+0x70]\n'
    source += _scope('aura_restore', capture=True)
    source += '''mov r11, {data}
xor eax, eax
mov r10d, 1
lock cmpxchg dword ptr [r11+0x20], r10d
jne aura_restore
cmp dword ptr [r11+0x1C], 1
jne aura_lookup
mov rax, qword ptr [rsp+0x20]
cmp qword ptr [r11], rax
jne aura_lookup
mov rax, qword ptr [rsp+0x28]
cmp qword ptr [r11+8], rax
jne aura_lookup
mov rax, qword ptr [rsp+0x30]
cmp qword ptr [r11+0x10], rax
jne aura_lookup
mov eax, dword ptr [rsp+0x50]
cmp dword ptr [r11+0x18], eax
je aura_unlock
aura_lookup:
inc dword ptr [r11+0x2C]
mov rcx, qword ptr [rsp+0x40]
mov edx, 99048
call {timing_lookup}
mov qword ptr [rsp+0x58], rax
'''
    source += _scope('aura_unlock') + _descriptor()
    source += _scope('aura_unlock') + _descriptor()
    source += '''mov r11, {data}
mov rax, qword ptr [rsp+0x20]
mov qword ptr [r11], rax
mov rax, qword ptr [rsp+0x28]
mov qword ptr [r11+8], rax
mov rax, qword ptr [rsp+0x30]
mov qword ptr [r11+0x10], rax
mov eax, dword ptr [rsp+0x50]
mov dword ptr [r11+0x18], eax
mov dword ptr [r11+0x1C], 1
inc dword ptr [r11+0x28]
inc dword ptr [r11+0x24]
mov rcx, qword ptr [rsp+0x38]
mov edx, 99048
mov r8d, -1
xor r9d, r9d
call {timing_queue}
aura_unlock:
mov r11, {data}
mov dword ptr [r11+0x20], 0
aura_restore:
fxrstor64 [rsp+0x70]
lea rsp, [rsp+0x270]
'''
    source += ''.join(f'pop {r}\n' for r in reversed(gprs))
    source += 'popfq\ncall {original_update}\njmp {return}\n'
    return source

