"""Version-only promotion of the live-confirmed Growth750 payload."""
from copy import deepcopy
from hinoenma_growth750 import apply_growth750, LEVEL_MAPPING
from living_weapon_start_production_layout import validate_production_layout

VERSION = '1.0.0-beta.5.6.3'


def validate_release(plan):
    if (plan.get('tool_version') != VERSION
            or plan.get('growth750_revision') != 1
            or plan.get('growth750_release_revision') != 1
            or plan.get('growth750_trial') is not False
            or plan.get('hp_growth_level_mapping') != LEVEL_MAPPING
            or plan.get('combat_growth_level_mapping') != LEVEL_MAPPING
            or plan.get('growth750_extra_multipliers') != dict(first_level=401, hp=[2, 1], attack=[6, 5])
            or plan.get('growth750_focus_channels') != ['hp', 'attack', 'defense', 'luck']
            or plan.get('growth750_flat_attack_separate') is not True):
        raise ValueError('Exact Beta5.6.3 growth policy required')
    previous = deepcopy(plan)
    previous['tool_version'] = '1.0.0-beta.5.6.2'
    validate_production_layout(previous)


def apply_release(previous):
    plan = apply_growth750(previous)
    plan.update(tool_version=VERSION, growth750_trial=False,
        growth750_release_revision=1, stage='local_beta563_growth750',
        growth750_gameplay_confirmation_pending=False,
        growth750_warm_gameplay_validated=True,
        growth750_exact_executable_gameplay_validated=False)
    validate_release(plan)
    return plan
