"""Portable Abyss interaction routing and per-player resource lifetime."""
from copy import deepcopy
from hinoenma_ninetails_runtime import (
    VERSION as PREVIOUS_VERSION, validate_layout as previous_layout)
import hinoenma_abyss_actions as actions
from hinoenma_abyss_lifetime import (
    cleanup_hook, spawn_hook, DATA_OFFSET, DATA_SIZE, CODE_OFFSET, SLOT_COUNT)
from hinoenma_abyss_assembly import assemble

VERSION = '1.0.0-beta.5.6'
ALLOCATION_SIZE = 0x55000
CHANGED_INDICES = (1, 8, 9, 39, 70)

def gate(rows):
    text = actions.gate_asm(rows)
    needle = 'cmp word ptr [r10+8], 0x101\njne abyss_actions_gate_bad\n'
    if text.count(needle) != 1:
        raise ValueError('Exact native availability boundary required')
    text = text.replace(needle, '''cmp word ptr [r10+8], 0x101
je abyss_cancel_request_flags_valid
cmp qword ptr [rsp+0x120], 2
jne abyss_actions_gate_bad
cmp word ptr [r10+8], 1
jne abyss_actions_gate_bad
mov r9, qword ptr [rdi+0x58]
'''+actions.pointer('r9', 'abyss_actions_gate_bad')+'''mov rax, qword ptr [rdi+0x80]
cmp qword ptr [r9+0x38], rax
jne abyss_actions_gate_bad
cmp byte ptr [r9+0x40], 1
jne abyss_actions_gate_bad
mov eax, dword ptr [r9]
sub eax, 73
cmp eax, 2
ja abyss_actions_gate_bad
abyss_cancel_request_flags_valid:
''')
    marker = 'mov rcx, qword ptr [rsp+0x88]\nmov edx, 170\ncall {native_ladder_set_action}\n'
    if text.count(marker) != 1:
        raise ValueError('Exact validated queue boundary required')
    text = text.replace(marker, '''mov rcx, qword ptr [rsp+0x80]
call {data} + 0x42800
test eax, eax
je abyss_lifetime_action_refused
mov rcx, qword ptr [rsp+0x88]
mov edx, 170
call {native_ladder_set_action}
jmp abyss_actions_gate_bad
abyss_lifetime_action_refused:
mov dword ptr [rsp+0xB4], 0
''')
    return text

def apply_abyss(previous):
    if previous.get('tool_version') != PREVIOUS_VERSION or len(previous['hooks']) != 81:
        raise ValueError('Complete released Beta5.4.2 source required')
    previous_layout(previous)
    plan = actions.apply_actions(previous, gate)
    plan['targets'].update(abyss_native_retain=0x8CEA40, abyss_native_release=0x8CEC80)
    plan['hooks'][1] = spawn_hook(previous['hooks'][1])
    plan['hooks'].append(cleanup_hook(plan))
    plan.update(tool_version=VERSION, allocation_size=ALLOCATION_SIZE,
        protected_data_pages=previous['protected_data_pages']+[[0x53000,0x54000],[0x54000,0x55000]],
        abyss_actions_revision=3, abyss_cancel_revision=1, abyss_resource_lifetime_revision=1,
        abyss_resource_data_offset=DATA_OFFSET, abyss_resource_data_size=DATA_SIZE,
        abyss_resource_ticket_slots=SLOT_COUNT, abyss_changed_indices=list(CHANGED_INDICES),
        abyss_native_motion_ids=[900,901,902], abyss_native_action_chain=[170,73,74,75,0],
        abyss_fresh_exe_gameplay_validated=False, abyss_continuous_floors_validated=False,
        abyss_boat_gameplay_validated=False, local_package_only=False,
        stage='local_beta55_abyss_resource_lifetime')
    original = assemble(previous,0x140000000,0x144000000)
    current = assemble(plan,0x140000000,0x144000000)
    if tuple(i for i,(a,b) in enumerate(zip(original,current)) if a['payload'] != b['payload']) != CHANGED_INDICES:
        raise ValueError('Unexpected changes outside the five bounded existing bodies')
    if any(a['patched'] != b['patched'] for a,b in zip(original,current)):
        raise ValueError('Existing 81 native entries changed')
    prefix = len(original[70]['payload'])
    # Relocation decoding must not treat frozen descriptor bytes or padding as code.
    life_prefix_plan=deepcopy(plan)
    life_prefix_plan['hooks']=[deepcopy(plan['hooks'][81])]
    from hinoenma_abyss_lifetime import release_asm
    life_prefix_plan['hooks'][0]['asm']=release_asm()
    life_prefix=len(assemble(life_prefix_plan,0x140000000,0x144000000)[0]['payload'])
    plan['abyss_assembly_code_intervals'] = {
        plan['hooks'][70]['name']: [[0,prefix],[0x2000,0x2000+plan['abyss_helper_code_size']]],
        plan['hooks'][81]['name']: [[0,life_prefix],[0x800,len(current[81]['payload'])]]}
    validate_layout(plan)
    from hinoenma_abyss_guide import candidate_plan
    return candidate_plan(plan)

def validate_layout(plan):
    if (plan.get('tool_version') != VERSION or len(plan.get('hooks',())) != 82
            or plan.get('allocation_size') != ALLOCATION_SIZE or plan['data_offset'] != 0xF000
            or plan.get('abyss_resource_data_offset') != DATA_OFFSET
            or plan.get('abyss_resource_data_size') != DATA_SIZE
            or plan.get('abyss_resource_ticket_slots') != SLOT_COUNT
            or plan.get('abyss_changed_indices') != list(CHANGED_INDICES)
            or plan['protected_data_pages'][-2:] != [[0x53000,0x54000],[0x54000,0x55000]]):
        raise ValueError('Exact portable Abyss lifetime layout required')
    previous = deepcopy(plan)
    previous.update(tool_version=PREVIOUS_VERSION,allocation_size=0x51000,
                    hooks=previous['hooks'][:81],protected_data_pages=plan['protected_data_pages'][:-2])
    from menu_preview_reload_portable import new_sources
    previous['hooks'][70]['asm']=new_sources()[2]
    previous_layout(previous)
    h=plan['hooks'][81]
    if (h['name'],h['rva'],h['length'],h['original'],h['code_offset'],h['code_capacity']) != (
            'HE_PlayerResourceLifetimeCleanup',0x753616,6,'48 8B 0E 48 8B D7',CODE_OFFSET,0x2000):
        raise ValueError('Exact post-cleanup release boundary required')
    code=sorted((h['code_offset'],h['code_offset']+h['code_capacity']) for h in plan['hooks'])
    pages=plan['protected_data_pages']
    entries=sorted((h['rva'],h['rva']+h['length']) for h in plan['hooks'])
    if (any(a[1]>b[0] for a,b in zip(code,code[1:])) or code[-1][1]>ALLOCATION_SIZE
            or any(max(a,c)<min(b,d) for a,b in code for c,d in pages)
            or any(a[1]>b[0] for a,b in zip(entries,entries[1:]))):
        raise ValueError('Abyss code, data or native entries overlap')

def ct_compatible_plan(plan):
    from menu_preview_portable_integration import frozen
    validate_layout(plan)
    result=deepcopy(plan)
    for hook in result['hooks']:
        hook['asm']='\n'.join(line if line.lstrip().startswith('.byte ') else
            frozen.SOURCE_NUMBER.sub(lambda m:hex(int(m.group(0),
                16 if m.group(0).lower().startswith('0x') else 10)),line)
            for line in hook['asm'].split('\n'))
    return result
