"""Portable dual-boss execution using independently owned native resources.

Retain the complete Beta 5.4.1 Orochi bodies and numerical guards. Route the
Nine Tails heavy input to its own current-generation bootstrap and native
4026/1210 -> 1273/1211 chain, with no actor, resource, HP or mission writes.
"""
from copy import deepcopy
import re

from hinoenma_orochi_trial import SAVE
from hinoenma_orochi_runtime import (
    VERSION as PREVIOUS_VERSION, CODE_SLOTS as PREVIOUS_SLOTS,
    validate_layout as previous_layout,
)
from hinoenma_ninetails_views import sources as native_views, PRIVATE_MAGIC

VERSION = '1.0.0-beta.5.4.2'
DATA_OFFSET = 0x44000
DATA_SIZE = 0x200
ALLOCATION_SIZE = 0x51000
CHANGED_INDICES = (71,72,73,74,75,76,77,80)
CODE_SLOTS = ((0x46000,0x4000),)+tuple(
    (offset,0x1000) for offset in range(0x4A000,0x51000,0x1000))
PRIVATE = re.compile(r'(?m)^mov (r(?:ax|cx|dx|bx|bp|si|di|[89]|1[0-5])), '
                     r'\{(ninetails_data|production_data)\}$')
TOKEN = re.compile(r'\{(ninetails_data|production_data)\}')


def bind_nine(source, core_data_offset):
    """Convert audited private register MOVs to relocation-safe core offsets."""
    if len(PRIVATE.findall(source)) != len(TOKEN.findall(source)):
        raise ValueError('Every Nine Tails private address must use a register MOV')

    def convert(match):
        register,name=match.groups()
        delta=0 if name=='production_data' else DATA_OFFSET-core_data_offset
        return f'mov {register}, {{data}}'+(f'\nadd {register}, {hex(delta)}' if delta else '')

    return PRIVATE.sub(convert,source)


ROUTE_SAVE = 'pushfq\npush rax\npush r11\n'
ROUTE_RESTORE = 'pop r11\npop rax\npopfq\n'


def heavy_route(prefix):
    # The native heavy function supplies a controller in RCX. Bound its
    # locked-target pointer before reading its template; never use a saved
    # target address to decide whether this new scene needs discovery.
    return ROUTE_SAVE+f'''cmp rcx, 0x10000
jb {prefix}_orochi
mov r11, 0x800000000000
cmp rcx, r11
jae {prefix}_orochi
mov rax, qword ptr [rcx+0x640]
cmp rax, 0x10000
jb {prefix}_orochi
cmp rax, r11
jae {prefix}_orochi
cmp dword ptr [rax], 0xC9AAF
jne {prefix}_orochi
'''+ROUTE_RESTORE+f'''jmp {prefix}_nine
{prefix}_orochi:
'''+ROUTE_RESTORE


def active_route(prefix,core_data_offset):
    # A discarded or interrupted Nine Tails scene can leave phase1 behind.
    # Require the current core generation and player/header before choosing
    # any Nine Tails view; otherwise the untouched Orochi body remains active.
    delta=DATA_OFFSET-core_data_offset
    return ROUTE_SAVE+f'''mov r11, {{data}}
mov rax, r11
add rax, {hex(delta)}
cmp dword ptr [rax], 0x{PRIVATE_MAGIC:X}
jne {prefix}_orochi
cmp dword ptr [rax+0x74], 1
jne {prefix}_orochi
mov r11d, dword ptr [r11+0x1C]
cmp dword ptr [rax+4], r11d
jne {prefix}_orochi
mov r11, {{data}}
mov r11, qword ptr [r11+0x10]
cmp qword ptr [rax+8], r11
jne {prefix}_orochi
cmp r11, 0x10000
jb {prefix}_orochi
push rax
mov rax, 0x800000000000
cmp r11, rax
pop rax
jae {prefix}_orochi
push rax
mov rax, {{player_slot}}
cmp qword ptr [rax], r11
pop rax
jne {prefix}_orochi
mov r11, qword ptr [r11]
cmp qword ptr [rax+0xA0], r11
jne {prefix}_orochi
mov r11, qword ptr [rax+8]
mov r11, qword ptr [r11+0x230]
cmp r11, 0x10000
jb {prefix}_orochi
push rax
mov rax, 0x800000000000
cmp r11, rax
pop rax
jae {prefix}_orochi
push rax
mov rax, qword ptr [rax+8]
cmp qword ptr [r11], rax
pop rax
jne {prefix}_orochi
mov r11, qword ptr [r11+8]
cmp qword ptr [rax+0x10], r11
jne {prefix}_orochi
cmp r11, 0x10000
jb {prefix}_orochi
push rax
mov rax, 0x800000000000
cmp r11, rax
pop rax
jae {prefix}_orochi
push rax
mov rax, qword ptr [rax+8]
cmp qword ptr [r11+0x50], rax
pop rax
jne {prefix}_orochi
push rax
mov rax, qword ptr [rax+0x18]
test rax, rax
je {prefix}_no_target
cmp qword ptr [r11+0x640], rax
je {prefix}_associated
cmp qword ptr [r11+0x5B0], rax
je {prefix}_associated
cmp qword ptr [r11+0x5D8], rax
je {prefix}_associated
pop rax
mov r11, qword ptr [r11+0x58]
test r11, r11
je {prefix}_orochi
cmp qword ptr [rax+0x68], r11
je {prefix}_owned_action
cmp qword ptr [rax+0x1A8], r11
jne {prefix}_orochi
jmp {prefix}_owned_action
{prefix}_no_target:
pop rax
jmp {prefix}_orochi
{prefix}_associated:
pop rax
{prefix}_owned_action:
'''+ROUTE_RESTORE+f'''jmp {prefix}_nine
{prefix}_orochi:
'''+ROUTE_RESTORE


def sources(baseline,menu_guard):
    """Return relocated dual bodies; the previous Orochi body stays verbatim."""
    from hinoenma_ninetails_binding import bootstrap
    views,targets=native_views(baseline,menu_guard)
    if len(views)!=len(CHANGED_INDICES):
        raise ValueError('Exact eight Nine Tails views required')
    result=[]
    for ordinal,(index,nine,slot) in enumerate(zip(CHANGED_INDICES,views,CODE_SLOTS)):
        old=baseline['hooks'][index]
        if any(old[field]!=nine[field] for field in ('rva','length','original')):
            raise ValueError('Nine Tails native entry differs from previous release')
        source=nine['asm']
        if ordinal==0:
            if not source.startswith(SAVE):
                raise ValueError('Frozen Nine Tails heavy save differs')
            source=SAVE+bootstrap(prefix='np_od',original_label='np_oh_original')+source[len(SAVE):]
        source=bind_nine(source,baseline['data_offset'])
        prefix='np_route'+str(ordinal)
        router=(heavy_route(prefix) if ordinal==0 else
                active_route(prefix,baseline['data_offset']))
        hook=deepcopy(old)
        hook.update(code_offset=slot[0],code_capacity=slot[1],
            asm=router+old['asm']+f'\n{prefix}_nine:\n'+source,
            purpose=old['purpose']+'; dynamically bind and route the independent native Nine Tails execution')
        if hook['asm'].count(old['asm'])!=1:
            raise ValueError('Original Orochi body must remain exact once')
        result.append(hook)
    targets.update(loaded_package_tree=0x1871700,motion_resource_vtable=0x13C8FA0,
                   event_wrapper_vtable=0x12C5408)
    return result,targets


def apply_ninetails_execution(baseline,menu_guard):
    if (baseline.get('tool_version')!=PREVIOUS_VERSION
            or len(baseline.get('hooks',()))!=81):
        raise ValueError('Exact complete Beta 5.4.1 source basis required')
    previous_layout(baseline)
    plan=deepcopy(baseline)
    hooks,targets=sources(baseline,menu_guard)
    for index,hook in zip(CHANGED_INDICES,hooks):plan['hooks'][index]=hook
    for name,rva in targets.items():
        if name in plan['targets'] and plan['targets'][name]!=rva:
            raise ValueError('Conflicting native Nine Tails target '+name)
        plan['targets'][name]=rva
    plan.update(tool_version=VERSION,allocation_size=ALLOCATION_SIZE,
        protected_data_pages=baseline['protected_data_pages']+[[DATA_OFFSET,0x45000]],
        ninetails_execution_revision=1,ninetails_binding_data_offset=DATA_OFFSET,
        ninetails_binding_data_size=DATA_SIZE,ninetails_native_chain=[3008,4026,1273,3000,0],
        ninetails_native_motion_ids=[1210,1211],ninetails_target_ready=[0xC9AAF,3174,31001],
        ninetails_changed_indices=list(CHANGED_INDICES),ninetails_scene_gameplay_validated=True,
        ninetails_fresh_exe_gameplay_validated=False,ninetails_execution_validated=False,
        ninetails_bootstrap_instance_addresses=False,stage='local_beta542_dual_boss_execution')
    unchanged=set(range(81))-set(CHANGED_INDICES)
    if any(plan['hooks'][i]!=baseline['hooks'][i] for i in unchanged):
        raise ValueError('Nine Tails integration changed an unrelated hook')
    validate_layout(plan)
    return plan


def validate_layout(plan):
    # Check the previous core and resource reservations through its frozen
    # validator after restoring only layout fields changed by this revision.
    previous=deepcopy(plan)
    previous.update(tool_version=PREVIOUS_VERSION,allocation_size=0x43000,
                    protected_data_pages=plan['protected_data_pages'][:-1])
    for ordinal,index in enumerate(CHANGED_INDICES):
        old_ordinal=index-71
        previous['hooks'][index]['code_offset'],previous['hooks'][index]['code_capacity']=PREVIOUS_SLOTS[old_ordinal]
    previous_layout(previous)
    if (plan.get('tool_version')!=VERSION or len(plan.get('hooks',()))!=81
            or plan.get('allocation_size')!=ALLOCATION_SIZE
            or plan.get('ninetails_execution_revision')!=1
            or plan.get('ninetails_binding_data_offset')!=DATA_OFFSET
            or plan.get('ninetails_binding_data_size')!=DATA_SIZE
            or plan.get('ninetails_changed_indices')!=list(CHANGED_INDICES)
            or plan['protected_data_pages'][-1]!=[DATA_OFFSET,0x45000]
            or tuple((plan['hooks'][i]['code_offset'],plan['hooks'][i]['code_capacity'])
                     for i in CHANGED_INDICES)!=CODE_SLOTS):
        raise ValueError('Exact portable dual-boss layout required')
    ranges=sorted((h['code_offset'],h['code_offset']+h['code_capacity']) for h in plan['hooks'])
    pages=plan['protected_data_pages']
    if (any(a[1]>b[0] for a,b in zip(ranges,ranges[1:]))
            or ranges[-1][1]>ALLOCATION_SIZE
            or any(max(a,c)<min(b,d) for a,b in ranges for c,d in pages)):
        raise ValueError('Dual-boss code overlaps reserved memory')
    entries=sorted((h['rva'],h['rva']+h['length']) for h in plan['hooks'])
    if any(a[1]>b[0] for a,b in zip(entries,entries[1:])):
        raise ValueError('Dual-boss native entry overlaps another hook')


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
