"""Promote the four user-confirmed item repairs without changing their code."""
from copy import deepcopy
import hashlib
import json

from hinoenma_spell_event_catchup import apply_spell_event_catchup
from hinoenma_item_hurt_lookup import apply_item_hurt_lookup
from hinoenma_item_recast_lookup import apply_item_recast_lookup
from hinoenma_guardian_sludge_items import apply_guardian_sludge_items

VERSION = '1.0.0-beta.6.1.1'
BASE_VERSION = '1.0.0-beta.6.1'
TRIAL_CANONICAL_SHA256 = '3e7f44589165440bdbfc94355da320752d6e699c57c530ed6b346f2bed3a60b9'
TRANSFORMS = (apply_spell_event_catchup, apply_item_hurt_lookup,
              apply_item_recast_lookup, apply_guardian_sludge_items)
CONFIRMED = ('spell_event_catchup_candidate', 'item_hurt_lookup_candidate',
             'item_recast_lookup_candidate', 'guardian_sludge_items_candidate')
RELEASE_FIELDS = dict(
    beta611_release_revision=1,
    beta611_gameplay_basis_version=BASE_VERSION,
    beta611_runtime_gameplay_validated=True,
    beta611_exact_executable_gameplay_validated=False,
    beta611_confirmed_new_item_ids=[62705, 20527],
    beta611_confirmed_spell_effect_ids=[26116, 44930],
)


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest()


def trial_plan(previous):
    plan = previous
    for apply in TRANSFORMS:
        plan = apply(plan)
    if digest(plan) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Exact user-confirmed four-repair trial required')
    return plan


def validate_release(plan):
    if (plan.get('tool_version') != VERSION
            or plan.get('stage') != 'local_beta611_confirmed_items'
            or plan.get('local_package_only') is not True
            or any(plan.get(key) != value for key, value in RELEASE_FIELDS.items())
            or any(plan.get(key, {}).get('live_confirmation_pending') is not False
                   for key in CONFIRMED)):
        raise ValueError('Exact Beta6.1.1 release identity and validation scope required')
    # Restore only promotion metadata. The digest pins every instruction,
    # relocation interval, signature, target, code slot and protected data page.
    # The original trial and its evidence retain their pre-release identities.
    trial = deepcopy(plan)
    for key in RELEASE_FIELDS:
        del trial[key]
    trial['tool_version'] = BASE_VERSION
    trial['stage'] = 'local_beta61_confirmed_spells'
    for key in CONFIRMED:
        trial[key]['live_confirmation_pending'] = True
    if digest(trial) != TRIAL_CANONICAL_SHA256:
        raise ValueError('Release differs from the exact confirmed trial')


def apply_release(previous):
    plan = trial_plan(previous)
    for key in CONFIRMED:
        plan[key]['live_confirmation_pending'] = False
    plan.update(deepcopy(RELEASE_FIELDS))
    plan.update(tool_version=VERSION, stage='local_beta611_confirmed_items')
    validate_release(plan)
    return plan
