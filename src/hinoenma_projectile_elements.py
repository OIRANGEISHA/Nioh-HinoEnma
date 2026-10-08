"""Carry current Hino elemental buffs into her observed fixed projectiles.

The native type1 object parameter route skips component1118/111C. At 7E2959
the game copies the completed attack context's original 16 bytes. Preserve
that copy, then replace only its element/power when the original element is
unset. Needle paralysis (context20), physics and base damage are untouched.
Only the observed Hino-owned roar, needle and dive effect templates qualify;
other player objects, guardians, NPCs and intrinsic-element attacks retain
their original values. No shared template table or buff timer is modified.
"""
from copy import deepcopy

from hinoenma_tutorial import player_guard

HOOK_NAME = 'HE_ProjectileElementInheritance'
HOOK_RVA = 0x7E2959
HOOK_ORIGINAL = '0F 10 4D 07 0F 11 4F 18'
CODE_OFFSET = 0x500
CODE_CAPACITY = 0x300
PROJECTILE_TEMPLATES = (0xBEA31, 0x11F85, 0xADD70)

PROJECTILE_ASM = '''movups xmm1, xmmword ptr [rbp+0x07]
movups xmmword ptr [rdi+0x18], xmm1
pushfq
push rax
push rdx
push r10
push r11
mov r11, {data}
'''+player_guard('projectile_element')+'''test r15, r15
je projectile_element_done
cmp word ptr [r15+0x04], 4
jne projectile_element_done
cmp r10, qword ptr [r15+0x200]
jne projectile_element_done
mov eax, dword ptr [r15]
cmp eax, 0xBEA31
je projectile_element_template
cmp eax, 0x11F85
je projectile_element_template
cmp eax, 0xADD70
jne projectile_element_done
projectile_element_template:
cmp dword ptr [rdi+0x18], -1
jne projectile_element_done
mov rax, qword ptr [r10+0x240]
test rax, rax
je projectile_element_done
cmp r10, qword ptr [rax]
jne projectile_element_done
cmp r10, qword ptr [rax+0x108]
jne projectile_element_done
cmp qword ptr [rax+0x20], 0
jle projectile_element_done
mov edx, dword ptr [rax+0x1118]
cmp edx, 4
ja projectile_element_done
mov eax, dword ptr [rax+0x111C]
test eax, eax
jle projectile_element_done
mov dword ptr [rdi+0x18], edx
mov dword ptr [rdi+0x1C], eax
projectile_element_done:
pop r11
pop r10
pop rdx
pop rax
popfq
jmp {return}
'''


def apply_projectile_elements(previous):
    if previous.get('tool_version') != '0.37' or len(previous['hooks']) != 42:
        raise ValueError('Projectile elements require the complete v0.37 plan')
    plan = deepcopy(previous)
    spawn = next(h for h in plan['hooks'] if h['name'] == 'HE_Spawn')
    if spawn['code_offset'] != 0x400 or spawn.get('code_capacity', 0x400) != 0x400:
        raise ValueError('Unexpected spawn code slot')
    spawn['code_capacity'] = 0x100
    plan['hooks'].append(dict(name=HOOK_NAME, rva=HOOK_RVA, length=8,
        original=HOOK_ORIGINAL, code_offset=CODE_OFFSET, code_capacity=CODE_CAPACITY,
        purpose='Current Hino-owned roar, needle and dive-effect attack contexts inherit native buff element/power while preserving all other fields',
        asm=PROJECTILE_ASM))
    spans = sorted((h['code_offset'], h['code_offset']+h.get('code_capacity', 0x400)) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])) or spans[-1][1] > plan['data_offset']:
        raise ValueError('Projectile element code overlaps existing code or data')
    plan.update(tool_version='0.38', projectile_element_inheritance_revision=1,
                projectile_element_templates=list(PROJECTILE_TEMPLATES),
                stage='projectile_element_inheritance_pending_gameplay')
    return plan
