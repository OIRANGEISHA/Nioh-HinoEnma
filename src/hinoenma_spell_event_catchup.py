"""Candidate: one native catch-up after an observed spell startup frame gap.

No spell, stock, damage, or inventory emulation. The existing Salt marker's
reserved value 2 tracks these two mutually exclusive player actions. Native
704E50 remains responsible for event selection, dispatch and lifecycle.
"""
from copy import deepcopy
import hashlib
import json
import struct

from hinoenma_wind_weakness_dragon import SCHEDULE_HEX
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64

BASELINE_SHA256 = '9bead9b91721dc925f79f6bd3ba85eb192e4981c6591b1310e37b8155668fdd5'
DESCRIPTORS = {17: '0000ffff000000000000ffffffffffff00000000ffffff06ffffffff1500000000000000000000000000ffffff00ffffffffffff00000000000000000000ffffffff6464646464646464ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff', 31: '0000ffff000000000000ffffffffffff00000000ffffff05ffffffffffff000000000000000000000000ffffff00ffffffffffff00000000000000000000ffffffff6464646464646464ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff'}

ENTRY = 'HE_SaltEventCatchup'
CARRIER = 'HE_ProjectileElementInheritance'
OFFSET = 0x1C300
CHANGED = (CARRIER, ENTRY)

def checks(raw, pointer, offset=0):
    data = bytes.fromhex(raw)
    assert len(data) % 8 == 0
    return ''.join(f'movabs rax, {struct.unpack_from("<Q", data, n)[0]}\n'
                   f'cmp qword ptr [{pointer}+{offset+n}], rax\njne spell_gap_reject\n'
                   for n in range(0, len(data), 8))

def prefix():
    s = '''pushfq
push rax
push r10
push r11
push r9
test rcx, rcx
je spell_gap_reject
test rdx, rdx
je spell_gap_reject
cmp qword ptr [rcx+0x58], rdx
jne spell_gap_reject
cmp byte ptr [rdx+0x40], 0
je spell_gap_reject
cmp dword ptr [rcx+0x68], 2
jne spell_gap_reject
mov r10, qword ptr [rcx+0x80]
test r10, r10
je spell_gap_reject
cmp qword ptr [rdx+0x38], r10
jne spell_gap_reject
cmp dword ptr [rcx+0x24], 0x3F800000
jne spell_gap_reject
cmp dword ptr [rcx+0x550], 1
jne spell_gap_reject
cmp dword ptr [rcx+0x554], 0
jne spell_gap_reject
cmp qword ptr [rcx+0x558], 0
jne spell_gap_reject
cmp byte ptr [rcx+0x570], 0
jne spell_gap_reject
cmp qword ptr [rcx+0x728], 0
jne spell_gap_reject
mov rax, qword ptr [rcx+0x720]
test rax, rax
je spell_gap_reject
cmp qword ptr [rax], rax
jne spell_gap_reject
cmp qword ptr [rax+8], rax
jne spell_gap_reject
cmp dword ptr [rdx], 1165
je spell_gap_wind
cmp dword ptr [rdx], 42
jne spell_gap_reject
cmp dword ptr [rcx+0x548], 44930
jne spell_gap_reject
cmp dword ptr [rcx+0x54C], 9
jne spell_gap_reject
mov r10, qword ptr [rdx+0x20]
test r10, r10
je spell_gap_reject
cmp dword ptr [r10+0x34], -1
jne spell_gap_reject
'''
    s += checks(SCHEDULE_HEX[42], 'r10', 0x40)
    s += '''jmp spell_gap_resources
spell_gap_wind:
cmp dword ptr [rcx+0x548], 26116
jne spell_gap_reject
cmp dword ptr [rcx+0x54C], 25
jne spell_gap_reject
mov r10, qword ptr [rdx+0x20]
test r10, r10
je spell_gap_reject
cmp dword ptr [r10+0x34], 90111
jne spell_gap_reject
'''
    s += checks(SCHEDULE_HEX[1165], 'r10', 0x40)
    s += '''spell_gap_resources:
cmp dword ptr [r10+0x20], 111
jne spell_gap_reject
mov r10, qword ptr [rcx+0x80]
cmp word ptr [r10+0x88], 32
jb spell_gap_reject
cmp word ptr [r10+0x88], 4096
ja spell_gap_reject
mov r10, qword ptr [r10+0x80]
test r10, r10
je spell_gap_reject
mov r11, qword ptr [r10+17*8]
test r11, r11
je spell_gap_reject
'''
    # Both actions use the same native create and release descriptors.
    descriptors = DESCRIPTORS
    s += checks(descriptors[17], 'r11')
    s += 'mov r11, qword ptr [r10+31*8]\ntest r11, r11\nje spell_gap_reject\n'
    s += checks(descriptors[31], 'r11')
    s += '''mov r10, qword ptr [rcx+0x50]
test r10, r10
je spell_gap_reject
mov r11, {player_slot}
cmp qword ptr [r11], r10
jne spell_gap_reject
mov r11, {data}
cmp qword ptr [r11+0x10], r10
jne spell_gap_reject
cmp dword ptr [r10+4], 0x10000
jne spell_gap_reject
mov eax, dword ptr [r10]
cmp eax, dword ptr [r11+4]
jne spell_gap_reject
cmp eax, 0x58E5E
je spell_gap_role
cmp eax, 0x51BE1
jne spell_gap_reject
spell_gap_role:
cmp dword ptr [r10+0xEF0], 0
jne spell_gap_reject
cmp dword ptr [r11+0x1C], 0
je spell_gap_reject
mov rax, qword ptr [r10+0xE90]
test rax, rax
je spell_gap_reject
cmp dword ptr [rax+0xC], 1
jne spell_gap_reject
mov eax, dword ptr [rax]
cmp eax, dword ptr [r10]
jne spell_gap_reject
mov rax, qword ptr [r10+0x230]
test rax, rax
je spell_gap_reject
cmp qword ptr [rax], r10
jne spell_gap_reject
cmp qword ptr [rax+8], rcx
jne spell_gap_reject
mov rax, qword ptr [r10+0x240]
test rax, rax
je spell_gap_reject
cmp qword ptr [rax], r10
jne spell_gap_reject
cmp qword ptr [rax+0x108], r10
jne spell_gap_reject
cmp qword ptr [rax+0x20], 0
jle spell_gap_reject
mov rax, qword ptr [r10+0x38]
test rax, rax
je spell_gap_reject
cmp dword ptr [rax+0x48], 2
jne spell_gap_reject
cmp dword ptr [rax+0x50], 0
jne spell_gap_reject
cmp r9b, 1
je spell_gap_arm
cmp r9b, 0
jne spell_gap_reject
cmp dword ptr [r11+0x4E80], 2
jne spell_gap_restore
mov eax, dword ptr [r11+0x1C]
cmp dword ptr [r11+0x4E84], eax
jne spell_gap_reject
cmp qword ptr [r11+0x4E88], r10
jne spell_gap_reject
cmp qword ptr [r11+0x4E90], rcx
jne spell_gap_reject
cmp qword ptr [r11+0x4E98], rdx
jne spell_gap_reject
mov eax, dword ptr [rcx+0x548]
cmp dword ptr [r11+0x4EA0], eax
jne spell_gap_reject
mov eax, 2
xor r10d, r10d
lock cmpxchg dword ptr [r11+0x4E80], r10d
jne spell_gap_restore
movd eax, xmm2
cmp eax, 0x41880000
jbe spell_gap_restore
cmp eax, 0x42D00000
jae spell_gap_restore
mov byte ptr [rsp], 1
jmp spell_gap_restore
spell_gap_arm:
movd eax, xmm2
test eax, eax
jne spell_gap_reject
mov dword ptr [r11+0x4E80], 0
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0x4E84], eax
mov qword ptr [r11+0x4E88], r10
mov qword ptr [r11+0x4E90], rcx
mov qword ptr [r11+0x4E98], rdx
mov eax, dword ptr [rcx+0x548]
mov dword ptr [r11+0x4EA0], eax
mov dword ptr [r11+0x4E80], 2
jmp spell_gap_restore
spell_gap_reject:
mov r11, {data}
cmp dword ptr [r11+0x4E80], 2
jne spell_gap_restore
cmp qword ptr [r11+0x4E90], rcx
jne spell_gap_restore
mov dword ptr [r11+0x4E80], 0
spell_gap_restore:
pop r9
pop r11
pop r10
pop rax
popfq
'''
    return s

def apply_spell_event_catchup(previous):
    fingerprint = hashlib.sha256(json.dumps(previous, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if fingerprint != BASELINE_SHA256:
        raise ValueError("Exact published Beta6.1 baseline required")
    if previous['tool_version'] != '1.0.0-beta.6.1' or len(previous['hooks']) != 82:
        raise ValueError('Exact Beta6.1 required')
    plan = deepcopy(previous)
    entry = next(h for h in plan['hooks'] if h['name'] == ENTRY)
    carrier = next(h for h in plan['hooks'] if h['name'] == CARRIER)
    if (entry['code_offset'],entry['code_capacity'],carrier['code_offset'],carrier['code_capacity']) != (0x1040,0x3C0,0x1C000,0x1000):
        raise ValueError('Exact owned slots required')
    plan['targets']['spell_schedule_return'] = entry['rva'] + entry['length']
    values = {k:0x140000000+v for k,v in plan['targets'].items()}
    values.update(data=0x14400F000, **{'return':0x140000000+carrier['rva']+carrier['length']})
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    old_bytes=bytes(ks.asm(carrier['asm'].format(**values),addr=0x14401C000)[0])
    if len(old_bytes) > 0x300:
        raise ValueError('Carrier prefix grew')
    gap=prefix()
    old_entry=entry['asm'].replace('{return}','{spell_schedule_return}')
    carrier['asm'] += '\n'+'nop\n'*(0x300-len(old_bytes))+gap+old_entry
    entry['asm']='jmp {data} + 0xD300\n'
    plan['spell_event_catchup_candidate']=dict(items=[26116,44930], one_native_catchup=True,
        marker_value=2, private_state_offset=0x13E80, helper_offset=OFFSET,
        effects_and_stock_native=True, live_confirmation_pending=True)
    return plan
