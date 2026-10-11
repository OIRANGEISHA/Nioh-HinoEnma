"""Portable native Orochi execution, derived from the confirmed scene trial.

Bind resources on the original heavy-transition path. Reuse seven tested
resource views and two scoped numerical guards, then protect the verified
pre-pairing windup from Living Weapon readiness. Keep all previous payloads.
There are no fixed actor, stack, package, descriptor or process addresses.
"""
from copy import deepcopy
import re

from hinoenma_orochi_trial import SAVE
from hinoenma_orochi_candidate_v5 import candidate_plan
from hinoenma_orochi_ray_guard_v2 import addon_plan
from hinoenma_orochi_binding import bootstrap
from hinoenma_orochi_weapon_guard import NATIVE_QUERY_FRAME, sources as weapon_guard_sources

VERSION = '1.0.0-beta.5.4.1'
DATA_OFFSET = 0x42000
ALLOCATION_SIZE = 0x43000
CODE_SLOTS = (((0x36000, 0x2000),)
              + tuple((n, 0x1000) for n in range(0x3A000, 0x42000, 0x1000))
              + ((0x38000, 0x1000),))
PRIVATE = re.compile(r'(?m)^mov (r(?:ax|cx|dx|bx|bp|si|di|[89]|1[0-5])), '
                     r'\{(data|orochi_data|production_data|execution_data)\}$')
TOKEN = re.compile(r'\{(data|orochi_data|production_data|execution_data)\}')
NATIVE_SPANS = ((0x73F860, 0x1A0), (0x73FA40, 0xD1), (0x954E73, 0x15D),
                (0x954FD0, 0x306), (0x968A10, 0x34B), (0x7DCF10, 0x11D),
                (0x2165F0, 0x592), (0x6E84EA, 0x26A), (0x7DEB70, 0x2AD),
                (NATIVE_QUERY_FRAME[0], NATIVE_QUERY_FRAME[1]-NATIVE_QUERY_FRAME[0]))


def bind(source, core_data_offset):
    if len(PRIVATE.findall(source)) != len(TOKEN.findall(source)):
        raise ValueError('Every private address must use an audited register MOV')

    def convert(match):
        register, name = match.groups()
        delta = (core_data_offset if name == 'production_data' else DATA_OFFSET)-core_data_offset
        return f'mov {register}, {{data}}'+(f'\nadd {register}, {hex(delta)}' if delta else '')

    return PRIVATE.sub(convert, source)


def native_target_record(source, prefix):
    before = f'''mov rdx, qword ptr [r11+0x1F0]
cmp qword ptr [rax+0x58], rdx
jne {prefix}_original
'''
    after = f'''mov rdx, qword ptr [rax+0x58]
test rdx, rdx
je {prefix}_original
mov rcx, qword ptr [rdx+0x38]
test rcx, rcx
je {prefix}_original
cmp rcx, qword ptr [rax+0x70]
je {prefix}_target_record_owned
cmp rcx, qword ptr [rax+0x78]
je {prefix}_target_record_owned
cmp rcx, qword ptr [rax+0x80]
jne {prefix}_original
{prefix}_target_record_owned:
'''
    if source.count(before) != 1:
        raise ValueError('Frozen paired-target ownership boundary changed')
    return source.replace(before, after, 1)


def sources(baseline, menu_guard):
    # Only private addresses from these standalone plans are replaced. All
    # native targets retain their verified module-relative identity.
    execution = candidate_plan(baseline, 0x140000000, 0x144000000, menu_guard)
    numerical = addon_plan(baseline, 0x140000000, 0x144000000, 0x145005000)
    hooks = deepcopy(execution['hooks'][:7]+numerical['hooks'])
    if not hooks[0]['asm'].startswith(SAVE):
        raise ValueError('Frozen heavy prologue differs')
    hooks[0]['asm'] = SAVE+bootstrap()+hooks[0]['asm'][len(SAVE):]
    for hook, prefix in zip(hooks[-2:], ('zr', 'sr')):
        hook['asm'] = native_target_record(hook['asm'], prefix)
    stalled = hooks[-1]
    before = '''cmp rdi, qword ptr [r11+0x1D8]
jne sr_original
cmp rsi, qword ptr [r11+0x1E0]
jne sr_original
'''
    after = '''cmp qword ptr [rsp+0xB0], 0
jne sr_original
cmp rdi, 0x10000
jb sr_original
cmp rsi, 0x10000
jb sr_original
mov rax, 0x800000000000
cmp rdi, rax
jae sr_original
cmp rsi, rax
jae sr_original
cmp qword ptr [rdi+0x48], 0
jne sr_original
'''
    if stalled['asm'].count(before) != 1:
        raise ValueError('Frozen stalled-ray boundary differs')
    stalled['asm'] = stalled['asm'].replace(before, after, 1)
    stalled['asm'] = stalled['asm'].replace('sr_no_hit:\n',
        'sr_no_hit:\nmov qword ptr [r11+0x1D8], rdi\nmov qword ptr [r11+0x1E0], rsi\n', 1)
    weapon_hooks, weapon_targets = weapon_guard_sources()
    hooks.extend(weapon_hooks)
    for hook, (offset, capacity) in zip(hooks, CODE_SLOTS):
        hook['code_offset'], hook['code_capacity'] = offset, capacity
        hook['asm'] = bind(hook['asm'], baseline['data_offset'])
    targets = {name: rva for plan in (execution, numerical) for name, rva in plan['targets'].items()
               if name not in ('production_data', 'execution_data')}
    targets.update(loaded_package_tree=0x1871700, motion_resource_vtable=0x13C8FA0,
                   event_wrapper_vtable=0x12C5408)
    targets.update(weapon_targets)
    return hooks, targets


def apply_orochi_execution(baseline, menu_guard):
    if len(baseline.get('hooks', ())) != 71 or baseline.get('tool_version') != '1.0.0-beta.5.3.2':
        raise ValueError('The exact previous71 profile is required')
    plan = deepcopy(baseline)
    hooks, targets = sources(baseline, menu_guard)
    for name, rva in targets.items():
        if name in plan['targets'] and plan['targets'][name] != rva:
            raise ValueError('Conflicting native execution target: '+name)
        plan['targets'][name] = rva
    plan['hooks'].extend(hooks)
    plan.update(tool_version=VERSION, allocation_size=ALLOCATION_SIZE,
        protected_data_pages=baseline['protected_data_pages']+[[DATA_OFFSET, ALLOCATION_SIZE]],
        orochi_execution_revision=3, orochi_hook_count=10, orochi_resource_revision=5,
        orochi_ray_guard_revision=2, orochi_binding_data_offset=DATA_OFFSET,
        orochi_binding_data_size=0x200, orochi_native_chain=[3008, 3491, 4000, 3000, 0],
        orochi_native_motion_ids=[1200, 1201], orochi_bootstrap_instance_addresses=False,
        orochi_fresh_exe_gameplay_validated=False, ninetails_execution_validated=False,
        stage='local_beta541_orochi_execution')
    validate_layout(plan)
    return plan


def validate_layout(plan):
    from menu_preview_coldstart_portable import validate_layout as previous_layout
    old = deepcopy(plan)
    old.update(tool_version='1.0.0-beta.5.3.2', allocation_size=0x36000,
               hooks=old['hooks'][:71], protected_data_pages=old['protected_data_pages'][:-1])
    previous_layout(old)
    if (plan.get('tool_version') != VERSION or len(plan.get('hooks', ())) != 81
            or plan.get('allocation_size') != ALLOCATION_SIZE
            or plan.get('orochi_execution_revision') != 3
            or plan.get('orochi_hook_count') != 10
            or plan.get('orochi_binding_data_offset') != DATA_OFFSET
            or plan.get('orochi_binding_data_size') != 0x200
            or plan['protected_data_pages'][-1] != [DATA_OFFSET, ALLOCATION_SIZE]):
        raise ValueError('Exact portable Orochi layout required')
    if tuple((h['code_offset'], h['code_capacity']) for h in plan['hooks'][71:]) != CODE_SLOTS:
        raise ValueError('Exact execution code capacities required')
    ranges = sorted((h['code_offset'], h['code_offset']+h['code_capacity']) for h in plan['hooks'])
    pages = plan['protected_data_pages']
    if (any(a[1] > b[0] for a, b in zip(ranges, ranges[1:]))
            or ranges[-1][1] > ALLOCATION_SIZE
            or any(max(a, c) < min(b, d) for a, b in ranges for c, d in pages)):
        raise ValueError('Execution code overlaps protected memory')
    sites = sorted((h['rva'], h['rva']+h['length']) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(sites, sites[1:])):
        raise ValueError('Native execution entry overlaps another hook')


def ct_compatible_plan(plan):
    from menu_preview_portable_integration import frozen
    validate_layout(plan)
    converted = deepcopy(plan)
    for hook in converted['hooks']:
        hook['asm'] = '\n'.join(line if line.lstrip().startswith('.byte ') else
            frozen.SOURCE_NUMBER.sub(lambda m: hex(int(m.group(0),
                16 if m.group(0).lower().startswith('0x') else 10)), line)
            for line in hook['asm'].split('\n'))
    return converted
