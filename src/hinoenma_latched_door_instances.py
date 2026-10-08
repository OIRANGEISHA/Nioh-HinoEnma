"""Use native object kind for wooden latches instead of player instance one.

The observed Shigisan latch is object15/kind2/instance100, with the same
request16, owned common170/157, descriptors0/75 and motion223 as instance1.
Native751318 and709398 compare the WORD kind at+4, not the identity at+6.
Keep all existing ownership, request, action and resource guards. Replace
one eight-byte instruction in an existing private carrier; nothing moves.
"""
from copy import deepcopy

from hinoenma_latched_door import NATIVE_SIGNATURE_SPANS


EXPECTED_SLOTS = ((45, 'HE_SameTemplateUnloadChild', 0x8B1868, 7, 0x10000, 0x800),)
OLD_CHECK = 'cmp dword ptr [r9+4], 0x10002\n'
NEW_CHECK = 'cmp word ptr [r9+4], 2\nnop\nnop\n'
OLD_BYTES = bytes.fromhex('4181790402000100')
NEW_BYTES = bytes.fromhex('6641837904029090')


def apply_latched_door_instances(previous_profile):
    """Pure0.50->0.51, one same-length private instruction replacement."""
    if previous_profile.get('tool_version') != '0.50' or len(previous_profile['hooks']) != 49:
        raise ValueError('Latch instances require the complete frozen v0.50 profile')
    if (previous_profile.get('allocation_size'), previous_profile.get('data_offset')) != (0x14000, 0xF000):
        raise ValueError('Unexpected frozen private allocation/data layout')
    if (previous_profile.get('latched_door_revision') != 1
            or previous_profile.get('latched_door_dispatch') != 16
            or previous_profile.get('latched_door_common_actions') != [170, 157]
            or previous_profile.get('latched_door_main_motion_id') != 223
            or previous_profile.get('latched_door_local_event_indices') != [0, 75]):
        raise ValueError('Unexpected frozen native latch action contract')
    for index, name, rva, length, offset, capacity in EXPECTED_SLOTS:
        hook = previous_profile['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != (name, rva, length, offset, capacity):
            raise ValueError('Unexpected latch carrier/private slot')
        if hook['asm'].count(OLD_CHECK) != 1:
            raise ValueError('Expected one frozen latch instance check')
    plan = deepcopy(previous_profile)
    carrier = plan['hooks'][45]
    carrier['asm'] = carrier['asm'].replace(OLD_CHECK, NEW_CHECK)
    carrier['purpose'] += '; native object-kind latch scope permits distinct door instance identities'
    plan.update(tool_version='0.51', stage='native_latched_door_distinct_instances',
        latched_door_revision=2, latched_door_changed_hook_indices=[45],
        latched_door_object=dict(id=15, kind=2, instance='native_object_identity_not_restricted'),
        latched_door_observed_instances=[1, 100],
        latched_door_instance_guard_matches_native_word_kind=True,
        latched_door_native_state_and_other_features_preserved=True,
        latched_door_gameplay_confirmation_pending=True)
    return plan
