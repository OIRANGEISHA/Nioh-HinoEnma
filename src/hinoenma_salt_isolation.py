"""Pure v0.52 -> v0.53 isolation of the unverified salt action path.

Salt7739 no longer enters common172 through the additional item helper.
InputA/B no longer hold native action982. Other seven routes retain their
exact frozen implementation; this does not repair an already running action
or claim salt gameplay success. Native sites and fixed resource entries stay.
"""
from copy import deepcopy

HOOK_INDICES = (6, 7, 48)
CODE_OFFSETS = (0x1800, 0x1C00, 0x11800)
CODE_CAPACITIES = (0x400, 0x400, 0x1800)
PAYLOAD_BYTES = (463, 463, 5837)
ENABLED_ITEM_IDS = (12084, 50129, 7696, 22295, 49379, 46858, 33287)
EXPECTED_SLOTS = (
    (6, 'HE_InputA', 0x721044, 5, 0x1800, 0x400),
    (7, 'HE_InputB', 0x721099, 5, 0x1C00, 0x400),
    (48, 'HE_SameTemplateUnloadResources', 0x8B1A10, 5, 0x11800, 0x1800),
)


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Frozen salt route shape differs')
    return text.replace(old, new, 1)


def apply_salt_isolation(previous):
    if (previous.get('tool_version') != '0.52' or len(previous.get('hooks', ())) != 49
            or (previous.get('allocation_size'), previous.get('data_offset')) != (0x14000, 0xF000)
            or previous.get('special_item_ids') != [12084,50129,7739,7696,22295,49379,46858,33287]):
        raise ValueError('Complete frozen v0.52 special-item candidate required')
    for index, *fields in EXPECTED_SLOTS:
        hook = previous['hooks'][index]
        if (hook['name'], hook['rva'], hook['length'], hook['code_offset'],
                hook.get('code_capacity', 0x400)) != tuple(fields):
            raise ValueError('Unexpected existing salt-isolation slot')
    plan = deepcopy(previous)
    hook = plan['hooks'][48]
    hook['asm'] = _once(hook['asm'],
        'cmp dword ptr [rdi+0x548], 7739\nje special_item_definition_7739\n',
        'cmp dword ptr [rdi+0x548], 7739\nje special_item_restore\n')
    for index, suffix in ((6, 'a'), (7, 'b')):
        hook = plan['hooks'][index]
        hook['asm'] = _once(hook['asm'],
            f'mov ecx, 120\ncmp dword ptr [rdx], 982\nje special_item_input_found_{suffix}\n',
            f'mov ecx, 120\ncmp dword ptr [rdx], 982\nje special_item_input_continue_{suffix}\n')
    plan.update(tool_version='0.53', stage='experimental_unverified_salt_route_containment',
        special_items_revision=2, special_item_actions_revision=2,
        special_items_salt_disabled_id=7739, special_items_salt_disabled_native_action=982,
        special_items_salt_gameplay_verified=False, special_items_salt_stuck_state_repair=False,
        special_item_ids=list(ENABLED_ITEM_IDS), special_items_other_seven_implementation_preserved=True,
        user_confirmed_prior_item_ids=list(ENABLED_ITEM_IDS),
        special_items_damage_compatibility_fully_verified=False,
        special_item_actions_item_ids=[12084,50129,7696,22295,49379],
        special_item_actions_common_actions=[172,165,601,602,610,1185],
        special_item_actions_changed_hook_indices=list(HOOK_INDICES),
        special_item_actions_gameplay_confirmation_pending=True,
        special_items_gameplay_confirmation_pending=True,
        salt_isolation_changed_hook_indices=list(HOOK_INDICES),
        salt_isolation_all_payload_lengths_unchanged=True,
        salt_isolation_native_sites_and_other46_payloads_unchanged=True)
    return plan
