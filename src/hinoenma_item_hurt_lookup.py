"""Resolve selected native item-injury leaves in the player's common bank.

No damage, Ki, query, action request or item state is changed. The source must
be an enabled, owned common item cast or common injury record. Only a complete
native selected transition and available clips in both slots 2/6 may return a
common injury leaf instead of an unrelated Boss action with the same number.
Rejections preserve the old lookup entry ABI. No persistent token is needed.
"""
from copy import deepcopy
import hashlib
import json
import struct

from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_special_item_actions import (SCHEDULE_HEX as SPECIAL_SCHEDULES,
                                         ITEM_SPECS as SPECIAL_ITEMS)
from hinoenma_wind_weakness_dragon import (SCHEDULE_HEX as SPELL_SCHEDULES,
    ALL_ITEM_SPECS, RECOVERY_SCHEDULE_HEX)

PARENT_SHA256 = '3154652f7fc272a638a141a2c71552b4e7a18f16e7d3efdf1365f3a8207c2488'
ENTRY = 'HE_LadderCommonLookup'
CODE_CARRIER = 'HE_MapVisualRestorePrivate'
DATA_CARRIER = 'HE_MapVisualResourcePrivate'
CODE_OFFSET = 0x23200
TABLE_OFFSET = 0x22200
FALLBACK_OFFSET = 0x66800
CHANGED = (ENTRY, DATA_CARRIER, CODE_CARRIER)
CALLERS = (0x711A09, 0x711B1B, 0x7216D7)
INJURY_MOTIONS = {85:30002, 87:30004, 88:30005, 89:30006, 91:30008,
    96:30014, 106:30102, 107:30102, 108:30108, 109:30108,
    147:-1, 151:-1, 152:-1, 205:30310, 224:-1}
SCHEDULES = {**SPECIAL_SCHEDULES, **SPELL_SCHEDULES,
    172: ('ffff0000ffff' * 16),
    609: '12000a00ffff1e002b00ffff80002b00ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    1228: RECOVERY_SCHEDULE_HEX}
CAST_MOTIONS = {row[7]:row[8] for row in SPECIAL_ITEMS + ALL_ITEM_SPECS
                if row[7] in SCHEDULES}
CAST_MOTIONS.update({172:-1, 609:123, 1228:60021})


def transition(target, queries, flags):
    raw = bytearray.fromhex('ffffffffffffffffffff00ffffffff000000000000000000ff806464000000000080ff7fffffffffffffffffffffffff')
    struct.pack_into('<5h', raw, 0, *(tuple(queries) + (-1,) * (5-len(queries))))
    struct.pack_into('<H', raw, 0x14, target)
    struct.pack_into('<I', raw, 0x1C, flags)
    return bytes(raw)


# Source, target, selected index, source first/count, exact descriptor.
ROUTES = []
for index, target, query in ((2593,106,59), (2594,107,58), (2595,109,57),
        (2596,109,56), (2597,109,55), (2598,106,-1)):
    ROUTES.append((151,target,index,2587,28,transition(target,(52,53,query),0x2000C0)))
for index, target, query in ((2599,85,63), (2600,85,62), (2601,85,61),
        (2602,87,60), (2603,88,59), (2604,89,58), (2605,91,57),
        (2606,91,56), (2607,91,55), (2608,88,-1)):
    ROUTES.append((151,target,index,2587,28,transition(target,(52,query),0x200040)))
ROUTES += [(152,96,2634,2615,32,transition(96,(52,60),0x200040)),
           (224,88,7936,7870,73,transition(88,(),0))]
ROUTES = tuple(ROUTES)
ROUTE_BYTES = b''.join(struct.pack('<6H2i48s', source,target,index,first,count,0,
    -1,INJURY_MOTIONS[target],raw) for source,target,index,first,count,raw in ROUTES)
CAST_ROWS = tuple((action,motion,bytes.fromhex(SCHEDULES[action])) for action,motion in sorted(CAST_MOTIONS.items()))
if any(len(schedule) != 96 for action,motion,schedule in CAST_ROWS):
    raise ValueError('Native cast schedule must contain sixteen six-byte entries')
CAST_BYTES = b''.join(struct.pack('<2i96s', action,motion,schedule) for action,motion,schedule in CAST_ROWS)
TABLE_BYTES = ROUTE_BYTES + CAST_BYTES


def helper_asm():
    text = '''item_hurt_lookup:
pushfq
push rcx
push rdx
push rbx
push rsi
push rdi
push r8
push r9
push r10
push r11
push r12
push r13
push r14
push r15
sub rsp, 0x108
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0x80]
mov qword ptr [rsp+0x88], rax
mov qword ptr [rsp+0x90], 0
mov ebx, edx
mov rsi, r8
mov rax, qword ptr [rsp+0x178]
mov r10, {salt_hurt_first_return}
cmp rax, r10
je item_hurt_role
mov r10, {salt_hurt_next_return}
cmp rax, r10
je item_hurt_role
mov r10, {salt_hurt_qualification_return}
cmp rax, r10
jne item_hurt_reject
item_hurt_role:
mov r15, {data}
cmp dword ptr [r15+0x1C], 0
je item_hurt_reject
mov r12, qword ptr [r15+0x10]
test r12, r12
je item_hurt_reject
mov rax, {player_slot}
cmp qword ptr [rax], r12
jne item_hurt_reject
cmp dword ptr [r12+4], 0x10000
jne item_hurt_reject
mov eax, dword ptr [r12]
cmp eax, dword ptr [r15+4]
jne item_hurt_reject
cmp eax, 0x58E5E
je item_hurt_actor
cmp eax, 0x51BE1
jne item_hurt_reject
item_hurt_actor:
cmp dword ptr [r12+0xEF0], 0
jne item_hurt_reject
mov rax, qword ptr [r12+0xE90]
test rax, rax
je item_hurt_reject
cmp dword ptr [rax+0xC], 1
jne item_hurt_reject
mov edx, dword ptr [r12]
cmp dword ptr [rax], edx
jne item_hurt_reject
mov rax, qword ptr [r12+0x240]
test rax, rax
je item_hurt_reject
cmp qword ptr [rax], r12
jne item_hurt_reject
cmp qword ptr [rax+0x108], r12
jne item_hurt_reject
cmp qword ptr [rax+0x20], 0
jle item_hurt_reject
mov rax, qword ptr [r12+0x230]
test rax, rax
je item_hurt_reject
cmp qword ptr [rax], r12
jne item_hurt_reject
mov r13, qword ptr [rax+8]
test r13, r13
je item_hurt_reject
cmp qword ptr [r13+0x50], r12
jne item_hurt_reject
lea rax, [r13+0x70]
cmp rax, rcx
jne item_hurt_reject
cmp dword ptr [r13+0x68], 2
jne item_hurt_reject
mov r14, qword ptr [r13+0x80]
test r14, r14
je item_hurt_reject
mov rax, qword ptr [r13+0x58]
test rax, rax
je item_hurt_reject
cmp qword ptr [rax+0x38], r14
jne item_hurt_reject
cmp byte ptr [rax+0x40], 0
je item_hurt_reject
mov qword ptr [rsp+0xA0], rax
mov r10, qword ptr [rax+0x20]
test r10, r10
je item_hurt_reject
mov qword ptr [rsp+0xA8], r10
mov edx, dword ptr [rax]
'''
    # Known native injury states can continue being hit without a stale token.
    for action, motion in sorted(INJURY_MOTIONS.items()):
        text += f'''cmp edx, {action}
jne item_hurt_current_next_{action}
cmp dword ptr [r10+0x20], {motion}
jne item_hurt_reject
jmp item_hurt_find_route
item_hurt_current_next_{action}:
'''
    text += f'''lea rdi, [r15+{TABLE_OFFSET - 0xF000 + len(ROUTE_BYTES)}]
mov ecx, {len(CAST_ROWS)}
item_hurt_cast_scan:
cmp dword ptr [rdi], edx
je item_hurt_cast_found
add rdi, 104
dec ecx
jne item_hurt_cast_scan
jmp item_hurt_reject
item_hurt_cast_found:
mov eax, dword ptr [rdi+4]
cmp dword ptr [r10+0x20], eax
jne item_hurt_reject
xor ecx, ecx
item_hurt_cast_schedule:
mov rax, qword ptr [rdi+rcx+8]
cmp qword ptr [r10+rcx+0x40], rax
jne item_hurt_reject
add ecx, 8
cmp ecx, 96
jb item_hurt_cast_schedule
item_hurt_find_route:
lea rdi, [r15+{TABLE_OFFSET - 0xF000}]
mov dword ptr [rsp+0xD0], {len(ROUTES)}
mov r9, qword ptr [r13+0x90]
test r9, r9
je item_hurt_reject
mov r10, qword ptr [r14+0x50]
test r10, r10
je item_hurt_reject
movzx ecx, word ptr [r14+0x5A]
cmp cx, word ptr [r14+0x58]
ja item_hurt_reject
item_hurt_route_scan:
cmp word ptr [rdi+2], bx
jne item_hurt_route_next
movzx eax, word ptr [rdi+4]
cmp eax, ecx
jae item_hurt_reject
cmp qword ptr [r10+rax*8], r9
jne item_hurt_route_next
mov qword ptr [rsp+0xC0], rdi
jmp item_hurt_unique
item_hurt_route_next:
add rdi, 68
dec dword ptr [rsp+0xD0]
jne item_hurt_route_scan
jmp item_hurt_reject
item_hurt_unique:
mov r10, qword ptr [r14+0x60]
test r10, r10
je item_hurt_reject
movzx ecx, word ptr [r14+0x6A]
test ecx, ecx
je item_hurt_reject
cmp cx, word ptr [r14+0x68]
ja item_hurt_reject
item_hurt_unique_loop:
cmp qword ptr [r10], r9
je item_hurt_signature
add r10, 8
dec ecx
jne item_hurt_unique_loop
jmp item_hurt_reject
item_hurt_signature:
xor ecx, ecx
item_hurt_signature_loop:
mov rax, qword ptr [rdi+rcx+20]
cmp qword ptr [r9+rcx], rax
jne item_hurt_reject
add ecx, 8
cmp ecx, 48
jb item_hurt_signature_loop
mov r10, qword ptr [r14+0x128]
test r10, r10
je item_hurt_reject
mov ecx, dword ptr [r14+0x130]
test ecx, ecx
je item_hurt_reject
cmp ecx, 4096
ja item_hurt_reject
mov qword ptr [rsp+0xB0], 0
mov qword ptr [rsp+0xB8], 0
mov dword ptr [rsp+0xD4], 0
item_hurt_records:
mov rax, qword ptr [r10]
test rax, rax
je item_hurt_records_next
cmp rax, qword ptr [rsp+0xA0]
jne item_hurt_records_source
inc dword ptr [rsp+0xD4]
item_hurt_records_source:
cmp qword ptr [rax+0x38], r14
jne item_hurt_records_next
cmp byte ptr [rax+0x40], 0
je item_hurt_records_next
movzx edx, word ptr [rdi]
cmp dword ptr [rax], edx
jne item_hurt_records_target
cmp qword ptr [rsp+0xB0], 0
jne item_hurt_reject
mov qword ptr [rsp+0xB0], rax
item_hurt_records_target:
cmp dword ptr [rax], ebx
jne item_hurt_records_next
cmp qword ptr [rsp+0xB8], 0
jne item_hurt_reject
mov qword ptr [rsp+0xB8], rax
item_hurt_records_next:
add r10, 8
dec ecx
jne item_hurt_records
cmp dword ptr [rsp+0xD4], 1
jne item_hurt_reject
mov rax, qword ptr [rsp+0xB0]
test rax, rax
je item_hurt_reject
mov ecx, dword ptr [rdi+6]
cmp dword ptr [rax+0x80], ecx
jne item_hurt_reject
mov r10, qword ptr [r14+0x50]
cmp qword ptr [rax+0x78], r10
jne item_hurt_reject
mov r10, qword ptr [rax+0x20]
test r10, r10
je item_hurt_reject
mov ecx, dword ptr [rdi+12]
cmp dword ptr [r10+0x20], ecx
jne item_hurt_reject
mov rax, qword ptr [rsp+0xB8]
test rax, rax
je item_hurt_reject
mov r10, qword ptr [rax+0x20]
test r10, r10
je item_hurt_reject
mov edx, dword ptr [rdi+16]
cmp dword ptr [r10+0x20], edx
jne item_hurt_reject
mov rcx, qword ptr [r12+0x38]
test rcx, rcx
je item_hurt_reject
cmp dword ptr [rcx+0x50], 1
ja item_hurt_reject
mov r8d, edx
call {{data}} - 0xEF00
test eax, eax
je item_hurt_reject
mov rax, qword ptr [rsp+0xB8]
mov qword ptr [rsp+0x90], rax
test rsi, rsi
je item_hurt_restore
mov dword ptr [rsi], 2
jmp item_hurt_restore
item_hurt_reject:
mov rax, qword ptr [rsp+0x88]
item_hurt_restore:
ldmxcsr dword ptr [rsp+0x80]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
cmp qword ptr [rsp+0x90], 0
je item_hurt_fallback
'''
    restore = '''add rsp, 0x108
pop r15
pop r14
pop r13
pop r12
pop r11
pop r10
pop r9
pop r8
pop rdi
pop rsi
pop rbx
pop rdx
pop rcx
popfq
'''
    return text + restore + 'ret\nitem_hurt_fallback:\n' + restore + 'jmp {data} + 0x57800\n'


def apply_item_hurt_lookup(previous):
    actual = hashlib.sha256(json.dumps(previous, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if actual != PARENT_SHA256:
        raise ValueError('Exact tested spell-event candidate required')
    plan = deepcopy(previous)
    hooks = {h['name']:h for h in plan['hooks']}
    entry, code, table = (hooks[n] for n in (ENTRY,CODE_CARRIER,DATA_CARRIER))
    if not entry['asm'].startswith('jmp {data} + 0x57800\n'):
        raise ValueError('Lookup chain changed')
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    for h, offset, addition in ((code,CODE_OFFSET,helper_asm()),
            (table,TABLE_OFFSET,'.byte '+','.join(map(str,TABLE_BYTES))+'\n')):
        values = {k:0x140000000+v for k,v in plan['targets'].items()}
        values.update(data=0x14400F000, **{'return':0x140000000+h['rva']+h['length']})
        prefix = bytes(ks.asm(h['asm'].format(**values), 0x144000000+h['code_offset'])[0])
        if offset != h['code_offset']+0x200 or len(prefix)>0x200:
            raise ValueError('Exact spare carrier prefix required')
        h['asm'] += '\n'+'nop\n'*(0x200-len(prefix))+addition
        complete = bytes(ks.asm(h['asm'].format(**values),0x144000000+h['code_offset'])[0])
        if len(complete)>h['code_capacity']:
            raise ValueError('Spare carrier capacity exceeded')
        if h is table:
            plan['abyss_assembly_code_intervals'][DATA_CARRIER] = [[0,len(prefix)]]
    entry['asm'] = entry['asm'].replace('jmp {data} + 0x57800\n', 'jmp {data} + 0x14200\n', 1)
    plan['item_hurt_lookup_candidate'] = dict(revision=1, native_queries_unchanged=True,
        persistent_state=False, damage_ki_stock_writes=False,
        cast_actions=sorted(CAST_MOTIONS), leaf_actions=sorted(set(r[1] for r in ROUTES)),
        live_confirmation_pending=True)
    return plan
