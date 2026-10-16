"""Promote the confirmed Soul Purge and Kodama payloads without changing code."""
from copy import deepcopy
from hinoenma_general_jutsu import digest
from hinoenma_soul_purge import apply_soul_purge
from hinoenma_kodama_transform import apply_kodama_transform

VERSION = '1.0.0-beta.6.2'
BASE_VERSION = '1.0.0-beta.6.1.4'
TRIAL_CANONICAL_SHA256 = '027bb12737a73456535609495a237ec57a2a3c8bd8653514166bcbd39a2c2e41'
CONFIRMED = ('soul_purge_candidate', 'kodama_transform_candidate')
RELEASE_FIELDS = dict(beta62_release_revision=1, beta62_gameplay_basis_version=BASE_VERSION,
    beta62_runtime_gameplay_validated=True, beta62_exact_executable_gameplay_validated=False,
    beta62_kodama_live_injury_validated=False, beta62_confirmed_item_ids=[51944, 19707])


def trial_plan(previous):
    plan = apply_kodama_transform(apply_soul_purge(previous))
    if digest(plan) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Exact confirmed Soul Purge and Kodama trial required')
    return plan


def validate_release(plan):
    if (plan.get('tool_version') != VERSION or plan.get('stage') != 'beta62_confirmed_special_jutsu'
            or plan.get('local_package_only') is not False
            or any(plan.get(k) != v for k, v in RELEASE_FIELDS.items())
            or any(plan.get(k, {}).get('live_confirmation_pending') is not False for k in CONFIRMED)):
        raise ValueError('Exact Beta6.2 identity and limited validation scope required')
    trial = deepcopy(plan)
    for key in RELEASE_FIELDS:
        del trial[key]
    for key in CONFIRMED:
        trial[key]['live_confirmation_pending'] = True
    trial.update(tool_version=BASE_VERSION, stage='local_beta614_general_jutsu', local_package_only=True)
    if digest(trial) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Release differs from the installed user-confirmed trial')


def apply_release(previous):
    plan = trial_plan(previous)
    for key in CONFIRMED:
        plan[key]['live_confirmation_pending'] = False
    plan.update(deepcopy(RELEASE_FIELDS))
    plan.update(tool_version=VERSION, stage='beta62_confirmed_special_jutsu', local_package_only=False)
    validate_release(plan)
    return plan
