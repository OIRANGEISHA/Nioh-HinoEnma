"""Package the tested general-jutsu/Kunai revision without changing its code.

Only the sampled Kunai use/recast/injury path is gameplay-confirmed here. The
family dispatcher is not a claim that every ninjutsu or Onmyo effect works.
"""
from copy import deepcopy
from hinoenma_general_jutsu import apply_general_jutsu, digest
from hinoenma_general_jutsu_timing import apply_general_jutsu_timing
from hinoenma_general_jutsu_recovery import apply_general_jutsu_recovery

VERSION = '1.0.0-beta.6.1.4'
BASE_VERSION = '1.0.0-beta.6.1.3'
TRIAL_CANONICAL_SHA256 = 'e7677327734d1eee83d6849add4af1c4906b59e91967b1ccc2758bd81ad2bc87'
RELEASE_FIELDS = dict(beta614_release_revision=1,
    beta614_gameplay_basis_version=BASE_VERSION,
    beta614_sampled_kunai_gameplay_validated=True,
    beta614_all_jutsu_gameplay_validated=False,
    beta614_exact_executable_gameplay_validated=False,
    beta614_confirmed_item_ids=[57728])


def trial_plan(previous):
    plan = previous
    for apply in (apply_general_jutsu, apply_general_jutsu_timing, apply_general_jutsu_recovery):
        plan = apply(plan)
    if digest(plan) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Exact sampled and user-confirmed general-jutsu trial required')
    return plan


def validate_release(plan):
    if (plan.get('tool_version') != VERSION or plan.get('stage') != 'local_beta614_general_jutsu'
            or plan.get('local_package_only') is not True
            or any(plan.get(k) != v for k,v in RELEASE_FIELDS.items())):
        raise ValueError('Exact Beta6.1.4 identity and limited gameplay scope required')
    trial = deepcopy(plan)
    for key in RELEASE_FIELDS: del trial[key]
    trial.update(tool_version=BASE_VERSION, stage='local_beta613_confirmed_items')
    if digest(trial) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Release differs from the installed and tested trial')


def apply_release(previous):
    plan = trial_plan(previous)
    plan.update(deepcopy(RELEASE_FIELDS))
    plan.update(tool_version=VERSION, stage='local_beta614_general_jutsu')
    validate_release(plan)
    return plan
