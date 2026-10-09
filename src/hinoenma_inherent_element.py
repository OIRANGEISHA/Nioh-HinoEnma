"""Private, uninstalled weapon-innate element candidate for Hotfix 1.

Read the selected *player* preview row before the existing Boss restoration,
and cache only its permanent element/power. All Boss rows, equipment effects,
attack deltas and animation descriptors remain untouched. The cache lives on
a separate new allocation page; CACHE_PREFIX can be mapped to independent
trial data without changing the production data pointer.

Completed ordinary body/owned projectile contexts, and the independently
built successful-drain stack context, can use the selected permanent pair
when their original element is unset. Native temporary enchant has priority.
Ordinary body descriptors with native type 6 can receive the same primary
element override as a native temporary enchant; this does not add a separate
body paralysis channel. Roar children, intrinsic dive 9, descriptor bit 43,
needle's independent attributes, physics and healing are preserved.
This module contains no process access and does not install anything.
"""
from copy import deepcopy

from hinoenma_grab_elements import coefficient_asm as native_coefficient_asm
from hinoenma_tutorial import player_guard

BASE_VERSION = '1.0.0-beta.5.1.hotfix.1'
VERSION = BASE_VERSION + '.inherent.2'
DATA_OFFSET = 0xF000
CACHE_OFFSET = 0x1F000
CACHE_DELTA = CACHE_OFFSET - DATA_OFFSET
CACHE_SIZE = 0x40
CACHE_PREFIX = 'mov r9, {data}\nadd r9, 0x10000\n'
ALLOCATION_SIZE = 0x20000
PROTECTED_DATA_PAGES = ((0xF000, 0x10000), (0x13000, 0x14000),
                        (0x1F000, 0x20000))

CACHE_FIELDS = dict(sequence=0x00, element=0x08, power=0x0C,
                    actor=0x10, component=0x18, epoch=0x20,
                    weapon_id=0x24, selected_slot=0x28, recalc=0x2C)

# Four existing hooks relocate to unused new slots; every other entry retains
# its original slot and exact source. No existing code/data slot is reused.
HOOK_LAYOUT = {
    'HE_AttributeOverlay': (0x1B000, 0x1000),
    'HE_ProjectileElementInheritance': (0x1C000, 0x1000),
    'HE_GrabElementDamage': (0x1D000, 0x800),
    'HE_GrabElementAccumulation': (0x1D800, 0x800),
    'HE_InherentDirectElement': (0x1E000, 0x1000),
}
HOOK_NAMES = tuple(HOOK_LAYOUT)
DIRECT_RVA = 0x717F06
DIRECT_ORIGINAL = '0F 10 4C 24 30 0F 11 4D 88'
DIRECT_LENGTH = 9
DIRECT_DESCRIPTOR_LOCAL_OFFSET = 0x70
DIRECT_DESCRIPTOR_SAVED_OFFSET = 0xB0  # SAVE pushes 8 qwords (0x40).
EXPECTED_EXISTING = {
    'HE_AttributeOverlay': (0x7C82DB, 5, 0x3C00, 0xC00),
    'HE_ProjectileElementInheritance': (0x7E2959, 8, 0x500, 0x300),
    'HE_GrabElementDamage': (0x727874, 8, 0x900, 0x300),
    'HE_GrabElementAccumulation': (0x727936, 8, 0xD00, 0x300),
}

SAVE = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
'''
RESTORE = '''pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {return}
'''


def capture_cache_asm():
    """r11 core data, r12 native equipped preview, rsi component, r14 actor.

    Existing overlay has committed 8C/98/9C using its C64 sole-slot fallback.
    The preview is about to be restored; only this separate cache is written.
    CAS gives one writer ownership; the sequence provides a coherent read if
    recalculation overlaps a hit. A busy writer causes this capture to skip.
    """
    return CACHE_PREFIX + '''mov eax, dword ptr [r9]
test al, 1
jne innate_capture_skipped
lea edx, [rax+1]
lock cmpxchg dword ptr [r9], edx
jne innate_capture_skipped
mov dword ptr [r9+0x08], -1
mov dword ptr [r9+0x0C], 0
mov qword ptr [r9+0x10], r14
mov qword ptr [r9+0x18], rsi
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r9+0x20], eax
mov eax, dword ptr [r11+0x98]
mov dword ptr [r9+0x24], eax
mov ecx, dword ptr [r11+0x8C]
mov dword ptr [r9+0x28], ecx
mov eax, dword ptr [r11+0x9C]
mov dword ptr [r9+0x2C], eax
cmp ecx, 1
ja innate_capture_commit
cmp dword ptr [r9+0x24], -1
je innate_capture_commit
imul ecx, ecx, 0x28
mov edx, dword ptr [r12+rcx+0x1C]
cmp edx, 4
ja innate_capture_commit
mov eax, dword ptr [r12+rcx+0x20]
test eax, eax
jle innate_capture_commit
mov dword ptr [r9+0x08], edx
mov dword ptr [r9+0x0C], eax
innate_capture_commit:
lock inc dword ptr [r9]
innate_capture_skipped:
'''


def resolve_element_asm(label):
    """Return EDX element/EAX power; R10 actor/R11 core data already guarded.

    RAX, RCX, RDX, R8 and R9 are scratch. A live valid temporary pair wins;
    only exactly-unset temporary type permits permanent fallback. Other
    invalid temporary values fail closed. Exit to LABEL_done on rejection.
    """
    if not label.replace('_', '').isalnum():
        raise ValueError('Assembly label must be alphanumeric/underscore')
    source = '''mov rax, qword ptr [r10+0x240]
test rax, rax
je LABEL_done
cmp r10, qword ptr [rax]
jne LABEL_done
cmp r10, qword ptr [rax+0x108]
jne LABEL_done
cmp qword ptr [rax+0xB98], 0
jne LABEL_done
cmp qword ptr [rax+0x20], 0
jle LABEL_done
mov edx, dword ptr [rax+0x1118]
cmp edx, 4
ja LABEL_permanent
mov ecx, dword ptr [rax+0x111C]
test ecx, ecx
jle LABEL_done
mov eax, ecx
jmp LABEL_pair_ready
LABEL_permanent:
cmp edx, -1
jne LABEL_done
''' + CACHE_PREFIX + '''mov r8d, dword ptr [r9]
test r8b, 1
jne LABEL_done
cmp r10, qword ptr [r9+0x10]
jne LABEL_done
cmp rax, qword ptr [r9+0x18]
jne LABEL_done
mov ecx, dword ptr [r11+0x1C]
cmp ecx, dword ptr [r9+0x20]
jne LABEL_done
mov ecx, dword ptr [r11+0x98]
cmp ecx, dword ptr [r9+0x24]
jne LABEL_done
cmp ecx, -1
je LABEL_done
mov ecx, dword ptr [r11+0x8C]
cmp ecx, 1
ja LABEL_done
cmp ecx, dword ptr [r9+0x28]
jne LABEL_done
mov ecx, dword ptr [r11+0x9C]
cmp ecx, dword ptr [r9+0x2C]
jne LABEL_done
mov edx, dword ptr [r9+0x08]
cmp edx, 4
ja LABEL_done
mov eax, dword ptr [r9+0x0C]
test eax, eax
jle LABEL_done
cmp r8d, dword ptr [r9]
jne LABEL_done
LABEL_pair_ready:
'''
    return source.replace('LABEL', label)


def _player_guard(label):
    return player_guard(label) + '''cmp word ptr [r10+0x04], 0
jne LABEL_done
mov eax, dword ptr [r10]
cmp eax, dword ptr [r11+0x04]
jne LABEL_done
'''.replace('LABEL', label)


def context_asm():
    """7E2959: RDI context, R12 descriptor, R15 source actor, RBP locals."""
    return '''movups xmm1, xmmword ptr [rbp+0x07]
movups xmmword ptr [rdi+0x18], xmm1
''' + SAVE + '''mov r11, {data}
''' + _player_guard('innate_context') + '''test r15, r15
je innate_context_done
cmp r15, r10
je innate_context_source_ready
cmp word ptr [r15+0x04], 4
jne innate_context_done
cmp r10, qword ptr [r15+0x200]
jne innate_context_done
mov eax, dword ptr [r15]
cmp eax, 0x11F85
je innate_context_source_ready
cmp eax, 0xADD70
jne innate_context_done
innate_context_source_ready:
cmp r15, qword ptr [rdi+0x28]
jne innate_context_done
cmp dword ptr [rdi+0x18], -1
jne innate_context_done
test r12, r12
je innate_context_done
cmp r12, qword ptr [rdi]
jne innate_context_done
cmp byte ptr [r12+0x20], 0xFF
je innate_context_descriptor_ready
cmp r15, r10
jne innate_context_done
cmp byte ptr [r12+0x20], 6
jne innate_context_done
cmp byte ptr [r12+0x1D], 0
je innate_context_done
movzx eax, byte ptr [r12+0x4F]
cmp eax, 42
je innate_context_descriptor_ready
cmp eax, 44
je innate_context_descriptor_ready
cmp eax, 45
jne innate_context_done
innate_context_descriptor_ready:
bt qword ptr [r12], 43
jc innate_context_done
''' + resolve_element_asm('innate_context') + '''mov dword ptr [rdi+0x18], edx
mov dword ptr [rdi+0x1C], eax
innate_context_done:
''' + RESTORE


def direct_asm():
    """717F06: RDI current actor, RSI controller; descriptor at [RSP+70].

    Native 717E98 saves the descriptor at RSP+70. 717EB6 then overwrites RBX
    with the source actor, and 717ECF clears R12; neither is a descriptor at
    this site. SAVE's 0x40-byte pushes shift that verified local to RSP+B0.

    Replay both native SSE operations unchanged. Element/power live in the
    copied 16-byte destination [RBP-78]; its other eight bytes and XMM1 remain
    native. A successful 857/1101 drain must own the exact active four-entry
    descriptor array, current paired target and controller. No native calls.
    """
    return '''movups xmm1, xmmword ptr [rsp+0x30]
movups xmmword ptr [rbp-0x78], xmm1
''' + SAVE + '''mov r11, {data}
''' + _player_guard('innate_direct') + '''cmp rdi, r10
jne innate_direct_done
cmp dword ptr [rbp-0x78], -1
jne innate_direct_done
mov r8, qword ptr [rsp+0xB0]
test r8, r8
je innate_direct_done
cmp byte ptr [r8+0x20], 0xFF
jne innate_direct_done
test word ptr [r8+0x44], 0x2000
je innate_direct_done
bt qword ptr [r8], 43
jc innate_direct_done
''' + resolve_element_asm('innate_direct') + '''mov r8, qword ptr [rsp+0xB0]
push rax
push rdx
mov rax, qword ptr [r10+0x230]
test rax, rax
je innate_direct_pair_reject
cmp r10, qword ptr [rax]
jne innate_direct_pair_reject
cmp rsi, qword ptr [rax+0x08]
jne innate_direct_pair_reject
cmp r10, qword ptr [rsi+0x50]
jne innate_direct_pair_reject
cmp qword ptr [rsi+0x5B0], 0
je innate_direct_pair_reject
cmp r14, qword ptr [rsi+0x5B0]
jne innate_direct_pair_reject
mov rdx, qword ptr [rsi+0x58]
test rdx, rdx
je innate_direct_pair_reject
cmp dword ptr [rdx], 857
jne innate_direct_pair_reject
cmp byte ptr [rdx+0x40], 1
jne innate_direct_pair_reject
mov rax, qword ptr [rdx+0x20]
test rax, rax
je innate_direct_pair_reject
cmp dword ptr [rax+0x20], 1101
jne innate_direct_pair_reject
cmp word ptr [rdx+0x52], 4
jne innate_direct_pair_reject
movzx ecx, word ptr [rdx+0x50]
cmp ecx, 4096
ja innate_direct_pair_reject
mov rdx, qword ptr [rdx+0x48]
test rdx, rdx
je innate_direct_pair_reject
lea rdx, [rdx+rcx*8]
cmp r8, qword ptr [rdx]
je innate_direct_pair_accept
cmp r8, qword ptr [rdx+0x08]
je innate_direct_pair_accept
cmp r8, qword ptr [rdx+0x10]
je innate_direct_pair_accept
cmp r8, qword ptr [rdx+0x18]
jne innate_direct_pair_reject
innate_direct_pair_accept:
pop rdx
pop rax
mov dword ptr [rbp-0x78], edx
mov dword ptr [rbp-0x74], eax
jmp innate_direct_done
innate_direct_pair_reject:
pop rdx
pop rax
innate_direct_done:
''' + RESTORE


def coefficient_asm(xmm):
    """Extend the exact existing drain coefficient guard's source-pair match."""
    source = native_coefficient_asm(xmm)
    guarded = player_guard('grab_element')
    if source.count(guarded) != 1:
        raise ValueError('Native drain player guard changed')
    source = source.replace(guarded, _player_guard('grab_element'))
    old = '''mov edx, dword ptr [r15+0x18]
cmp edx, 4
ja grab_element_done
cmp edx, dword ptr [rax+0x1118]
jne grab_element_done
mov edx, dword ptr [r15+0x1C]
test edx, edx
jle grab_element_done
cmp edx, dword ptr [rax+0x111C]
jne grab_element_done
'''
    if source.count(old) != 1:
        raise ValueError('Native drain source-pair guard changed')
    source = source.replace(old, resolve_element_asm('grab_element') + '''cmp edx, dword ptr [r15+0x18]
jne grab_element_done
cmp eax, dword ptr [r15+0x1C]
jne grab_element_done
''')
    source = source.replace('push r10\npush r11\n', 'push r8\npush r9\npush r10\npush r11\n')
    source = source.replace('pop r11\npop r10\npop rdx\n',
                            'pop r11\npop r10\npop r9\npop r8\npop rdx\n')
    intrinsic = 'test word ptr [rax+0x44], 0x2000\n'
    if source.count(intrinsic) != 1:
        raise ValueError('Native drain descriptor guard changed')
    source = source.replace(intrinsic, '''cmp byte ptr [rax+0x20], 0xFF
jne grab_element_done
''' + intrinsic)
    return source


def apply_inherent_elements(previous):
    """Return a pure independent, uninstalled Hotfix59-derived candidate."""
    if (previous.get('tool_version') != BASE_VERSION
            or len(previous.get('hooks', ())) != 59
            or previous.get('data_offset') != DATA_OFFSET
            or previous.get('allocation_size') != 0x1B000):
        raise ValueError('Exact complete Hotfix 1 baseline59 required')
    plan = deepcopy(previous)
    hooks = {hook['name']: hook for hook in plan['hooks']}
    if len(hooks) != 59 or set(HOOK_NAMES[:-1]) - set(hooks):
        raise ValueError('Unique original59 hooks required')
    for name, (rva, length, offset, capacity) in EXPECTED_EXISTING.items():
        hook = hooks[name]
        if (hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity')) != (rva, length, offset, capacity):
            raise ValueError('Existing Hotfix hook layout changed: ' + name)
    insertion = 'inc dword ptr [r11+0x9C]\nmov edx, 8\nattr_restore_boss_weapon:'
    overlay = hooks['HE_AttributeOverlay']
    if overlay['asm'].count(insertion) != 1:
        raise ValueError('Selected native preview capture position changed')
    overlay['asm'] = overlay['asm'].replace(insertion,
        'inc dword ptr [r11+0x9C]\n' + capture_cache_asm()
        + 'mov edx, 8\nattr_restore_boss_weapon:')
    overlay['purpose'] += '; cache only selected native permanent element before unchanged Boss-row restoration'
    context = hooks['HE_ProjectileElementInheritance']
    if context['original'] != '0F 10 4D 07 0F 11 4F 18':
        raise ValueError('Completed attack context native signature changed')
    context['asm'] = context_asm()
    context['purpose'] = ('Current Hino body and exact owned child unset contexts use '
        'temporary enchant first, then selected native innate element; ordinary body type 6 '
        'follows native primary enchant priority, protected projectile channels retained')
    for name, xmm, original in (
            ('HE_GrabElementDamage', 'xmm1', '0F B6 48 1D 66 0F 6E C9'),
            ('HE_GrabElementAccumulation', 'xmm2', '0F B6 48 1D 66 0F 6E D1')):
        if hooks[name]['original'] != original:
            raise ValueError('Exact native drain coefficient site changed')
        hooks[name]['asm'] = coefficient_asm(xmm)
        hooks[name]['purpose'] += '; exact matching selected innate pair accepted when temporary element is unset'
    plan['hooks'].append(dict(name=HOOK_NAMES[-1], rva=DIRECT_RVA,
        length=DIRECT_LENGTH, original=DIRECT_ORIGINAL,
        purpose='Only current successful Hino drain857/1101 unset stack-context pair receives native element source',
        asm=direct_asm()))
    for hook in plan['hooks']:
        if hook['name'] in HOOK_LAYOUT:
            hook['code_offset'], hook['code_capacity'] = HOOK_LAYOUT[hook['name']]
    code_spans = sorted((h['code_offset'], h['code_offset'] + h.get('code_capacity', 0x400))
                        for h in plan['hooks'])
    site_spans = sorted((h['rva'], h['rva'] + h['length']) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(code_spans, code_spans[1:])):
        raise ValueError('Candidate code capacities overlap')
    if any(a[1] > b[0] for a, b in zip(site_spans, site_spans[1:])):
        raise ValueError('Candidate native hook sites overlap')
    for low, high in code_spans:
        if low < 0 or high > CACHE_OFFSET or any(
                low < last and high > first for first, last in PROTECTED_DATA_PAGES):
            raise ValueError('Candidate code overlaps protected data page')
    plan.update(tool_version=VERSION, allocation_size=ALLOCATION_SIZE,
        inherent_element_revision=2, inherent_element_cache_offset=CACHE_OFFSET,
        inherent_element_cache_size=CACHE_SIZE,
        inherent_element_cache_fields=CACHE_FIELDS.copy(),
        inherent_element_modified_hooks=list(HOOK_NAMES),
        inherent_element_projectile_intrinsic_channels_preserved=True,
        inherent_element_body_native_enchant_priority=True,
        inherent_element_body_type6_attributes=[42, 44, 45],
        inherent_element_body_type6_requires_damage_coefficient=True,
        inherent_element_temporary_priority=True,
        stage='private_inherent_element_candidate_pending_cpu_and_gameplay')
    return plan
