"""Promote the live-confirmed resistance talismans without changing payloads."""
from copy import deepcopy
import hashlib
import json

from hinoenma_elemental_resistance_items import apply_elemental_resistance_items

VERSION = '1.0.0-beta.6.1.2'
BASE_VERSION = '1.0.0-beta.6.1.1'
TRIAL_CANONICAL_SHA256 = '4396cab287160082c91e6f39b9edd5ccb8e5929f4481936c41c08a4da18b294b'
CONFIRMED = 'elemental_resistance_items_candidate'
RELEASE_FIELDS = dict(
    beta612_release_revision=1,
    beta612_gameplay_basis_version=BASE_VERSION,
    beta612_runtime_gameplay_validated=True,
    beta612_exact_executable_gameplay_validated=False,
    beta612_confirmed_item_ids=[7785, 805, 64630, 35156, 10101],
    beta612_quantity_decrement_not_required=True,
)


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()


def trial_plan(previous):
    plan = apply_elemental_resistance_items(previous)
    if digest(plan) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Exact user-confirmed resistance trial required')
    return plan


def validate_release(plan):
    if (plan.get('tool_version') != VERSION
            or plan.get('stage') != 'local_beta612_confirmed_resistance'
            or plan.get('local_package_only') is not True
            or any(plan.get(key) != value for key, value in RELEASE_FIELDS.items())
            or plan.get(CONFIRMED, {}).get('live_confirmation_pending') is not False):
        raise ValueError('Exact Beta6.1.2 release identity and validation scope required')
    trial = deepcopy(plan)
    for key in RELEASE_FIELDS:
        del trial[key]
    trial['tool_version'] = BASE_VERSION
    trial['stage'] = 'local_beta611_confirmed_items'
    trial[CONFIRMED]['live_confirmation_pending'] = True
    if digest(trial) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Release differs from the exact confirmed resistance trial')


def apply_release(previous):
    plan = trial_plan(previous)
    plan[CONFIRMED]['live_confirmation_pending'] = False
    plan.update(deepcopy(RELEASE_FIELDS))
    plan.update(tool_version=VERSION, stage='local_beta612_confirmed_resistance')
    validate_release(plan)
    return plan
