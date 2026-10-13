"""Version-only promotion of the ten live-confirmed item compatibility fixes."""
from copy import deepcopy

from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import apply_dung_fan
from hinoenma_four_throwables import apply_four_throwables
from hinoenma_arrow_sloth import apply_arrow_sloth
from hinoenma_arrow_sloth_lookup import apply_arrow_sloth_lookup

VERSION = '1.0.0-beta.6'
BASE_VERSION = '1.0.0-beta.5.6.3'
REVISIONS = ('harakiri', 'dung_fan', 'four_throwables',
             'arrow_sloth', 'arrow_sloth_lookup')
ITEM_IDS = (34209, 32016, 6518, 44220, 63258, 46857, 40896, 4600, 64367, 4998)
ITEM_CODE_INTERVAL = [0x4000, 26103]
PREVIOUS_LW_CODE_INTERVALS = [[0, 3557], [4096, 14381]]


def validate_release(plan):
    if (plan.get('tool_version') != VERSION
            or plan.get('beta6_release_revision') != 1
            or plan.get('beta6_gameplay_basis_version') != BASE_VERSION
            or plan.get('beta6_confirmed_item_ids') != list(ITEM_IDS)
            or plan.get('beta6_runtime_gameplay_validated') is not True
            or plan.get('beta6_exact_executable_gameplay_validated') is not False
            or plan.get('beta6_item_code_intervals_revision') != 1
            or plan.get('abyss_assembly_code_intervals', {}).get('HE_LivingWeaponDigitNine')
                != PREVIOUS_LW_CODE_INTERVALS + [ITEM_CODE_INTERVAL]
            or any(plan.get(key+'_revision') != 1 for key in REVISIONS)
            or any(plan.get(key+'_gameplay_confirmation_pending') is not False
                   for key in REVISIONS)):
        raise ValueError('Exact confirmed Beta6 item release metadata required')
    # Preserve the old validator's version contract rather than broadening it.
    from hinoenma_growth750_release import validate_release as validate_beta563
    basis = deepcopy(plan)
    basis['tool_version'] = BASE_VERSION
    validate_beta563(basis)


def apply_release(previous):
    if (previous.get('tool_version') != BASE_VERSION
            or previous.get('growth750_release_revision') != 1
            or previous.get('beta6_release_revision')):
        raise ValueError('Exact Beta5.6.3 release basis required')
    plan = previous
    for apply_revision in (apply_harakiri, apply_dung_fan, apply_four_throwables,
                           apply_arrow_sloth, apply_arrow_sloth_lookup):
        plan = apply_revision(plan)
    for key in REVISIONS:
        plan[key+'_gameplay_confirmation_pending'] = False
    intervals = plan.get('abyss_assembly_code_intervals', {})
    if intervals.get('HE_LivingWeaponDigitNine') != PREVIOUS_LW_CODE_INTERVALS:
        raise ValueError('Exact pre-item LW instruction intervals required')
    # The native-start carrier intentionally excludes embedded data. Its new
    # item tail is all instructions and must participate in EXE relocation.
    # Keeping only the old intervals would leave absolute pointers unrelocated.
    intervals['HE_LivingWeaponDigitNine'] += [list(ITEM_CODE_INTERVAL)]
    plan.update(tool_version=VERSION, beta6_release_revision=1,
                beta6_item_code_intervals_revision=1,
                beta6_gameplay_basis_version=BASE_VERSION,
                beta6_confirmed_item_ids=list(ITEM_IDS),
                beta6_runtime_gameplay_validated=True,
                beta6_exact_executable_gameplay_validated=False,
                local_package_only=True, stage='local_beta6_confirmed_items')
    validate_release(plan)
    return plan
