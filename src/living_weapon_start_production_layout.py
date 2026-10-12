"""Pure, explicitly versioned layout for a standalone LW restart trial.

This module does not load profiles, game files, process APIs or assemblers.
It accepts only the exact published Beta5.6 geometry after R4 input/views,
and makes one bounded code-slot migration. It provides no resource bootstrap
and cannot be used as a replacement validator for the legacy 0x55000 layout.
"""
from copy import deepcopy
import hashlib
import json

BASE_VERSION = '1.0.0-beta.5.6'
VERSION = '1.0.0-beta.5.6.2'
LAYOUT_REVISION = 1
ALLOCATION_SIZE = 0x69000
INPUT_CODE_OFFSET = 0x61000
INPUT_CODE_CAPACITY = 0x8000
STAGING_OFFSET = 0x55000
STAGING_SIZE = 0xC000
BINDING_OFFSET = 0x44200
BINDING_SIZE = 0x200
NEW_DATA_PAGES = tuple((at, at + 0x1000)
                       for at in range(STAGING_OFFSET, INPUT_CODE_OFFSET, 0x1000))
BASE_GEOMETRY_SHA256 = 'e81b7310209143ddba97ba3eae64f1de0a07d2e3fb99f1bea09ec380340f129c'
GEOMETRY_KEYS = ('tool_version', 'allocation_size', 'data_offset',
                 'protected_data_pages', 'disk_sha256', 'image_size', 'pe_timestamp_hex')
HOOK_GEOMETRY_KEYS = ('name', 'rva', 'length', 'original',
                      'code_offset', 'code_capacity')


def _geometry_digest(plan):
    shape = {key: plan[key] for key in GEOMETRY_KEYS}
    shape['hooks'] = [{key: hook[key] for key in HOOK_GEOMETRY_KEYS}
                      for hook in plan['hooks']]
    raw = json.dumps(shape, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def _baseline_geometry(plan):
    if _geometry_digest(plan) != BASE_GEOMETRY_SHA256:
        raise ValueError('Exact published Beta5.6 82-site / 0x55000 geometry required')


def apply_production_layout(previous):
    """Migrate only h36; leave all old data pages and fixed helpers in place."""
    _baseline_geometry(previous)
    if (previous.get('living_weapon_start_trial_revision') != 4
            or previous.get('living_weapon_start_views_revision') != 3
            or previous.get('living_weapon_start_binding_offset') != BINDING_OFFSET
            or previous.get('living_weapon_start_binding_size') != BINDING_SIZE
            or previous.get('living_weapon_start_production_layout_revision')):
        raise ValueError('Unmigrated R4 input and exact startup views required')
    plan = deepcopy(previous)
    plan['hooks'][36].update(code_offset=INPUT_CODE_OFFSET,
                            code_capacity=INPUT_CODE_CAPACITY)
    plan['protected_data_pages'] += [list(pair) for pair in NEW_DATA_PAGES]
    plan.update(tool_version=VERSION, allocation_size=ALLOCATION_SIZE,
        living_weapon_start_production_layout_revision=LAYOUT_REVISION,
        living_weapon_start_input_code_offset=INPUT_CODE_OFFSET,
        living_weapon_start_input_code_capacity=INPUT_CODE_CAPACITY,
        living_weapon_start_staging_offset=STAGING_OFFSET,
        living_weapon_start_staging_size=STAGING_SIZE,
        living_weapon_start_native_jump_changed_indices=[36],
        local_package_only=True, stage='local_beta56_living_weapon_restart_trial')
    validate_production_layout(plan)
    return plan


def validate_production_layout(plan):
    """Validate only this explicit new version, never relax a legacy layout."""
    if (plan.get('tool_version') != VERSION
            or plan.get('living_weapon_start_production_layout_revision') != LAYOUT_REVISION
            or plan.get('allocation_size') != ALLOCATION_SIZE
            or plan.get('data_offset') != 0xF000
            or len(plan.get('hooks', ())) != 82
            or plan.get('local_package_only') is not True
            or plan.get('living_weapon_start_input_code_offset') != INPUT_CODE_OFFSET
            or plan.get('living_weapon_start_input_code_capacity') != INPUT_CODE_CAPACITY
            or plan.get('living_weapon_start_staging_offset') != STAGING_OFFSET
            or plan.get('living_weapon_start_staging_size') != STAGING_SIZE
            or plan.get('living_weapon_start_binding_offset') != BINDING_OFFSET
            or plan.get('living_weapon_start_binding_size') != BINDING_SIZE
            or plan.get('living_weapon_start_native_jump_changed_indices') != [36]):
        raise ValueError('Exact standalone LW production layout required')
    pages = plan['protected_data_pages']
    if len(pages) != 23 or pages[-12:] != [list(pair) for pair in NEW_DATA_PAGES]:
        raise ValueError('Twelve exact new staging RW pages required')
    old_shape = deepcopy(plan)
    old_shape.update(tool_version=BASE_VERSION, allocation_size=0x55000,
                     protected_data_pages=old_shape['protected_data_pages'][:-12])
    old_shape['hooks'][36].update(code_offset=0xD000, code_capacity=0x1000)
    _baseline_geometry(old_shape)
    if (plan['hooks'][36]['code_offset'], plan['hooks'][36]['code_capacity']) != (
            INPUT_CODE_OFFSET, INPUT_CODE_CAPACITY):
        raise ValueError('Only the exact h36 code migration is permitted')
    code = sorted((hook['code_offset'], hook['code_offset'] + hook['code_capacity'])
                  for hook in plan['hooks'])
    entries = sorted((hook['rva'], hook['rva'] + hook['length'])
                     for hook in plan['hooks'])
    if (code[0][0] < 0 or code[-1][1] != ALLOCATION_SIZE
            or any(a[1] > b[0] for a, b in zip(code, code[1:]))
            or any(a[1] > b[0] for a, b in zip(entries, entries[1:]))
            or any(max(first & ~0xFFF, start) < min((last + 0xFFF) & ~0xFFF, end)
                   for first, last in code for start, end in pages)):
        raise ValueError('LW code capacities, writable pages or native entries overlap')
    return None
