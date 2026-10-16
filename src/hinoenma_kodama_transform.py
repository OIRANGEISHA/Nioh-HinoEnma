"""Use the native Kodama enter/loop/cleanup actions for the local Hino player.

The game's events own the visual replacement, item cost and cancellation. This
module only admits the verified request and protects common action routing.
"""
from copy import deepcopy
import struct

from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_general_jutsu import digest
from hinoenma_special_item_actions import _once
from hinoenma_kodama_transform_data import PARAMS, EVENTS, AUX_ROWS, AUX_HEX
import hinoenma_wind_weakness_dragon as spells

PARENT_SHA256 = 'd93f6b10b9d2053bbfe505c5d765b68c08c49e7a30af6f6c2897604fbd53cf69'
DEFINITION_OFFSET = 0x2BB00
SCHEDULE_OFFSET = 0x20600
AUX_OFFSET = 0x40400
RESOURCE_OFFSET = 0x41400
HURT_ROWS_OFFSET = 0x23C00
ITEM = 19707
DEFINITION = ((0, ITEM), (4, 0xE02), (0x104, 5), (0x10C, 28),
              (0x110, 0), (0x114, 0), (0x118, 0), (0x11C, 161855))


def call_at(offset):
    return f'{{data}} + {offset-0xF000}'


def immediates(raw):
    b = bytes.fromhex(raw)
    if len(b) % 8:
        raise ValueError('Complete native qwords required')
    return ''.join(f'movabs rax, {q}\n' for q, in struct.iter_unpack('<Q', b))


def definition_source():
    s = '''kodama_definition:
cmp dword ptr [rdi+0x548], 19707
jne kodama_definition_existing
xor r10d, r10d
xor r11d, r11d
cmp dword ptr [rdi+0x54C], 28
jne kodama_definition_no
cmp byte ptr [rdi+0x570], 0
jne kodama_definition_no
'''
    for off, value in DEFINITION:
        s += f'cmp {"word" if off==4 else "dword"} ptr [rax+{off}], {value}\njne kodama_definition_no\n'
    return s + '''mov r10d, 1205
mov r11d, 122
kodama_definition_no:
ret
kodama_definition_existing:
jmp {data} + 116224
'''


def schedule_source():
    # Exact parameters and event descriptors, including hide/cleanup flags.
    # RAX=params, EDX=action, R8=common bank. Only volatile state is scratch.
    s = '''kodama_schedule:
cmp edx, 1205
je kodama_schedule_start
cmp edx, 1206
je kodama_schedule_start
jmp {data} + 112128
kodama_schedule_start:
sub rsp, 0x38
mov qword ptr [rsp+0x20], r8
mov rcx, rax
lea r8, [rip+kodama_params_1205]
cmp edx, 1205
je kodama_schedule_compare
lea r8, [rip+kodama_params_1206]
kodama_schedule_compare:
mov edx, 20
call kodama_compare
test al, al
je kodama_schedule_no
mov r8, qword ptr [rsp+0x20]
movzx eax, word ptr [r8+0x88]
cmp eax, 159
jbe kodama_schedule_no
cmp eax, 4096
ja kodama_schedule_no
mov rax, qword ptr [r8+0x80]
test rax, rax
je kodama_schedule_no
mov qword ptr [rsp+0x28], rax
'''
    for index in sorted(EVENTS):
        s += f'''mov rax, qword ptr [rsp+0x28]
mov rcx, qword ptr [rax+{index*8}]
test rcx, rcx
je kodama_schedule_no
lea r8, [rip+kodama_event_{index}]
mov edx, 16
call kodama_compare
test al, al
je kodama_schedule_no
'''
    s += '''mov r8, qword ptr [rsp+0x20]
mov rax, qword ptr [rsp+0x28]
cmp qword ptr [r8+0x80], rax
jne kodama_schedule_no
mov eax, 1
add rsp, 0x38
ret
kodama_schedule_no:
xor eax, eax
add rsp, 0x38
ret
kodama_compare:
mov rax, qword ptr [r8+2]
cmp qword ptr [rcx], rax
jne kodama_compare_no
add r8, 10
add rcx, 8
dec edx
jne kodama_compare
mov eax, 1
ret
kodama_compare_no:
xor eax, eax
ret
'''
    for action, raw in PARAMS.items():
        s += f'kodama_params_{action}:\n' + immediates(raw)
    for index, raw in sorted(EVENTS.items()):
        s += f'kodama_event_{index}:\n' + immediates(raw)
    return s


def auxiliary_source():
    # 60012 is a timing descriptor, not a body-animation ID. Verify both native
    # common packs and the exact bounded probe chain used by native968230.
    fail = 'kodama_aux_no'
    s = '''kodama_aux:
sub rsp, 0x48
mov r10, qword ptr [rcx+0x50]
test r10, r10
je kodama_aux_no
mov r11, qword ptr [r10+0x68]
test r11, r11
je kodama_aux_no
mov rax, {timing_vtable}
cmp qword ptr [r11], rax
jne kodama_aux_no
cmp qword ptr [r11+8], r10
jne kodama_aux_no
mov rdx, qword ptr [r11+0x40]
test rdx, rdx
je kodama_aux_no
add rax, 0x10
cmp qword ptr [rdx], rax
jne kodama_aux_no
cmp qword ptr [rdx+8], r10
jne kodama_aux_no
cmp dword ptr [rdx+0x14], 1
ja kodama_aux_no
cmp dword ptr [rdx+0x10], 2
ja kodama_aux_no
mov qword ptr [rsp+0x20], r11
'''
    for row in AUX_ROWS:
        s += f'''mov r11, qword ptr [rsp+0x20]
mov r11, qword ptr [r11+{0x20+row['row']*0x18}]
test r11, r11
je {fail}
mov rax, qword ptr [r11]
test rax, rax
je {fail}
mov r11, qword ptr [r11+8]
test r11, r11
je {fail}
cmp dword ptr [r11+8], {row['hash_capacity']}
jne {fail}
mov rdx, qword ptr [r11+0x10]
test rdx, rdx
je {fail}
'''
        for offset, (q,) in enumerate(struct.iter_unpack('<Q', bytes.fromhex(row['header']))):
            s += f'movabs r10, {q}\ncmp qword ptr [rax+{offset*8}], r10\njne {fail}\n'
        for entry in row['hash_probe_trace']:
            q = entry['key'] | (entry['index'] << 32)
            s += f'movabs r10, {q}\ncmp qword ptr [rdx+{entry["bucket"]*8}], r10\njne {fail}\n'
        s += f'''cmp dword ptr [rax+{0x30+row['index']*4}], {row['offset']}
jne {fail}
cmp dword ptr [rax+{0x34+row['index']*4}], {row['end']}
jne {fail}
lea rcx, [rax+{row['offset']}]
lea r8, [rip+kodama_aux_bytes]
mov edx, {len(bytes.fromhex(AUX_HEX))//8}
call kodama_aux_compare
test al, al
je {fail}
'''
    return s + '''mov eax, 1
add rsp, 0x48
ret
kodama_aux_no:
xor eax, eax
add rsp, 0x48
ret
kodama_aux_compare:
mov rax, qword ptr [r8+2]
cmp qword ptr [rcx], rax
jne kodama_aux_compare_no
add r8, 10
add rcx, 8
dec edx
jne kodama_aux_compare
mov eax, 1
ret
kodama_aux_compare_no:
xor eax, eax
ret
kodama_aux_bytes:
''' + immediates(AUX_HEX)


def resource_source():
    # RCX=controller, R8=common bank, R9=entry params; called before the parent
    # repeats its local player, epoch, request, definition and resource checks.
    s = '''kodama_resources:
sub rsp, 0x68
mov qword ptr [rsp+0x20], rcx
mov qword ptr [rsp+0x28], r8
mov qword ptr [rsp+0x30], r9
mov rax, qword ptr [rcx+0x50]
test rax, rax
je kodama_resources_no
mov qword ptr [rsp+0x38], rax
mov rax, qword ptr [rax+0x38]
test rax, rax
je kodama_resources_no
cmp dword ptr [rax+0x50], 1
ja kodama_resources_no
mov qword ptr [rsp+0x40], rax
add rcx, 0x70
mov edx, 1206
xor r8d, r8d
call {signpost_action_lookup}
test rax, rax
je kodama_resources_no
cmp dword ptr [rax], 1206
jne kodama_resources_no
cmp byte ptr [rax+0x40], 0
je kodama_resources_no
mov r8, qword ptr [rsp+0x28]
cmp qword ptr [rax+0x38], r8
jne kodama_resources_no
mov qword ptr [rsp+0x48], rax
mov rax, qword ptr [rax+0x20]
test rax, rax
je kodama_resources_no
mov qword ptr [rsp+0x50], rax
mov edx, 1206
call SCHEDULE
test al, al
je kodama_resources_no
mov rcx, qword ptr [rsp+0x40]
xor edx, edx
call {data} + 0x3E00
test al, al
je kodama_resources_no
mov rcx, qword ptr [rsp+0x20]
mov rax, qword ptr [rsp+0x38]
cmp qword ptr [rcx+0x50], rax
jne kodama_resources_no
mov r8, qword ptr [rsp+0x40]
cmp qword ptr [rax+0x38], r8
jne kodama_resources_no
cmp dword ptr [r8+0x50], 1
ja kodama_resources_no
mov r8, qword ptr [rsp+0x28]
cmp qword ptr [rcx+0x80], r8
jne kodama_resources_no
mov rdx, qword ptr [rsp+0x48]
cmp dword ptr [rdx], 1206
jne kodama_resources_no
cmp byte ptr [rdx+0x40], 0
je kodama_resources_no
cmp qword ptr [rdx+0x38], r8
jne kodama_resources_no
mov rax, qword ptr [rsp+0x50]
cmp qword ptr [rdx+0x20], rax
jne kodama_resources_no
mov edx, 1206
call SCHEDULE
test al, al
je kodama_resources_no
mov rax, qword ptr [rsp+0x30]
mov r8, qword ptr [rsp+0x28]
mov edx, 1205
call SCHEDULE
test al, al
je kodama_resources_no
mov rcx, qword ptr [rsp+0x20]
call AUXILIARY
test al, al
je kodama_resources_no
mov eax, 1
add rsp, 0x68
ret
kodama_resources_no:
xor eax, eax
add rsp, 0x68
ret
'''
    return s.replace('SCHEDULE', call_at(SCHEDULE_OFFSET)).replace('AUXILIARY', call_at(AUX_OFFSET))


def apply_kodama_transform(parent):
    if digest(parent) != PARENT_SHA256:
        raise ValueError('Exact tested Soul Purge candidate required')
    plan = deepcopy(parent)
    hooks = {h['name']: h for h in plan['hooks']}
    ks = Ks(KS_ARCH_X86, KS_MODE_64)

    def encode(h, text=None, offset=None):
        v = {k: 0x140000000+r for k, r in plan['targets'].items()}
        v.update(data=0x144000000+plan['data_offset'], **{'return': 0x140000000+h['rva']+h['length']})
        return bytes(ks.asm((text if text is not None else h['asm']).format(**v),
                            0x144000000+(h['code_offset'] if offset is None else offset))[0])

    def append(name, offset, text):
        h = hooks[name]
        before = encode(h)
        gap = offset-h['code_offset']-len(before)
        if gap < 0:
            raise ValueError('Occupied owned helper space: '+name)
        h['asm'] += '\n'+'nop\n'*gap+text
        if not encode(h).startswith(before):
            raise ValueError('Carrier prefix changed: '+name)

    append('HE_MapPreviewCameraHeightPrivate', DEFINITION_OFFSET, definition_source())
    append('HE_MapVisualReadyPrivate', SCHEDULE_OFFSET, schedule_source())
    append('HE_OrochiZeroLengthRay', AUX_OFFSET, auxiliary_source())
    append('HE_OrochiStalledInvalidRayExit', RESOURCE_OFFSET, resource_source())
    carrier = hooks[spells.CARRIER_NAME]
    prefix, rest = carrier['asm'].split('dung_fan_helper:')
    helper, rest = ('dung_fan_helper:'+rest).split('arrow_sloth_lookup_entry:')

    def unpad(s):
        s = s.rstrip()+'\n'
        while s.endswith('nop\n'):
            s = s[:-4]
        return s

    helper = unpad(helper)
    old = 'call {data} + 116224\n'
    if helper.count(old) != 2:
        raise ValueError('Definition pre/post guards missing')
    helper = helper.replace(old, 'call '+call_at(DEFINITION_OFFSET)+'\n')
    for label in ('wind_weakness_dragon_alternate', 'wind_weakness_dragon_post_alternate'):
        anchor = 'mov ecx, -1\ncmp dword ptr [rsp+0x94], 1165\njne '+label+'\n'
        replacement = f'''mov ecx, 60012
cmp dword ptr [rsp+0x94], 1205
je {label}
'''+anchor
        helper = _once(helper, anchor, replacement)
    helper = _once(helper, 'dung_fan_schedule:\njmp {data} + 112128\n',
                   'dung_fan_schedule:\njmp '+call_at(SCHEDULE_OFFSET)+'\n')
    anchor = 'mov edx, dword ptr [rsp+0x94]\ncmp edx, 1165\nje wind_weakness_dragon_extra_guard\n'
    helper = _once(helper, anchor, '''mov edx, dword ptr [rsp+0x94]
cmp edx, 1205
jne kodama_dispatch_existing_extra
mov rcx, rdi
mov r8, qword ptr [rsp+0x80]
mov r9, qword ptr [rsp+0xD0]
call '''+call_at(RESOURCE_OFFSET)+'''
test al, al
je dung_fan_restore
jmp wind_weakness_dragon_extra_done
kodama_dispatch_existing_extra:
'''+anchor)
    hs = len(encode(carrier, helper, spells.HELPER_OFFSET))
    if hs > 0x1800:
        raise ValueError('Fixed dispatch helper capacity exceeded')
    carrier['asm'] = prefix+helper+'nop\n'*(0x1800-hs)+'arrow_sloth_lookup_entry:'+rest

    for name, suffix in (('HE_InputA', 'a'), ('HE_InputB', 'b')):
        h = hooks[name]
        anchor = f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        extra = ''.join(f'mov ecx, {m}\ncmp dword ptr [rdx], {a}\nje special_item_input_found_{suffix}\n'
                        for a, m in ((1205,122),(1206,0)))
        h['asm'] = _once(h['asm'], anchor, extra+anchor)

    # Existing injury resolver still requires an exact selected common hurt
    # transition and local owner; extend only eligible transformation sources.
    h = hooks['HE_MapVisualRestorePrivate']
    head, sep, tail = h['asm'].partition('item_recast_movement_guard:\n')
    if not sep:
        raise ValueError('Fixed recast entry missing')
    head = unpad(head)
    anchor = 'jutsu_chain_hurt_next_613:\n'
    extra = ''
    for i, action in enumerate((1205,1206)):
        extra += f'''cmp edx, {action}
jne kodama_hurt_next_{action}
lea rdi, [r15+{HURT_ROWS_OFFSET-0xF000+i*104}]
jmp item_hurt_cast_found
kodama_hurt_next_{action}:
'''
    head = _once(head, anchor, anchor+extra)
    gap = 0x23A00-h['code_offset']-len(encode(h, head))
    if gap < 0:
        raise ValueError('Injury prefix would move fixed recast entry')
    h['asm'] = head+'nop\n'*gap+sep+tail
    rows = b''.join(struct.pack('<2i96s', a, m, bytes.fromhex(PARAMS[a])[0x40:0xA0])
                    for a, m in ((1205,122),(1206,0)))
    append(h['name'], HURT_ROWS_OFFSET, '.byte '+','.join(map(str,rows))+'\n')
    # The existing relocation builder uses these intervals to separate code
    # from unreachable tables. Include the appended definition code, while
    # excluding the new fixed native-injury rows from instruction decoding.
    intervals = plan['abyss_assembly_code_intervals']
    if intervals.get('HE_MapPreviewCameraHeightPrivate') != [[0,0xA00]]:
        raise ValueError('Unexpected prior definition/data intervals')
    intervals['HE_MapPreviewCameraHeightPrivate'].append(
        [DEFINITION_OFFSET-0x2B000,len(encode(hooks['HE_MapPreviewCameraHeightPrivate']))])
    if 'HE_MapVisualRestorePrivate' in intervals:
        raise ValueError('Unexpected prior injury data interval')
    intervals['HE_MapVisualRestorePrivate'] = [[0,HURT_ROWS_OFFSET-0x23000]]
    changed = []
    for old, new in zip(parent['hooks'], plan['hooks']):
        if new['asm'] != old['asm']:
            changed.append(new['name'])
        if len(encode(new)) > new['code_capacity']:
            raise ValueError('Owned helper capacity exceeded: '+new['name'])
    plan['kodama_transform_candidate'] = dict(revision=1,item=ITEM,
        actions=[1205,1206], native_visual_template=408470,
        exact_common_parameters_events_timing=True,
        native_cost_visual_lifecycle_and_cancellation=True,
        native_injury_protection=True, inventory_save_model_writes=False,
        changed_hooks=changed, live_confirmation_pending=True)
    if digest(parent) != PARENT_SHA256:
        raise ValueError('Parent mutated')
    return plan
