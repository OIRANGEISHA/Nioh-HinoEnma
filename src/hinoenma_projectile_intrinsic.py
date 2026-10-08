"""Protect intrinsic projectile status channels from enchant replacement.

Native72746C chooses context18 or, if unset, descriptor20; native727487
uses context1C for that chosen type. Roar's descriptor20=6 uses the original
power150. Leaving the VFX at context20 unchanged does not preserve that
status channel. Only a projectile with both an unset context18 and an
unset descriptor20 may currently inherit the parent's enchant in-place.
Intrinsic projectiles require a separately verified additive damage path.
"""
from copy import deepcopy


def apply_projectile_intrinsic_protection(previous):
    if previous.get('tool_version') != '0.39' or len(previous['hooks']) != 45:
        raise ValueError('Intrinsic status protection requires complete v0.39')
    plan = deepcopy(previous)
    hook = next(h for h in plan['hooks'] if h['name'] == 'HE_ProjectileElementInheritance')
    old = '''cmp dword ptr [rdi+0x18], -1
jne projectile_element_done
'''
    new = old+'''mov rax, qword ptr [rdi]
test rax, rax
je projectile_element_done
cmp byte ptr [rax+0x20], 0xFF
jne projectile_element_done
'''
    if hook['asm'].count(old) != 1 or hook['code_offset'] != 0x500:
        raise ValueError('Unexpected projectile element hook')
    hook['asm'] = hook['asm'].replace(old, new)
    hook['purpose'] = 'Preserve native intrinsic projectile element/status and strength; inherit buffs only where both native channels are unset'
    plan.update(tool_version='0.40', projectile_intrinsic_protection_revision=1,
                intrinsic_projectile_additive_enchant_pending=True,
                stage='intrinsic_projectile_status_protection')
    return plan
