"""Extend item-animation compatibility to native skill-point locks only.

The current catalogue has three tiers each of Samurai/Ninja/Onmyo locks:
ordinary kind 1/subtype 0, category 1, a single effect of type 18/19/20.
Native eligibility, effect amount, cooldown and inventory commit stay intact.
"""
from hinoenma_hooks import PLAYER_SELF_CONSUMABLES

SKILL_LOCKS_EFFECT_TYPES = (18, 19, 20)


def skill_locks_hook():
    hook = dict(PLAYER_SELF_CONSUMABLES)
    guard = '''mov ecx, dword ptr [rax+0x04]
cmp ecx, 64'''
    if hook['asm'].count(guard) != 1:
        raise ValueError('Unexpected native consumable effect guard')
    hook['asm'] = hook['asm'].replace(guard, '''mov ecx, dword ptr [rax+0x04]
mov eax, ecx
sub eax, 18
cmp eax, 2
ja consumable_regular_effect
cmp dword ptr [rdi+0x54C], 1
jne consumable_original
test ebx, ebx
jne consumable_original
cmp dword ptr [rsi+0x114], 0
jne consumable_original
cmp dword ptr [rsi+0x118], 0
jne consumable_original
jmp consumable_approved
consumable_regular_effect:
cmp ecx, 64''')
    hook['purpose'] = 'Continue accepted ordinary self-recovery/buffs or single-effect Samurai/Ninja/Onmyo locks through native effects and inventory commit'
    return hook
