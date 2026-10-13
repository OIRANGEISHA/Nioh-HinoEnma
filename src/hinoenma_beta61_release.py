"""Metadata-only promotion of the three live-confirmed native spell routes."""
from copy import deepcopy

from hinoenma_beta6_release import (validate_release as validate_beta6,
    ITEM_CODE_INTERVAL as BETA6_ITEM_INTERVAL, PREVIOUS_LW_CODE_INTERVALS)
from hinoenma_wind_weakness_dragon import apply_wind_weakness_dragon

VERSION = '1.0.0-beta.6.1'
BASE_VERSION = '1.0.0-beta.6'
ITEM_IDS = (26116, 44930, 44607)
ITEM_CODE_INTERVAL = [0x4000, 32164]
CARRIER = 'HE_LivingWeaponDigitNine'


def validate_release(plan):
    if (plan.get('tool_version') != VERSION
            or plan.get('beta61_release_revision') != 1
            or plan.get('beta61_gameplay_basis_version') != BASE_VERSION
            or plan.get('beta61_confirmed_item_ids') != list(ITEM_IDS)
            or plan.get('beta61_runtime_gameplay_validated') is not True
            or plan.get('beta61_exact_executable_gameplay_validated') is not False
            or plan.get('beta61_item_code_intervals_revision') != 1
            or plan.get('wind_weakness_dragon_revision') != 1
            or plan.get('wind_weakness_dragon_item_ids') != list(ITEM_IDS)
            or plan.get('wind_weakness_dragon_common_actions') != [42, 1165, 1227, 1228]
            or plan.get('wind_weakness_dragon_gameplay_confirmation_pending') is not False
            or plan.get('wind_weakness_dragon_auxiliary_timing_guard_pending') is not False
            or plan.get('wind_weakness_dragon_direct_inventory_effect_hp_save_writes') is not False
            or plan.get('abyss_assembly_code_intervals', {}).get(CARRIER)
                != PREVIOUS_LW_CODE_INTERVALS + [ITEM_CODE_INTERVAL]):
        raise ValueError('Exact confirmed Beta6.1 three-spell release metadata required')
    # The older validator intentionally retains its own version and instruction
    # interval contract. Adapt only the validation copy, never the release plan.
    basis = deepcopy(plan)
    basis['tool_version'] = BASE_VERSION
    basis['abyss_assembly_code_intervals'][CARRIER] = (
        deepcopy(PREVIOUS_LW_CODE_INTERVALS) + [list(BETA6_ITEM_INTERVAL)])
    validate_beta6(basis)


def apply_release(previous):
    validate_beta6(previous)
    if previous.get('beta61_release_revision'):
        raise ValueError('Exact unpromoted Beta6 basis required')
    plan = apply_wind_weakness_dragon(previous)
    plan['wind_weakness_dragon_gameplay_confirmation_pending'] = False
    # JSON object keys are strings. Normalize metadata before freezing so that
    # the source rebuild and on-disk profile compare without lossy coercion.
    plan['wind_weakness_dragon_auxiliary_descriptor_checks'] = {
        str(key): value for key, value in
        plan['wind_weakness_dragon_auxiliary_descriptor_checks'].items()}
    plan.update(tool_version=VERSION, beta61_release_revision=1,
        beta61_gameplay_basis_version=BASE_VERSION,
        beta61_confirmed_item_ids=list(ITEM_IDS),
        beta61_runtime_gameplay_validated=True,
        beta61_exact_executable_gameplay_validated=False,
        beta61_item_code_intervals_revision=1,
        local_package_only=True, stage='local_beta61_confirmed_spells')
    validate_release(plan)
    return plan
