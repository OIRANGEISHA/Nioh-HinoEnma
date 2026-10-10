"""Portable Beta 5.3.2 cold-start readiness revision; no process access.

Only the existing Ready payload changes. Requests stay once per epoch;
temporary manager absence retries without discarding the epoch budget.
Native map loading gates precede budget consumption. All native readiness
and visual-construction checks remain mandatory.
"""
from copy import deepcopy

ASSET_WAIT_FRAMES = 1800
TOTAL_WAIT_FRAMES = 7200
TARGETS = dict(map_gate_one=0xC448E0, map_gate_two=0xC449A0,
    map_gate_one_root=0x189F430, map_gate_two_root=0x189F400)
NATIVE_SPANS = ((0xC448E0, 0x27), (0xC449A0, 0xA1A), (0xC002C0, 3))


def once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Exact frozen Ready boundary required')
    return source.replace(old, new)


def pointer(register, rejected):
    return f'''cmp {register}, 0x10000
jb {rejected}
mov r10, 0x800000000000
cmp {register}, r10
jae {rejected}
'''


def patch(plan):
    candidate = deepcopy(plan)
    found = [h for h in candidate['hooks'] if h['name'] == 'HE_MapVisualReadyPrivate']
    if len(found) != 1:
        raise ValueError('Exactly one Ready entry required')
    h = found[0]
    source = h['asm']
    source = once(source, 'je visual_ready_check\npreload_probe_first:', '''jne preload_probe_first
cmp dword ptr [r11+0x14], 4
je coldstart_retry_roots
cmp dword ptr [r11+0x14], 5
je coldstart_retry_roots
jmp visual_ready_check
preload_probe_first:''')
    source = once(source, 'mov dword ptr [r11+0x38], 0\nmov dword ptr [r11+0x14], 5',
        '''mov dword ptr [r11+0x38], 0
mov dword ptr [r11+0x34], 0
mov dword ptr [r11+0x3C], 0
coldstart_retry_roots:
mov dword ptr [r11+0x14], 5''')
    source = once(source, '''jne visual_ready_yes
mov r11, {data}
add r11, 0x15000
inc dword ptr [r11+0x1C]
cmp dword ptr [r11+0x1C], 480''', '''jne visual_ready_yes
jmp coldstart_pending
coldstart_asset_tick:
mov r11, {data}
add r11, 0x15000
inc dword ptr [r11+0x1C]
cmp dword ptr [r11+0x1C], 1800''')
    old_unlock = '''cmp dword ptr [r11+0x14], 3
jb visual_ready_unlock
cmp dword ptr [r11+0x14], 5
ja visual_ready_unlock
mov dword ptr [r11+0x14], 6
inc dword ptr [r11+0x24]
visual_ready_unlock:'''
    source = once(source, old_unlock, '''cmp dword ptr [r11+0x14], 3
je visual_ready_timeout
cmp dword ptr [r11+0x14], 4
je coldstart_pending
cmp dword ptr [r11+0x14], 5
je coldstart_pending
visual_ready_unlock:''')
    source = once(source,
        'mov dword ptr [rsp+0x88], 1\njmp preload_probe_unlock\nvisual_ready_timeout:',
        'mov dword ptr [rsp+0x88], 1\njmp visual_ready_unlock\nvisual_ready_timeout:')
    source = once(source,
        'inc dword ptr [r11+0x1C]\ncmp dword ptr [r11+0x1C], 1800',
        '''inc dword ptr [r11+0x1C]
mov eax, dword ptr [r11+0x1C]
add eax, dword ptr [r11+0x34]
cmp eax, 7200
jae visual_ready_timeout
cmp dword ptr [r11+0x1C], 1800''')
    # Gate helpers return an AL boolean, as at original 8C538A/8C5397.
    # Slot/state/selector are already scoped; absent root skips native calls.
    pending = '''coldstart_pending:
mov r11, {data}
add r11, 0x15000
mov dword ptr [r11+0x3C], 1
mov rax, {map_gate_one_root}
mov rax, qword ptr [rax]
''' + pointer('rax', 'coldstart_gate_wait') + '''call {map_gate_one}
test al, al
je coldstart_gate_wait
mov r11, {data}
add r11, 0x15000
mov dword ptr [r11+0x3C], 2
mov rax, {map_gate_two_root}
mov rax, qword ptr [rax]
''' + pointer('rax', 'coldstart_gate_wait') + '''call {map_gate_two}
test al, al
je coldstart_gate_wait
mov r11, {data}
add r11, 0x15000
mov dword ptr [r11+0x3C], 0
jmp coldstart_asset_tick
coldstart_gate_wait:
mov r11, {data}
add r11, 0x15000
inc dword ptr [r11+0x34]
mov eax, dword ptr [r11+0x34]
add eax, dword ptr [r11+0x1C]
cmp eax, 7200
jae visual_ready_timeout
mov dword ptr [rsp+0x88], 1
jmp visual_ready_unlock
'''
    # Shared data remains in its original RW/NX page. New fields34/3C were
    # unused padding; no gameplay/native objects are modified by this logic.
    source += pending
    h['asm'] = source
    for name, rva in TARGETS.items():
        if name in candidate['targets'] and candidate['targets'][name] != rva:
            raise ValueError('Conflicting native loading target')
        candidate['targets'][name] = rva
    candidate['menu_coldstart_revision'] = 1
    candidate['menu_asset_wait_frames'] = ASSET_WAIT_FRAMES
    candidate['menu_total_wait_frames'] = TOTAL_WAIT_FRAMES
    unchanged = [a == b for a, b in zip(plan['hooks'], candidate['hooks'])]
    if unchanged.count(False) != 1 or len(plan['hooks']) != len(candidate['hooks']):
        raise ValueError('Only Ready payload may change')
    return candidate


import menu_preview_reload_portable as previous
VERSION = '1.0.0-beta.5.3.2'


def apply_menu_preview(baseline):
    candidate = patch(previous.apply_menu_preview(baseline))
    candidate.update(tool_version=VERSION, stage='beta532_menu_coldstart',
        menu_coldstart_test_payload_verified=True,
        menu_aura_fresh_exe_validation_pending=False)
    validate_layout(candidate)
    return candidate


def validate_layout(plan):
    if (plan.get('tool_version') != VERSION or plan.get('menu_coldstart_revision') != 1
            or plan.get('menu_asset_wait_frames') != ASSET_WAIT_FRAMES
            or plan.get('menu_total_wait_frames') != TOTAL_WAIT_FRAMES):
        raise ValueError('Exact Beta 5.3.2 cold-start revision required')
    old = deepcopy(plan)
    old['tool_version'] = previous.VERSION
    old_ready = previous.previous._sources(plan['menu_visual_core_relative_continuation_delta'])[0]
    ready = [h for h in old['hooks'] if h['name'] == 'HE_MapVisualReadyPrivate']
    if len(ready) != 1:
        raise ValueError('Exactly one readiness entry required')
    ready[0]['asm'] = old_ready
    for name, rva in TARGETS.items():
        if plan['targets'].get(name) != rva:
            raise ValueError('Native cold-start loading target differs')
        old['targets'].pop(name)
    previous.validate_layout(old)
    expected = patch(old)
    if plan['hooks'] != expected['hooks'] or plan['targets'] != expected['targets']:
        raise ValueError('Cold-start source differs from the tested single-hook revision')


def ct_compatible_plan(plan):
    if plan.get('tool_version') != VERSION:
        return previous.ct_compatible_plan(plan)
    validate_layout(plan)
    converted = deepcopy(plan)
    number = previous.previous.frozen.SOURCE_NUMBER
    for h in converted['hooks']:
        h['asm'] = '\n'.join(line if line.lstrip().startswith('.byte ') else
            number.sub(lambda m: hex(int(m.group(0),
                16 if m.group(0).lower().startswith('0x') else 10)), line)
            for line in h['asm'].split('\n'))
    return converted
