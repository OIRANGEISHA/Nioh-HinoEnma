"""Recognize the current Hino player's built-in attacks for elemental use.

Native A8D240 receives an effect ID and its recipient, then looks up the
effect. Types 3..7 reach A8D3F0, which rejects an empty William melee slot.
Hino has native attacks while both logical slots can legitimately be empty.
Only that weapon-presence check is bypassed for the captured live player;
A8D40C still performs the original Living Weapon restriction. Quantity,
inventory, request, cooldown, menus and native effect dispatch are untouched.
"""
from copy import deepcopy

from hinoenma_tutorial import player_guard

HOOK_NAME = 'HE_ElementalItemEligibility'
HOOK_RVA = 0xA8D283
HOOK_ORIGINAL = '8B 48 04 81 F9 73 01 00 00'
CODE_OFFSET = 0x5E80
CODE_CAPACITY = 0x180

ELIGIBILITY_ASM = '''pushfq
push rax
push r10
push r11
mov r11, {data}
'''+player_guard('element_eligibility')+'''cmp r10, rbp
jne element_eligibility_done
mov rax, qword ptr [r10+0x240]
test rax, rax
je element_eligibility_done
cmp r10, qword ptr [rax]
jne element_eligibility_done
cmp r10, qword ptr [rax+0x108]
jne element_eligibility_done
cmp qword ptr [rax+0x20], 0
jle element_eligibility_done
mov rax, qword ptr [rsp+0x10]
cmp dword ptr [rax+0x04], 3
jb element_eligibility_done
cmp dword ptr [rax+0x04], 7
ja element_eligibility_done
pop r11
pop r10
pop rax
popfq
jmp {element_eligibility_lw}
element_eligibility_done:
pop r11
pop r10
pop rax
popfq
mov ecx, dword ptr [rax+0x04]
cmp ecx, 0x173
jmp {return}
'''


def apply_element_eligibility(previous):
    if previous.get('tool_version') != '0.36' or len(previous['hooks']) != 41:
        raise ValueError('Elemental eligibility requires the complete v0.36 plan')
    plan = deepcopy(previous)
    carrier = next(h for h in plan['hooks'] if h['name'] == 'HE_TalismanElementVisualParameter')
    if carrier['code_offset'] != 0x5C00 or carrier.get('code_capacity') != 0x400:
        raise ValueError('Unexpected elemental helper slot')
    carrier['code_capacity'] = 0x280
    plan['targets']['element_eligibility_lw'] = 0xA8D40C
    plan['hooks'].append(dict(name=HOOK_NAME, rva=HOOK_RVA, length=9,
        original=HOOK_ORIGINAL, code_offset=CODE_OFFSET, code_capacity=CODE_CAPACITY,
        purpose='Current live Hino built-in attacks satisfy elemental effect types3..7 weapon presence; native Living Weapon restriction remains',
        asm=ELIGIBILITY_ASM))
    spans = sorted((h['code_offset'], h['code_offset']+h.get('code_capacity', 0x400)) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])) or spans[-1][1] > plan['data_offset']:
        raise ValueError('Element eligibility code overlaps existing code or data')
    plan.update(tool_version='0.37', elemental_eligibility_revision=1,
                stage='elemental_repeat_eligibility_pending_gameplay')
    return plan
