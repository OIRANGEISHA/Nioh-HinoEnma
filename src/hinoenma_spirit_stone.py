"""Allow accepted ordinary single-effect spirit stones through native commit.

The observed Small Spirit Stone 42170 is kind1/subtype0, category1 with one
effect39321/type16. Native A84B0C dispatches type16 through D8CEC0 using its
own effect parameters, count and actor position. Nothing here applies an
effect, grants currency, edits inventory or credits teaching on its own.
Only this verified effect class can use the existing missing-animation
fallback. Native eligibility, effect dispatch, cooldown, inventory commit
and HE_ConsumableNotice remain intact. Digit skills and shortcuts are untouched.
"""


def spirit_stones_hook(previous):
    hook=dict(previous)
    original='mov ecx, dword ptr [rax+0x04]\nmov eax, ecx'
    if hook['name']!='HE_Consumables' or hook['asm'].count(original)!=1:
        raise ValueError('Unexpected skill-lock compatible consumable guard')
    hook['asm']=hook['asm'].replace(original,'''mov ecx, dword ptr [rax+0x04]
cmp ecx, 16
jne consumable_non_stone_effect
cmp dword ptr [rdi+0x54C], 1
jne consumable_original
test ebx, ebx
jne consumable_original
cmp dword ptr [rsi+0x114], 0
jne consumable_original
cmp dword ptr [rsi+0x118], 0
jne consumable_original
cmp dword ptr [rax+0x08], 0
jle consumable_original
cmp dword ptr [rax+0x0C], 0
jne consumable_original
cmp dword ptr [rax+0x10], 100
jne consumable_original
cmp dword ptr [rax+0x14], 0
jle consumable_original
cmp dword ptr [rax+0x18], 0
jne consumable_original
cmp dword ptr [rax+0x1C], 100
jne consumable_original
cmp dword ptr [rax+0x20], 0
jne consumable_original
cmp dword ptr [rax+0x24], 0
jne consumable_original
cmp dword ptr [rax+0x28], 0
jne consumable_original
jmp consumable_approved
consumable_non_stone_effect:
mov eax, ecx''')
    hook['purpose']='Continue accepted ordinary self-recovery/buffs, single-effect skill locks or category1 single-effect type16 spirit stones through native effects and inventory commit'
    return hook
