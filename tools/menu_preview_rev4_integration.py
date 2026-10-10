"""Pure, unpublished integration of eight scoped map-display hooks.

The input is the frozen Beta 5.2 plan; this module never opens a process,
changes a file, builds an executable, or updates a published profile.
All private addresses use the existing core-data relocation plus a constant.
"""
from __future__ import annotations

from copy import deepcopy
import re

from build_hinoenma import assemble
from menu_preview_visual_hooks import (
    HOOKS, TARGET_RVAS, MAX_WAIT_FRAMES, WRAPPER_FRAME_SIZE,
    ready_asm, spawn_asm, ctor_asm, restore_asm,
)
from menu_preview_appearance_rev4_hooks import (
    HOOKS as APPEARANCE_HOOKS, TARGET_RVAS as APPEARANCE_TARGET_RVAS,
    appearance_asm, OWN_DATA_SIZE, CONSTRUCTION_SUPPRESSED_OFFSET,
)
from menu_preview_appearance_rev2_hooks import idle_asm, idle_selection_asm, loadout_appearance_asm
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

BASE_VERSION = '1.0.0-beta.5.2'
VERSION = BASE_VERSION + '.menu-preview-private.4'
CORE_DATA_OFFSET = 0xF000
CODE_OFFSET = 0x20000
SCRATCH_OFFSET = 0x24000
APPEARANCE_CODE_OFFSET = 0x25000
APPEARANCE_SCRATCH_OFFSET = 0x29000
ALLOCATION_SIZE = 0x2A000
SCRATCH_DELTA = SCRATCH_OFFSET - CORE_DATA_OFFSET
APPEARANCE_SCRATCH_DELTA = APPEARANCE_SCRATCH_OFFSET - CORE_DATA_OFFSET
PROTECTED_DATA_PAGES = ((0xF000, 0x10000), (0x13000, 0x14000),
                        (0x1F000, 0x20000), (0x24000, 0x25000),
                        (0x29000, 0x2A000))
CANONICAL_MODULE, CANONICAL_ALLOCATION = 0x140000000, 0x144000000
SPAWN_HOOK_NAME = HOOKS[1][0]
EXPECTED_VISUAL_HOOKS = (
    ('HE_MapVisualReadyPrivate', 0x8C536F, '8B 46 1C 45 33 E4', 0),
    ('HE_MapVisualSpawnPrivate', 0x8C5407, 'E8 54 FD E8 FF', 0x1000),
    ('HE_MapVisualResourcePrivate', 0x7604E7, '48 85 C0 0F 84 50 03 00 00', 0x2000),
    ('HE_MapVisualRestorePrivate', 0x760778, '49 8B 85 C0 00 00 00', 0x3000),
)
EXPECTED_APPEARANCE_HOOKS = (
    ('HE_MapAppearancePrivate', 0x7C8302, 'E8 69 88 FE FF', 0),
    ('HE_MapNativeIdlePrivate', 0x9530BA, '48 8B 47 20 48 89 43 28', 0x1000),
    ('HE_MapIdleSelectionPrivate', 0x70ED46, '8B 56 68 8B CA', 0x2000),
    ('HE_MapLoadoutAppearancePrivate', 0x75724F, 'E8 1C 99 05 00', 0x3000),
)
POINTER_LOAD = re.compile(
    r'(?m)^mov (r(?:ax|cx|dx|[89]|1[01])), '
    r'\{(data|production_data|visual_data|wrapper_continuation)\}$')
PRIVATE_POINTER = re.compile(r'\{(data|production_data|visual_data|wrapper_continuation)\}')
SOURCE_NUMBER = re.compile(r'(?<![\w{}])(?:0x[0-9A-Fa-f]+|[0-9]+)(?![\w{}])')


def _validate_sources() -> None:
    if tuple(HOOKS) != EXPECTED_VISUAL_HOOKS or tuple(APPEARANCE_HOOKS) != EXPECTED_APPEARANCE_HOOKS:
        raise ValueError('Exactly four visual and four appearance source entries required')


def wrapper_continuation_offset(plan: dict, module_base: int, allocation: int) -> int:
    """Resolve the unique native spawner call, not a guessed source length."""
    wrappers = [hook for hook in plan['hooks'] if hook['name'] == SPAWN_HOOK_NAME]
    if len(wrappers) != 1:
        raise ValueError('Exactly one scoped map-spawner wrapper required')
    wrapper = assemble(dict(plan, hooks=wrappers), module_base, allocation)[0]
    calls = [ins for ins in Cs(CS_ARCH_X86, CS_MODE_64).disasm(
        wrapper['payload'], wrapper['target'])
        if ins.mnemonic == 'call' and int(ins.op_str, 16) == module_base + TARGET_RVAS['spawn']]
    if len(calls) != 1 or calls[0].size != 5:
        raise ValueError('Exactly one direct native spawner call required')
    offset = calls[0].address + calls[0].size - allocation
    if not wrapper['code_offset'] <= offset < wrapper['code_offset'] + wrapper['code_capacity']:
        raise ValueError('Wrapper continuation escaped its code slot')
    return offset


def _bind_core_data(source: str, *, scratch_delta: int) -> str:
    """Translate each original pointer load once, using only fixup kind0.

    The new ADD occurs inside each source's saved-register/flags guard. A
    one-pass replacement is essential: inserted core-data loads must never
    be mistaken for a second standalone scratch pointer.
    """
    matches = list(POINTER_LOAD.finditer(source))
    if len(matches) != len(PRIVATE_POINTER.findall(source)):
        raise ValueError('Standalone private-pointer load syntax changed')
    deltas = dict(data=hex(scratch_delta), production_data=None,
                  visual_data=hex(SCRATCH_DELTA),
                  wrapper_continuation='{menu_continuation_delta}')

    def bind(match):
        register, token = match.groups()
        result = f'mov {register}, {{data}}'
        if deltas[token] is not None:
            result += f'\nadd {register}, {deltas[token]}'
        return result

    return POINTER_LOAD.sub(bind, source)


def _integrated_sources(continuation_delta: int | None = None) -> tuple[str, ...]:
    visual = (ready_asm(), spawn_asm(), ctor_asm(), restore_asm())
    appearance = (appearance_asm(), idle_asm(), idle_selection_asm(), loadout_appearance_asm())
    sources = tuple(_bind_core_data(source, scratch_delta=delta)
                    for group, delta in ((visual, SCRATCH_DELTA),
                                         (appearance, APPEARANCE_SCRATCH_DELTA))
                    for source in group)
    if continuation_delta is not None:
        sources = tuple(source.replace('{menu_continuation_delta}', hex(continuation_delta))
                        for source in sources)
    return sources


def ct_compatible_plan(plan: dict) -> dict:
    """Make instruction literals unambiguous for the existing CT emitter.

    Keystone source uses decimal bare integers, whereas AutoAssembler uses
    hexadecimal bare integers. The public renderer strips the 0x prefix, so
    express every numeric instruction operand in hex first. Literal byte
    rows stay decimal for its existing .byte-to-db conversion. Names and
    placeholders, including numeric label suffixes, are not operands.
    """
    validate_layout(plan)
    result = deepcopy(plan)
    for hook in result['hooks']:
        hook['asm'] = '\n'.join(
            line if line.lstrip().startswith('.byte ') else
            SOURCE_NUMBER.sub(lambda m: hex(int(m.group(0), 16 if m.group(0).lower().startswith('0x') else 10)), line)
            for line in hook['asm'].split('\n'))
    return result


def validate_layout(plan: dict) -> None:
    _validate_sources()
    if (plan.get('data_offset') != CORE_DATA_OFFSET or
            plan.get('allocation_size') != ALLOCATION_SIZE or
            plan.get('menu_visual_scratch_offset') != SCRATCH_OFFSET or
            plan.get('menu_appearance_scratch_offset') != APPEARANCE_SCRATCH_OFFSET or
            plan.get('menu_appearance_scratch_size') != OWN_DATA_SIZE or
            plan.get('menu_appearance_revision') != 4 or
            plan.get('menu_renderer_validation_pending') is not True or
            plan.get('menu_framing_validation_pending') is not True or
            len(plan.get('hooks', ())) != 68 or
            plan.get('menu_visual_scope') != 'BaseMode state0, local map placeholder100/0/1 only' or
            tuple(map(tuple, plan.get('protected_data_pages', ()))) != PROTECTED_DATA_PAGES):
        raise ValueError('Unpublished integrated code/data layout differs')
    names, sites, spans = set(), [], []
    for hook in plan['hooks']:
        if hook['name'] in names:
            raise ValueError('Duplicate hook name')
        names.add(hook['name'])
        length = len(bytes.fromhex(hook['original']))
        if length != hook['length'] or length < 5:
            raise ValueError('Invalid native overwrite shape')
        capacity = hook.get('code_capacity', 0x400)
        low, high = hook['code_offset'], hook['code_offset'] + capacity
        if low < 0 or high > ALLOCATION_SIZE or capacity <= 0 or any(
                max(low, start) < min(high, end) for start, end in PROTECTED_DATA_PAGES):
            raise ValueError('Code overlaps protected data or allocation boundary')
        spans.append((low, high))
        sites.append((hook['rva'], hook['rva'] + length))
    for ranges in (spans, sites):
        ranges.sort()
        if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
            raise ValueError('Overlapping code capacity or native sites')
    menu = plan['hooks'][-8:]
    expected = [(name, rva, original, base + offset, 0x1000)
                for group, base in ((HOOKS, CODE_OFFSET),
                                    (APPEARANCE_HOOKS, APPEARANCE_CODE_OFFSET))
                for name, rva, original, offset in group]
    if [(h['name'], h['rva'], h['original'], h['code_offset'], h['code_capacity'])
            for h in menu] != expected:
        raise ValueError('Exact eight stabilized menu entries required')
    continuation = wrapper_continuation_offset(plan, CANONICAL_MODULE, CANONICAL_ALLOCATION)
    delta = continuation - CORE_DATA_OFFSET
    if (plan.get('menu_visual_wrapper_continuation_offset') != continuation or
            plan.get('menu_visual_core_relative_continuation_delta') != delta or
            tuple(h['asm'] for h in menu) != _integrated_sources(delta)):
        raise ValueError('Scoped source or transformed wrapper continuation differs')


def apply_menu_preview(previous: dict) -> dict:
    """Append a selected-Hino-only display feature; native William stays logical owner."""
    if (previous.get('tool_version') != BASE_VERSION or len(previous.get('hooks', ())) != 60 or
            previous.get('data_offset') != CORE_DATA_OFFSET or
            previous.get('allocation_size') != CODE_OFFSET or
            previous.get('inherent_element_revision') != 2):
        raise ValueError('Exact frozen 60-hook Beta 5.2 input required')
    _validate_sources()
    plan = deepcopy(previous)
    for name, rva in tuple(TARGET_RVAS.items()) + tuple(APPEARANCE_TARGET_RVAS.items()):
        if name in plan['targets'] and plan['targets'][name] != rva:
            raise ValueError('Conflicting native target: ' + name)
        plan['targets'][name] = rva
    sources = _integrated_sources()
    additions = [dict(name=name, rva=rva, original=original,
        length=len(bytes.fromhex(original)), code_offset=base + offset,
        code_capacity=0x1000, asm=sources[index],
        purpose='Unpublished scoped map display visual/gear/native-idle integration')
        for index, (base, (name, rva, original, offset)) in enumerate(
            [(base, hook) for group, base in ((HOOKS, CODE_OFFSET),
                (APPEARANCE_HOOKS, APPEARANCE_CODE_OFFSET)) for hook in group])]
    plan['hooks'].extend(additions)
    continuation = wrapper_continuation_offset(plan, CANONICAL_MODULE, CANONICAL_ALLOCATION)
    delta = continuation - CORE_DATA_OFFSET
    if delta <= 0 or delta >= ALLOCATION_SIZE:
        raise ValueError('Invalid core-relative wrapper continuation')
    for hook in additions:
        hook['asm'] = hook['asm'].replace('{menu_continuation_delta}', hex(delta))
    plan.update(tool_version=VERSION, allocation_size=ALLOCATION_SIZE,
        protected_data_pages=[list(page) for page in PROTECTED_DATA_PAGES],
        menu_visual_revision=1, menu_visual_base_version=BASE_VERSION,
        menu_visual_scratch_offset=SCRATCH_OFFSET, menu_visual_scratch_size=0x3C,
        menu_appearance_revision=4,
        menu_appearance_scratch_offset=APPEARANCE_SCRATCH_OFFSET,
        menu_appearance_scratch_size=OWN_DATA_SIZE,
        menu_appearance_constructor_suppressed_offset=CONSTRUCTION_SUPPRESSED_OFFSET,
        menu_appearance_scope='Exact phase3 native map constructor plus completed selected-Hino map body; persistent native idle and both visual gear binders',
        menu_renderer_validation_pending=True,
        menu_framing_validation_pending=True,
        menu_appearance_native_equipment_preserved=True,
        menu_appearance_native_stats_preserved=True,
        menu_visual_wrapper_continuation_offset=continuation,
        menu_visual_core_relative_continuation_delta=delta,
        menu_visual_max_wait_frames=MAX_WAIT_FRAMES,
        menu_visual_wrapper_frame_size=WRAPPER_FRAME_SIZE,
        menu_visual_selector_offset=0, menu_visual_william_selection=0,
        menu_visual_scope='BaseMode state0, local map placeholder100/0/1 only',
        menu_visual_native_actor_identity_preserved=True,
        menu_visual_native_flags_preserved=True,
        menu_visual_native_cpose_preserved=True,
        menu_visual_existing_fixup_kinds_only=True,
        stage='unpublished_menu_preview_rev4_integration')
    if plan['hooks'][:60] != previous['hooks']:
        raise ValueError('Existing Beta 5.2 hooks changed')
    validate_layout(plan)
    return plan
