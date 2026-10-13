"""Offline, exact-definition extension of the published Beta6 native item path.

The game retains common172, event dispatch, stock, effects and save ownership.
Wind's positive alternate field is an auxiliary timing key, not a body motion.
This module is deliberately independent of the release/profile builder.
"""
from copy import deepcopy
import hashlib
import json
import struct

from hinoenma_arrow_sloth import (
    HELPER_ASM as _PREVIOUS_HELPER, ALL_ITEM_SPECS as _PREVIOUS_ITEMS,
    ITEM_SPECS as _PREVIOUS_LOOKUP_ITEMS,
    SCHEDULE_HEX as _PREVIOUS_SCHEDULES, EVENT_GUARDS as _PREVIOUS_GUARDS,
    NATIVE_SPANS as _PREVIOUS_NATIVE_SPANS,
)
from hinoenma_arrow_sloth_lookup import (
    LOOKUP_ASM as _PREVIOUS_LOOKUP, LOOKUP_OFFSET, _post_definition,
)
from hinoenma_special_item_actions import _definition_scope, _schedules, _once
from hinoenma_beta6_release import validate_release as _validate_beta6

BETA6_BASELINE_SHA256 = '7d1536c7848252ab9f807e5d25e50b1cf54e88588092913f7e545a07ead0dda0'
HELPER_OFFSET = 0x65000
EXTRA_GUARD_OFFSET = 0x67C00
CARRIER_NAME = 'HE_LivingWeaponDigitNine'
CHANGED_HOOKS = ('HE_InputA', 'HE_InputB', CARRIER_NAME)
ITEM_SPECS = (
    (26116, 2, 15, 25, 5, (0, 0, 0), 0xD3A86, 1165, 111, 359),
    (44930, 2, 15, 9, 5, (0, 0, 0), 0x7ED63, 42, 111, 194),
    (44607, 2, 14, 30, 5, (0, 0, 0), 0x7BF64, 1227, 60020, 462),
)
ALL_ITEM_SPECS = _PREVIOUS_ITEMS + ITEM_SPECS
LOOKUP_ITEM_SPECS = _PREVIOUS_LOOKUP_ITEMS + (ITEM_SPECS[1],)
SCHEDULE_HEX = {
    **_PREVIOUS_SCHEDULES,
    1165: '11001100ffff1f006800ffff14000000320011273200280014005a000e0011276800ffff9b00320019008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    1227: 'ffff0000ffffaf0012000100b00058000100ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
}
RECOVERY_SCHEDULE_HEX = 'ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff00001e00ffff1f00ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff'
EVENT_GUARDS = {
    **_PREVIOUS_GUARDS,
    1165: ((17, 6, -1, 21, 255, 255, -1),
           (20, -1, -1, -1, 255, 18, -1),
           (31, 5, -1, -1, 255, 255, -1),
           (142, -1, -1, -1, 255, 255, -1),
           (143, -1, -1, -1, 255, 255, -1),
           (155, -1, -1, -1, 255, 255, -1),
           (10001, -1, -1, -1, 255, 0, -1)),
    1227: ((175, 2, 0x7BF64, 1, 255, 255, -1),
           (176, 5, -1, -1, 255, 255, -1)),
}
NATIVE_SPANS = _PREVIOUS_NATIVE_SPANS + (
    (0x738401, 0x2F), (0x7384EC, 0x2F),
    (0x6FF530, 0x2B0), (0x968D60, 0xA8),
    (0x968A10, 0x167), (0x968B7C, 0x1DF), (0x968230, 0xE9),
)


AUX_CONTRACT_HEX = {60020: '000000000b00000024000000a8000000a001000000040000000400000004000000000000000000000000000000000000000000000a00000005000000000000000a00000006000000000000000a000000070000000a0000000a00000001000000170000000000000001000000180000000a00000000000000180000000a00000003000000280000000a000000040000003c0000000a00000002000000580000000b00000006000000',
 60021: '000000000b00000024000000a80000001c02000030040000300400003004000000000000000000000a00000001000000000000000a00000006000000020000000a00000004000000060000000a000000050000000b00000000000000000000000c0000000a00000000000000140000000100000002000000180000000a000000030000002e0000000a000000010000003c0000000a000000020000003e0000000000000001000000',
 90111: '000000001300000024000000080100008401000060050000600500006005000000000000010000000a00000009000000060000000a000000000000000c0000000a00000005000000120000000a00000002000000180000000a00000006000000220000000a00000004000000300000000a000000070000004e0000000a000000020000004f0000002800000000000000560000000a0000000a000000620000000a00000003000000640000000a0000000c0000006500000000000000000000006a0000000a00000008000000880000000a000000010000008e0000000a0000000a000000910000002900000000000000920000000a00000002000000980000000a0000000b000000000000000000000000000000000000000000000000000000000000000000803f0000803f0000803f0000803f0700000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff00000000ffffffff010000000000000000040000ffffffff00000000ffffffff00000000000000000000000000000000000000000100000002000000a8004474000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000617c8684000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000aa69b7bd000000000000000000000000ffffffff64000000ffffffffffffffff00000000010000000000000000000000000000000000000000000000000000000000000001000000020000009d225848000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000b09db2a1000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000a3b4c78e000000000000000000000000ffffffff64000000ffffffffffffffff00000000010000000000000000000000000000000000000000000000000000000000000001000000020000004f82d705000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000cb4a3fed000000000000000000000000ffffffff64000000ffffffffffffffff00000000010000000000000000000000000000000000000000000000000000000000000001000000020000000ef2f784000000000000000000000000ffffffff64000000ffffffffffffffff0000000001000000000000000000000000000000000000000000000000000000000000000100000002000000e7ffc230000000000000000000000000ffffffff28000000ffffffffffffffff000000000c0000000000000000000000000000000000000000000000000000000000000001000000020000004038ae20000000000000000000000000ffffffff64000000ffffffffffffffff000000000100000000000000000000000000000000000000000000000000000000000000010000000200000029ff8d1b000000000000000000000000ffffffff64000000ffffffffffffffff000000000100000000000000000000000000000000000000000000000000000000000000010000000200000063065bcb000000000000000000000000ffffffff64000000ffffffffffffffff000000000100000000000000000000000100000000000000000000000000000000000000000000000000000000000000'}
AUX_ROWS = ({'hash_capacity': 953,
  'header': '544d475f5041434b000001013000000010c40700dc010000dc0100000000000030000000a0070000100f000000000000',
  'records': {60020: {'extent': 1024,
                      'hash_probe_trace': [{'bucket': 333, 'index': 220, 'key': 6030},
                                           {'bucket': 334, 'index': 107, 'key': 257},
                                           {'bucket': 335, 'index': 263, 'key': 21004},
                                           {'bucket': 336, 'index': 215, 'key': 6010},
                                           {'bucket': 337, 'index': 227, 'key': 16011},
                                           {'bucket': 338, 'index': 328, 'key': 30501},
                                           {'bucket': 339, 'index': 418, 'key': 60020}],
                      'index': 418,
                      'offset': 489632},
              60021: {'extent': 1088,
                      'hash_probe_trace': [{'bucket': 43, 'index': 33, 'key': 28},
                                           {'bucket': 44, 'index': 419, 'key': 60021}],
                      'index': 419,
                      'offset': 490656},
              90111: {'extent': 1408,
                      'hash_probe_trace': [{'bucket': 9, 'index': 117, 'key': 267},
                                           {'bucket': 10, 'index': 13, 'key': 99404},
                                           {'bucket': 11, 'index': 333, 'key': 34003},
                                           {'bucket': 12, 'index': 423, 'key': 90111}],
                      'index': 423,
                      'offset': 494208}},
  'row': 0,
  'size': 508944},
 {'hash_capacity': 811,
  'header': '544d475f5041434b000001013000000010ed06009501000095010000000000003000000090060000f00c000000000000',
  'records': {60020: {'extent': 1024,
                      'hash_probe_trace': [{'bucket': 695, 'index': 204, 'key': 16031},
                                           {'bucket': 696, 'index': 271, 'key': 34100},
                                           {'bucket': 697, 'index': 283, 'key': 34420},
                                           {'bucket': 698, 'index': 64, 'key': 201},
                                           {'bucket': 699, 'index': 314, 'key': 35260},
                                           {'bucket': 700, 'index': 347, 'key': 60020}],
                      'index': 347,
                      'offset': 434688},
              60021: {'extent': 1088,
                      'hash_probe_trace': [{'bucket': 565, 'index': 186, 'key': 977},
                                           {'bucket': 566, 'index': 272, 'key': 34101},
                                           {'bucket': 567, 'index': 284, 'key': 34421},
                                           {'bucket': 568, 'index': 325, 'key': 35360},
                                           {'bucket': 569, 'index': 348, 'key': 60021}],
                      'index': 348,
                      'offset': 435712},
              90111: {'extent': 1408,
                      'hash_probe_trace': [{'bucket': 83, 'index': 352, 'key': 90111}],
                      'index': 352,
                      'offset': 439264}},
  'row': 1,
  'size': 453904})


WIND_DESCRIPTOR_HEX = AUX_CONTRACT_HEX[90111]


def _lookup_post_definition(items):
    text = ''
    for ident, *_ in items:
        text += f'cmp dword ptr [rdi+0x548], {ident}\nje arrow_sloth_lookup_post_definition_{ident}\n'
    text += 'jmp arrow_sloth_lookup_restore\n'
    for ident, kind, sub, cat, flags, effects, spawn, *_ in items:
        text += f'arrow_sloth_lookup_post_definition_{ident}:\n'
        for off, value in ((0, ident), (4, kind | sub << 8), (0x104, flags),
                           (0x10C, cat), *((0x110+i*4, v) for i, v in enumerate(effects)),
                           (0x11C, spawn)):
            width = 'word' if off == 4 else 'dword'
            text += f'cmp {width} ptr [rax+{off}], {value}\njne arrow_sloth_lookup_restore\n'
        text += 'jmp arrow_sloth_lookup_success\n'
    return text


LOOKUP_ASM = _once(_PREVIOUS_LOOKUP,
    _definition_scope(_PREVIOUS_LOOKUP_ITEMS).replace('special_item_', 'arrow_sloth_lookup_'),
    _definition_scope(LOOKUP_ITEM_SPECS).replace('special_item_', 'arrow_sloth_lookup_'))
LOOKUP_ASM = _once(LOOKUP_ASM, _post_definition(),
                   _lookup_post_definition(LOOKUP_ITEM_SPECS))

HELPER_ASM = _once(_PREVIOUS_HELPER,
    _definition_scope(_PREVIOUS_ITEMS).replace('special_item_', 'dung_fan_'),
    _definition_scope(ALL_ITEM_SPECS).replace('special_item_', 'dung_fan_'))
HELPER_ASM = _once(HELPER_ASM,
    _schedules(_PREVIOUS_SCHEDULES, _PREVIOUS_GUARDS).replace('special_item_', 'dung_fan_'),
    _schedules(SCHEDULE_HEX, EVENT_GUARDS).replace('special_item_', 'dung_fan_'))
HELPER_ASM = _once(HELPER_ASM,
    'cmp dword ptr [rax+0x34], -1\njne dung_fan_restore\n',
    '''mov ecx, -1
cmp dword ptr [rsp+0x94], 1165
jne wind_weakness_dragon_alternate
mov ecx, 90111
wind_weakness_dragon_alternate:
cmp dword ptr [rax+0x34], ecx
jne dung_fan_restore
''')
HELPER_ASM = _once(HELPER_ASM,
    'mov ecx, dword ptr [rsp+0x94]\ncmp dword ptr [rax], ecx\njne dung_fan_restore\n',
    'mov ecx, dword ptr [rsp+0x94]\ncmp dword ptr [rax], ecx\njne dung_fan_restore\n'
    'mov qword ptr [rsp+0x88], rax\n')
HELPER_ASM = _once(HELPER_ASM,
    'call {data} + 0x3E00\ntest al, al\nje dung_fan_restore\n',
    '''call {data} + 0x3E00
test al, al
je dung_fan_restore
mov edx, dword ptr [rsp+0x94]
cmp edx, 1165
je wind_weakness_dragon_extra_guard
cmp edx, 1227
jne wind_weakness_dragon_extra_done
wind_weakness_dragon_extra_guard:
mov rcx, rdi
mov r8, qword ptr [rsp+0x80]
mov r9, qword ptr [rsp+0xD0]
call {data} + 0x58C00
test al, al
je dung_fan_restore
wind_weakness_dragon_extra_done:
''')


def _new_post_definition():
    text = ''
    for ident, *_ in ITEM_SPECS:
        text += f'cmp dword ptr [rdi+0x548], {ident}\nje wind_weakness_dragon_post_{ident}\n'
    text += 'jmp wind_weakness_dragon_post_done\n'
    for ident, kind, sub, cat, flags, effects, spawn, *_ in ITEM_SPECS:
        text += f'wind_weakness_dragon_post_{ident}:\nmov rax, qword ptr [rsp+0xC8]\n'
        for off, value in ((0, ident), (4, kind | sub << 8), (0x104, flags),
                           (0x10C, cat), *((0x110+i*4, v) for i, v in enumerate(effects)),
                           (0x11C, spawn)):
            width = 'word' if off == 4 else 'dword'
            text += f'cmp {width} ptr [rax+{off}], {value}\njne dung_fan_restore\n'
        text += 'jmp wind_weakness_dragon_post_resources\n'
    return text + '''wind_weakness_dragon_post_resources:
mov rdx, qword ptr [rsp+0x88]
mov ecx, dword ptr [rsp+0x94]
cmp dword ptr [rdx], ecx
jne dung_fan_restore
cmp byte ptr [rdx+0x40], 0
je dung_fan_restore
mov r8, qword ptr [rsp+0x80]
cmp qword ptr [rdx+0x38], r8
jne dung_fan_restore
mov rax, qword ptr [rsp+0xD0]
cmp qword ptr [rdx+0x20], rax
jne dung_fan_restore
mov ecx, dword ptr [rsp+0x98]
cmp dword ptr [rax+0x20], ecx
jne dung_fan_restore
mov ecx, -1
cmp dword ptr [rsp+0x94], 1165
jne wind_weakness_dragon_post_alternate
mov ecx, 90111
wind_weakness_dragon_post_alternate:
cmp dword ptr [rax+0x34], ecx
jne dung_fan_restore
mov edx, dword ptr [rsp+0x94]
mov r8, qword ptr [rsp+0x80]
call dung_fan_schedule
test al, al
je dung_fan_restore
wind_weakness_dragon_post_done:
'''


HELPER_ASM = _once(HELPER_ASM, 'mov rcx, rdi\nmov edx, 172\n',
                   _new_post_definition() + 'mov rcx, rdi\nmov edx, 172\n')


def _exact_schedule(raw, pointer='rax', failure='wind_weakness_dragon_guard_false'):
    """Compare all event references, including an event-free recovery action."""
    data = bytes.fromhex(raw)
    if len(data) != 0x60:
        raise ValueError('Expected sixteen complete event references')
    text = ''
    for offset in range(0, len(data), 8):
        text += (f'movabs r10, {struct.unpack_from("<Q", data, offset)[0]}\n'
                 f'cmp qword ptr [{pointer}+{0x40+offset}], r10\njne {failure}\n')
    return text


# RCX=accepted controller, EDX=action, R8=common bank, R9=main params.
# The enclosing helper saves all volatile state; this callback follows Win64
# and touches only its stack. Main owner/epoch/request are rechecked afterward.
EXTRA_GUARD_ASM = '''wind_weakness_dragon_guard:
sub rsp, 0x98
mov qword ptr [rsp+0x20], rcx
mov qword ptr [rsp+0x28], r8
mov qword ptr [rsp+0x30], r9
mov dword ptr [rsp+0x60], edx
cmp edx, 1165
je wind_weakness_dragon_wind_guard
cmp edx, 1227
jne wind_weakness_dragon_guard_false
mov rax, qword ptr [rcx+0x50]
mov qword ptr [rsp+0x38], rax
test rax, rax
je wind_weakness_dragon_guard_false
mov rax, qword ptr [rax+0x38]
mov qword ptr [rsp+0x40], rax
test rax, rax
je wind_weakness_dragon_guard_false
cmp dword ptr [rax+0x50], 1
ja wind_weakness_dragon_guard_false
add rcx, 0x70
mov edx, 1228
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je wind_weakness_dragon_guard_false
mov qword ptr [rsp+0x48], rax
cmp dword ptr [rax], 1228
jne wind_weakness_dragon_guard_false
cmp byte ptr [rax+0x40], 0
je wind_weakness_dragon_guard_false
mov r8, qword ptr [rsp+0x28]
cmp qword ptr [rax+0x38], r8
jne wind_weakness_dragon_guard_false
mov rax, qword ptr [rax+0x20]
test rax, rax
je wind_weakness_dragon_guard_false
mov qword ptr [rsp+0x50], rax
cmp dword ptr [rax+0x20], 60021
jne wind_weakness_dragon_guard_false
cmp dword ptr [rax+0x34], -1
jne wind_weakness_dragon_guard_false
''' + _exact_schedule(RECOVERY_SCHEDULE_HEX) + '''mov rcx, qword ptr [rsp+0x40]
mov edx, 60021
call {data} + 0x3E00
test al, al
je wind_weakness_dragon_guard_false
mov rcx, qword ptr [rsp+0x20]
mov rax, qword ptr [rsp+0x38]
cmp qword ptr [rcx+0x50], rax
jne wind_weakness_dragon_guard_false
mov r8, qword ptr [rsp+0x40]
cmp qword ptr [rax+0x38], r8
jne wind_weakness_dragon_guard_false
cmp dword ptr [r8+0x50], 1
ja wind_weakness_dragon_guard_false
mov r8, qword ptr [rsp+0x28]
cmp qword ptr [rcx+0x80], r8
jne wind_weakness_dragon_guard_false
mov rdx, qword ptr [rsp+0x48]
cmp dword ptr [rdx], 1228
jne wind_weakness_dragon_guard_false
cmp byte ptr [rdx+0x40], 0
je wind_weakness_dragon_guard_false
cmp qword ptr [rdx+0x38], r8
jne wind_weakness_dragon_guard_false
mov rax, qword ptr [rsp+0x50]
cmp qword ptr [rdx+0x20], rax
jne wind_weakness_dragon_guard_false
cmp dword ptr [rax+0x20], 60021
jne wind_weakness_dragon_guard_false
cmp dword ptr [rax+0x34], -1
jne wind_weakness_dragon_guard_false
''' + _exact_schedule(RECOVERY_SCHEDULE_HEX) + '''jmp wind_weakness_dragon_aux_guard
wind_weakness_dragon_wind_guard:
jmp wind_weakness_dragon_aux_guard
wind_weakness_dragon_guard_true:
mov eax, 1
add rsp, 0x98
ret
wind_weakness_dragon_guard_false:
xor eax, eax
add rsp, 0x98
ret
'''


def _aux_guard():
    """Read the native TMG path without invoking its unbounded hash callback.

    Both common rows are required. The probe chains are checked exactly before
    the corresponding index and offset, so native968230 resolves the verified
    descriptor. Positive90111 uses its complete descriptor; the two Dragon
    descriptors use exact header/event references and bounded remaining tables.
    Existing Orochi1200 handling is left entirely in the native dispatch path.
    """
    fail = 'wind_weakness_dragon_guard_false'
    text = '''wind_weakness_dragon_aux_guard:
mov rcx, qword ptr [rsp+0x20]
mov r10, qword ptr [rcx+0x50]
test r10, r10
je wind_weakness_dragon_guard_false
mov r11, qword ptr [r10+0x68]
test r11, r11
je wind_weakness_dragon_guard_false
mov rax, {timing_vtable}
cmp qword ptr [r11], rax
jne wind_weakness_dragon_guard_false
cmp qword ptr [r11+8], r10
jne wind_weakness_dragon_guard_false
mov rdx, qword ptr [r11+0x40]
test rdx, rdx
je wind_weakness_dragon_guard_false
add rax, 0x10
cmp qword ptr [rdx], rax
jne wind_weakness_dragon_guard_false
cmp qword ptr [rdx+8], r10
jne wind_weakness_dragon_guard_false
cmp dword ptr [rdx+0x14], 1
ja wind_weakness_dragon_guard_false
cmp dword ptr [rdx+0x10], 2
ja wind_weakness_dragon_guard_false
mov qword ptr [rsp+0x58], r11
'''
    for row in AUX_ROWS:
        number = row['row']
        text += f'''mov r10, qword ptr [rsp+0x58]
mov r10, qword ptr [r10+{0x20+number*0x18}]
test r10, r10
je {fail}
mov rax, qword ptr [r10]
test rax, rax
je {fail}
mov qword ptr [rsp+0x68], rax
mov r11, qword ptr [r10+8]
test r11, r11
je {fail}
cmp dword ptr [r11+8], {row['hash_capacity']}
jne {fail}
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je {fail}
mov qword ptr [rsp+0x70], rdx
'''
        header = bytes.fromhex(row['header'])
        for offset in range(0, len(header), 8):
            text += (f'movabs r10, {struct.unpack_from("<Q", header, offset)[0]}\n'
                     f'cmp qword ptr [rax+{offset}], r10\njne {fail}\n')
        text += (f'cmp dword ptr [rsp+0x60], 1165\nje wind_weakness_dragon_aux_{number}_90111\n'
                 f'jmp wind_weakness_dragon_aux_{number}_60020\n')
        for key in (90111, 60020, 60021):
            record = row['records'][key]
            if record['offset'] + record['extent'] > row['size']:
                raise ValueError('Auxiliary descriptor extends beyond its exact pack')
            if record['index'] >= struct.unpack_from('<I', header, 0x14)[0]:
                raise ValueError('Auxiliary index extends beyond its exact pack table')
            text += f'wind_weakness_dragon_aux_{number}_{key}:\n'
            text += 'mov rdx, qword ptr [rsp+0x70]\n'
            for probe in record['hash_probe_trace']:
                if not 0 <= probe['bucket'] < row['hash_capacity']:
                    raise ValueError('Auxiliary probe lies outside its hash table')
                pair = probe['key'] | (probe['index'] << 32)
                text += (f'movabs r10, {pair}\n'
                         f'cmp qword ptr [rdx+{probe["bucket"]*8}], r10\njne {fail}\n')
            text += 'mov rax, qword ptr [rsp+0x68]\n'
            text += (f'cmp dword ptr [rax+{0x30+record["index"]*4}], {record["offset"]}\n'
                     f'jne {fail}\nlea rcx, [rax+{record["offset"]}]\n'
                     f'lea r8, [rip+wind_weakness_dragon_aux_bytes_{key}]\n'
                     f'mov edx, {len(bytes.fromhex(AUX_CONTRACT_HEX[key]))//8}\n'
                     'call wind_weakness_dragon_aux_compare\ntest al, al\n'
                     f'je {fail}\n')
            next_label = (f'wind_weakness_dragon_aux_{number}_60021' if key == 60020
                          else f'wind_weakness_dragon_aux_{number}_done')
            text += f'jmp {next_label}\n'
        text += f'wind_weakness_dragon_aux_{number}_done:\n'
    text += '''jmp wind_weakness_dragon_guard_true
wind_weakness_dragon_aux_compare:
mov rax, qword ptr [r8+2]
cmp qword ptr [rcx], rax
jne wind_weakness_dragon_aux_compare_false
add r8, 10
add rcx, 8
dec edx
jne wind_weakness_dragon_aux_compare
mov eax, 1
ret
wind_weakness_dragon_aux_compare_false:
xor eax, eax
ret
'''
    for key, raw in AUX_CONTRACT_HEX.items():
        data = bytes.fromhex(raw)
        if len(data) % 8:
            raise ValueError('Auxiliary comparison must include complete qwords')
        text += f'wind_weakness_dragon_aux_bytes_{key}:\n'
        for offset in range(0, len(data), 8):
            text += f'movabs rax, {struct.unpack_from("<Q", data, offset)[0]}\n'
    return text


EXTRA_GUARD_ASM += _aux_guard()


def _fingerprint(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def apply_wind_weakness_dragon(previous):
    """Pure candidate transform; does not read a process or write a profile."""
    _validate_beta6(previous)
    if (_fingerprint(previous) != BETA6_BASELINE_SHA256
            or len(previous['hooks']) != 82
            or previous.get('allocation_size') != 0x69000
            or previous.get('data_offset') != 0xF000):
        raise ValueError('Exact published 82-hook Beta6 baseline required')
    plan = deepcopy(previous)
    carrier = next(h for h in plan['hooks'] if h['name'] == CARRIER_NAME)
    if ((carrier['code_offset'], carrier['code_capacity']) != (0x61000, 0x8000)
            or not carrier['asm'].endswith(_PREVIOUS_LOOKUP)
            or carrier['asm'].count(_PREVIOUS_HELPER) != 1):
        raise ValueError('Exact Beta6 helper and common lookup layout required')
    prefix, old_tail = carrier['asm'].split(_PREVIOUS_HELPER)
    old_padding = old_tail[:-len(_PREVIOUS_LOOKUP)]
    if old_padding.replace('nop\n', '').strip():
        raise ValueError('Unexpected instructions between item helper and lookup')
    from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    values = {key: 0x140000000 + rva for key, rva in plan['targets'].items()}
    values.update(data=0x144000000 + plan['data_offset'],
                  **{'return': 0x140000000 + carrier['rva'] + carrier['length']})

    def encoded(asm, offset):
        return bytes(ks.asm(asm.format(**values), addr=0x144000000 + offset)[0])

    original_prefix = encoded(prefix, carrier['code_offset'])
    if len(original_prefix) != HELPER_OFFSET - carrier['code_offset']:
        raise ValueError('Previous carrier prefix no longer ends at the fixed helper')
    helper = encoded(HELPER_ASM, HELPER_OFFSET)
    lookup = encoded(LOOKUP_ASM, LOOKUP_OFFSET)
    guard = encoded(EXTRA_GUARD_ASM, EXTRA_GUARD_OFFSET)
    if (HELPER_OFFSET + len(helper) > LOOKUP_OFFSET
            or LOOKUP_OFFSET + len(lookup) > EXTRA_GUARD_OFFSET
            or EXTRA_GUARD_OFFSET + len(guard) > 0x69000):
        raise ValueError('Expanded native item path exceeds a fixed private region')
    carrier['asm'] = (prefix + HELPER_ASM + '\n'
        + 'nop\n' * (LOOKUP_OFFSET - HELPER_OFFSET - len(helper)) + LOOKUP_ASM + '\n'
        + 'nop\n' * (EXTRA_GUARD_OFFSET - LOOKUP_OFFSET - len(lookup)) + EXTRA_GUARD_ASM)
    for name, suffix in (('HE_InputA', 'a'), ('HE_InputB', 'b')):
        hook = next(h for h in plan['hooks'] if h['name'] == name)
        anchor = f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        extra = ''.join(f'mov ecx, {motion}\ncmp dword ptr [rdx], {action}\n'
                        f'je special_item_input_found_{suffix}\n'
                        for action, motion in ((1165, 111), (1227, 60020), (1228, 60021)))
        hook['asm'] = _once(hook['asm'], anchor, extra + anchor)
    for hook in plan['hooks']:
        if hook['name'] in CHANGED_HOOKS:
            values['return'] = 0x140000000 + hook['rva'] + hook['length']
            code = encoded(hook['asm'], hook['code_offset'])
            if len(code) > hook['code_capacity']:
                raise ValueError('Expanded native item path exceeds carrier: ' + hook['name'])
            if hook is carrier:
                if code[:len(original_prefix)] != original_prefix:
                    raise ValueError('Carrier instructions before 65000 were changed')
                final_length = len(code)
    carrier['purpose'] += '; exact Wind26116, Weakness44930 and Dragon44607 native item candidate'
    intervals = plan['abyss_assembly_code_intervals'][CARRIER_NAME]
    if intervals[-1] != [0x4000, 26103]:
        raise ValueError('Exact Beta6 relocation interval required')
    intervals[-1] = [0x4000, final_length]
    plan.update(wind_weakness_dragon_revision=1,
        wind_weakness_dragon_item_ids=[row[0] for row in ITEM_SPECS],
        wind_weakness_dragon_common_actions=[42, 1165, 1227, 1228],
        wind_weakness_dragon_gameplay_confirmation_pending=True,
        wind_weakness_dragon_direct_inventory_effect_hp_save_writes=False,
        wind_weakness_dragon_helper_offsets=dict(entry=HELPER_OFFSET, lookup=LOOKUP_OFFSET,
                                               extra_guard=EXTRA_GUARD_OFFSET),
        wind_weakness_dragon_source_baseline_sha256=BETA6_BASELINE_SHA256,
        wind_weakness_dragon_auxiliary_timing_guard_pending=False,
        wind_weakness_dragon_auxiliary_timing_keys=[90111, 60020, 60021],
        wind_weakness_dragon_auxiliary_descriptor_checks={
            90111: 'complete_descriptor', 60020: 'header_and_events_with_pack_bounds',
            60021: 'header_and_events_with_pack_bounds'})
    if _fingerprint(previous) != BETA6_BASELINE_SHA256:
        raise ValueError('The input Beta6 plan was mutated')
    return plan
