"""Audited native Nine Tails execution read views.

Pure source transformation only: this module does not open a process, install
patches, discover actors or write game state. Runtime activates these views
only after binding and validating the current scene's owned resources.
All native branches, input, pairing, damage and terminal requests stay native.
"""
from copy import deepcopy
import re
from hinoenma_orochi_candidate_v5 import candidate_plan as frozen_candidate
from hinoenma_orochi_weapon_guard import pending_weapon_hook

BIND_SIZE = 0x200
TEMPLATE = 0xC9AAF
READY_ACTION = 3174
READY_MOTION = 31001
WINDUP_ACTION, PAIRED_ACTION = 4026, 1273
WINDUP_MOTION, PAIRED_MOTION = 1210, 1211
PRIVATE_MAGIC = 0x4643524F

# These are audited counts in the exact frozen seven resource-view bodies.
# Fail closed if an upstream instruction is added, removed or renamed.
COUNTS = ((1,1,0,1), (2,2,0,1), (1,1,1,2), (1,1,1,2),
          (2,2,1,3), (1,1,1,2), (1,1,1,2))
IDENTIFIERS = ((3491, WINDUP_ACTION), (4000, PAIRED_ACTION),
               (1200, WINDUP_MOTION), (1201, PAIRED_MOTION))


def replace_exact(source, before, after, count=1):
    if source.count(before) != count:
        raise ValueError('Frozen Nine Tails adaptation boundary changed')
    return source.replace(before, after)


def adapt_identifiers(source, counts):
    for (before, after), count in zip(IDENTIFIERS, counts):
        pattern = re.compile(r'(?<![A-Za-z0-9_])'+str(before)+r'(?![A-Za-z0-9_])')
        if len(pattern.findall(source)) != count:
            raise ValueError(f'Frozen identifier {before} count changed')
        source = pattern.sub(str(after), source)
    return source


def ready_owner_guard():
    # At this boundary rax is the current target action record. Its bank must
    # still be one of that target controller's actual three native slots.
    return '''cmp byte ptr [rax+0x40], 1
jne oh_original
mov rdx, qword ptr [rax+0x38]
test rdx, rdx
je oh_original
mov r9, qword ptr [r11+0xA8]
cmp rdx, qword ptr [r9+0x70]
je oh_ready_owned
cmp rdx, qword ptr [r9+0x78]
je oh_ready_owned
cmp rdx, qword ptr [r9+0x80]
jne oh_original
oh_ready_owned:
mov rax, qword ptr [rax+0x20]
test rax, rax
je oh_original
cmp dword ptr [rax+0x20], 31001
jne oh_original
'''


def weapon_guard():
    """Scoped native query86 false path for the proved Nine Tails windup.

    Independent live-page replay proved q86 true in this scene. Reuse the
    exact native false epilogue and ABI, removing only the unrelated Orochi
    mission condition. No readiness, gauge or controller fields are written.
    """
    hook = pending_weapon_hook()
    source = hook['asm']
    mission = '''mov rax, qword ptr [r11+0x130]
mov rdx, {mission_temp_owner}
cmp qword ptr [rdx], rax
jne wp_original
mov rax, qword ptr [r11+0x120]
cmp byte ptr [rax], 7
jne wp_original
cmp dword ptr [rax+4], 1
jne wp_original
'''
    source = replace_exact(source, mission, '')
    source = replace_exact(source, '''test r9, r9
je wp_original
mov rax, qword ptr [r8+0x5D8]
''', '''test r9, r9
je wp_original
cmp dword ptr [r9], 0xC9AAF
jne wp_original
mov rax, qword ptr [r8+0x5D8]
''')
    source = replace_exact(source, '''mov rax, qword ptr [r11+0xA8]
cmp qword ptr [rax+0x50], r9
jne wp_original
''', '''mov rax, qword ptr [r9+0x230]
test rax, rax
je wp_original
cmp qword ptr [rax], r9
jne wp_original
mov rax, qword ptr [rax+8]
cmp rax, qword ptr [r11+0xA8]
jne wp_original
cmp qword ptr [rax+0x50], r9
jne wp_original
''')
    source = replace_exact(source, '''mov edx, dword ptr [r11+0x118]
cmp dword ptr [rax], edx
jne wp_original
''', '''cmp dword ptr [r11+0x118], 3174
jne wp_original
cmp dword ptr [rax], 3174
jne wp_original
'''+ready_owner_guard().replace('oh_', 'wp_')+'''test byte ptr [rax+0x19], 1
je wp_original
''')
    source = adapt_identifiers(source, (2,0,0,0))
    windup = '''cmp dword ptr [rax], 4026
jne wp_original
cmp byte ptr [rax+0x40], 1
jne wp_original
cmp qword ptr [rax+0x38], rdx
jne wp_original
'''
    source = replace_exact(source, windup, windup+'''mov rax, qword ptr [rax+0x20]
test rax, rax
je wp_original
cmp dword ptr [rax+0x20], 1210
jne wp_original
''')
    hook['asm'] = source
    hook['purpose'] = 'Native query86 false only for scene-owned Nine Tails 4026 windup, ready locked target, HP 1, active pair absent and pending pair absent or bound'
    return hook


def sources(installed, menu_guard):
    """Return eight unbound bodies derived from the proven private candidate.

    Runtime adds dynamic discovery and converts the two private address
    tokens. Namespace all labels so each dual body can retain the exact
    original Orochi assembly beside its Nine Tails branch.
    """
    if (installed.get('tool_version') != '1.0.0-beta.5.4.1'
            or len(installed.get('hooks', ())) != 81
            or installed.get('orochi_binding_data_offset') != 0x42000
            or installed.get('orochi_binding_data_size') != BIND_SIZE):
        raise ValueError('Exact installed Beta 5.4.1 source plan required')
    scene = frozen_candidate(installed, 0x140000000, 0x144000000, menu_guard)
    hooks = deepcopy(scene['hooks'][:7])
    heavy = hooks[0]
    # Preserve the final target's owned stats/HP check, remove only Orochi's
    # mission-local eight-head counter and its saved owner references.
    mission = '''mov rax, {mission_temp_owner}
mov rax, qword ptr [rax]
cmp rax, qword ptr [r11+0x130]
jne oh_original
mov rax, qword ptr [r11+0x120]
cmp byte ptr [rax], 7
jne oh_original
cmp dword ptr [rax+4], 1
jne oh_original
'''
    heavy['asm'] = replace_exact(heavy['asm'], mission, '')
    boundary = '''mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x640], r9
'''
    heavy['asm'] = replace_exact(heavy['asm'], boundary,
        '''mov r9, qword ptr [r11+0x18]
cmp dword ptr [r9], 0xC9AAF
jne oh_original
cmp qword ptr [r8+0x640], r9
''')
    ready = '''mov edx, dword ptr [r11+0x118]
cmp dword ptr [rax], edx
jne oh_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je oh_original
'''
    heavy['asm'] = replace_exact(heavy['asm'], ready,
        '''cmp dword ptr [r11+0x118], 3174
jne oh_original
cmp dword ptr [rax], 3174
jne oh_original
'''+ready_owner_guard())

    for index, (hook, counts, prefix) in enumerate(zip(hooks, COUNTS,
            ('oh', 'ob', 'om', 'op', 'oe', 'bp', 'br'))):
        hook['asm'] = adapt_identifiers(hook['asm'], counts)
        # V5 already verifies paired params/motion. Add the equally strict
        # windup key check after each owned windup record guard.
        boundary = f'''cmp dword ptr [rax], {WINDUP_ACTION}
jne {prefix}_original
cmp byte ptr [rax+0x40], 1
jne {prefix}_original
cmp qword ptr [rax+0x38], rdx
jne {prefix}_original
'''
        after = boundary+f'''mov rax, qword ptr [rax+0x20]
test rax, rax
je {prefix}_original
cmp dword ptr [rax+0x20], {WINDUP_MOTION}
jne {prefix}_original
'''
        hook['asm'] = replace_exact(hook['asm'], boundary, after, 2 if index == 4 else 1)
        previous = installed['hooks'][71+index]
        for field in ('rva', 'length', 'original'):
            if hook[field] != previous[field]:
                raise ValueError('Native resource hook differs: '+field)
        hook['purpose'] = ('Scene-pinned native Nine Tails execution read view; '
                           '4026/1210 -> 1273/1211; private binding only')
        if 'mission_temp_owner' in hook['asm']:
            raise ValueError('Nine Tails view retained Orochi mission dependency')
    pending = weapon_guard()
    previous = installed['hooks'][80]
    if any(pending[field] != previous[field] for field in
           ('rva','length','original','code_offset','code_capacity')):
        raise ValueError('Installed query86 hook differs')
    hooks.append(pending)
    targets = {}
    for name, rva in scene['targets'].items():
        if name in ('production_data', 'mission_temp_owner'):
            continue
        if name in installed['targets'] and installed['targets'][name] != rva:
            raise ValueError('Conflicting scene native target '+name)
        targets[name] = rva
    labels = re.compile(r'\b(?:oh|ob|om|op|oe|bp|br|wp)_[A-Za-z0-9_]+\b')
    for hook in hooks:
        hook['asm'] = labels.sub(lambda m:'np_'+m.group(0),hook['asm'])
        hook['asm'] = hook['asm'].replace('{data}','{ninetails_data}')
    return hooks, targets
