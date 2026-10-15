"""Promote the complete confirmed item chain without changing runtime payloads."""
from copy import deepcopy
import hashlib, json
from hinoenma_sticky_dispersal_items import apply_sticky_dispersal_items
from hinoenma_dispersal_reuse import apply_dispersal_reuse
from hinoenma_nine_talismans import apply_nine_talismans
from hinoenma_soul_release import apply_soul_release

VERSION='1.0.0-beta.6.1.3'
BASE_VERSION='1.0.0-beta.6.1.2'
TRIAL_CANONICAL_SHA256='5a5a99a515d6895ba5e624f1b8f16fb7a24d398d597e01e12acd545fbcb0d781'
CONFIRMED=('sticky_dispersal_items_candidate','dispersal_reuse_candidate',
           'nine_talismans_candidate','soul_release_candidate')
RELEASE_FIELDS=dict(beta613_release_revision=1,beta613_gameplay_basis_version=BASE_VERSION,
    beta613_runtime_gameplay_validated=True,beta613_exact_executable_gameplay_validated=False,
    beta613_confirmed_item_ids=[57901,22722,52306,40718,19803,31267,3735,52147,3944,24932,35389,64629])

def digest(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def trial_plan(previous):
    plan=previous
    for apply in (apply_sticky_dispersal_items,apply_dispersal_reuse,apply_nine_talismans,apply_soul_release):
        plan=apply(plan)
    if digest(plan)!=TRIAL_CANONICAL_SHA256:raise ValueError('Exact user-confirmed twelve-item trial required')
    return plan

def validate_release(plan):
    if (plan.get('tool_version')!=VERSION or plan.get('stage')!='local_beta613_confirmed_items'
        or plan.get('local_package_only') is not True
        or any(plan.get(k)!=v for k,v in RELEASE_FIELDS.items())
        or any(plan.get(k,{}).get('live_confirmation_pending') is not False for k in CONFIRMED)):
        raise ValueError('Exact Beta6.1.3 release identity and validation scope required')
    trial=deepcopy(plan)
    for key in RELEASE_FIELDS:del trial[key]
    trial['tool_version']=BASE_VERSION
    trial['stage']='local_beta612_confirmed_resistance'
    for key in CONFIRMED:trial[key]['live_confirmation_pending']=True
    if digest(trial)!=TRIAL_CANONICAL_SHA256:raise ValueError('Release differs from the confirmed live trial')

def apply_release(previous):
    plan=trial_plan(previous)
    for key in CONFIRMED:plan[key]['live_confirmation_pending']=False
    plan.update(deepcopy(RELEASE_FIELDS))
    plan.update(tool_version=VERSION,stage='local_beta613_confirmed_items')
    validate_release(plan)
    return plan
