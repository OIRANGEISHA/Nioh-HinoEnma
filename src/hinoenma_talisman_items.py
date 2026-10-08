"""Native elemental consumables and the observed shrine-return item.

Keep existing item eligibility, confirmation, cooldown, effect dispatch and
inventory commit. The player's missing use animation is the only bypass.
Ordinary category8/subtype15, single-effect element types3..7 are accepted;
category7 additionally requires the observed Travel Amulet52207/effect8969.
Kind2 jutsu, unknown warps, mixed effects and empty-effect Signpost are excluded.

The native element factory's paired suppress-weapon-visuals boolean avoids
William weapon resource lookups while retaining element, power and duration.
The helper occupies the existing unallocated 5C00..6000 private-code gap.
"""
from copy import deepcopy

from hinoenma_tutorial import player_guard

ELEMENT_HOOK_NAME = 'HE_TalismanElementVisualParameter'
ELEMENT_HOOK_RVA = 0xA845BF
ELEMENT_HOOK_ORIGINAL = 'C6 44 24 20 00'
CARRIER_OFFSET = 0x5C00
HELPER_OFFSET = 0x140
HELPER_FROM_DATA = 0xF000 - CARRIER_OFFSET - HELPER_OFFSET

VISUAL_GUARD = '''pushfq
push rax
push r10
push r11
mov r11, {data}
'''+player_guard('talisman_visual').replace('talisman_visual_done', 'talisman_visual_original')+'''cmp r10, r14
jne talisman_visual_original
mov rax, qword ptr [r10+0x240]
cmp rax, r15
jne talisman_visual_original
lea rax, [r15+0x10B0]
cmp rax, rcx
jne talisman_visual_original
cmp r10, qword ptr [r15+0x1218]
jne talisman_visual_original
mov rax, qword ptr [r10+0x230]
test rax, rax
je talisman_visual_original
mov rax, qword ptr [rax+8]
test rax, rax
je talisman_visual_original
cmp r10, qword ptr [rax+0x50]
jne talisman_visual_original
cmp dword ptr [rax+0x54C], 8
jne talisman_visual_original
cmp r13d, dword ptr [rax+0x548]
jne talisman_visual_original
cmp r13d, dword ptr [r11+0x54]
jne talisman_visual_original
cmp dword ptr [rax+0x550], 1
jne talisman_visual_original
cmp word ptr [rax+0x554], 0x100
jne talisman_visual_original
pop r11
pop r10
pop rax
popfq
mov byte ptr [rsp+0x20], 1
jmp {return}
talisman_visual_original:
pop r11
pop r10
pop rax
popfq
mov byte ptr [rsp+0x20], 0
jmp {return}
'''

ITEM_HELPER = '''talisman_helper:
push rbx
push rsi
sub rsp, 0x28
mov ebx, dword ptr [rdi+0x54C]
cmp ebx, 7
je talisman_helper_category
cmp ebx, 8
jne talisman_helper_reject
talisman_helper_category:
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je talisman_helper_reject
mov rcx, qword ptr [rcx+0x20]
test rcx, rcx
je talisman_helper_reject
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je talisman_helper_reject
mov edx, dword ptr [rdi+0x548]
call {item_lookup}
test rax, rax
je talisman_helper_reject
mov edx, dword ptr [rdi+0x548]
cmp dword ptr [rax], edx
jne talisman_helper_reject
cmp word ptr [rax+0x04], 0x0F01
jne talisman_helper_reject
test byte ptr [rax+0x104], 1
je talisman_helper_reject
cmp dword ptr [rax+0x10C], ebx
jne talisman_helper_reject
mov rsi, rax
xor edx, edx
xor ecx, ecx
talisman_helper_slot:
mov eax, dword ptr [rsi+rcx*4+0x110]
test eax, eax
je talisman_helper_next_slot
test edx, edx
jne talisman_helper_reject
mov edx, eax
talisman_helper_next_slot:
inc ecx
cmp ecx, 3
jb talisman_helper_slot
test edx, edx
je talisman_helper_reject
cmp ebx, 7
jne talisman_helper_effect
cmp dword ptr [rsi], 52207
jne talisman_helper_reject
cmp edx, 8969
jne talisman_helper_reject
talisman_helper_effect:
mov dword ptr [rsp+0x20], edx
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je talisman_helper_reject
mov rcx, qword ptr [rcx+0x148]
test rcx, rcx
je talisman_helper_reject
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je talisman_helper_reject
call {effect_lookup}
test rax, rax
je talisman_helper_reject
mov edx, dword ptr [rsp+0x20]
cmp dword ptr [rax], edx
jne talisman_helper_reject
mov eax, dword ptr [rax+0x04]
cmp ebx, 7
jne talisman_helper_element
cmp eax, 14
jne talisman_helper_reject
jmp talisman_helper_accept
talisman_helper_element:
sub eax, 3
cmp eax, 4
ja talisman_helper_reject
talisman_helper_accept:
mov eax, 1
jmp talisman_helper_return
talisman_helper_reject:
xor eax, eax
talisman_helper_return:
add rsp, 0x28
pop rsi
pop rbx
ret
'''


def apply_talisman_items(previous):
    """Extend a complete v0.35 plan without moving any original code slots."""
    if previous.get('tool_version') != '0.35' or len(previous['hooks']) != 40:
        raise ValueError('Talisman compatibility requires the complete v0.35 plan')
    plan = deepcopy(previous)
    consumables = next(h for h in plan['hooks'] if h['name'] == 'HE_Consumables')
    anchor = '''mov eax, dword ptr [rdi+0x54C]
sub eax, 1
cmp eax, 2
ja consumable_original
'''
    replacement = '''mov eax, dword ptr [rdi+0x54C]
cmp eax, 3
jbe talisman_existing_category
mov rax, {data}
sub rax, '''+hex(HELPER_FROM_DATA)+'''
call rax
test al, al
je consumable_original
jmp talisman_native_commit
talisman_existing_category:
sub eax, 1
cmp eax, 2
ja consumable_original
'''
    commit = 'mov r11, {data}\ninc dword ptr [r11+0x50]\n'
    if consumables['asm'].count(anchor) != 1 or consumables['asm'].count(commit) != 1:
        raise ValueError('Existing consumable guards differ')
    consumables['asm'] = consumables['asm'].replace(anchor, replacement).replace(commit, 'talisman_native_commit:\n'+commit)
    consumables['purpose'] += '; ordinary single-effect elemental talismans and verified shrine-return item retain native commit'
    # Encoded guard length is independent of runtime ASLR. The helper entry is
    # fixed, and all its data/native addresses use normal profile relocation.
    from keystone import Ks, KS_ARCH_X86, KS_MODE_64
    values = {key: 0x140000000+rva for key, rva in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'], **{'return': 0x140000000+ELEMENT_HOOK_RVA+5})
    encoded, _ = Ks(KS_ARCH_X86, KS_MODE_64).asm(VISUAL_GUARD.format(**values), addr=0x144000000+CARRIER_OFFSET)
    if len(encoded) > HELPER_OFFSET:
        raise ValueError('Visual guard overlaps fixed helper entry')
    plan['hooks'].append(dict(name=ELEMENT_HOOK_NAME, rva=ELEMENT_HOOK_RVA, length=5,
        original=ELEMENT_HOOK_ORIGINAL, code_offset=CARRIER_OFFSET, code_capacity=0x400,
        purpose='Current Hino accepted elemental consumables suppress paired William weapon VFX only; native element/power/duration remain unchanged',
        asm=VISUAL_GUARD+'nop\n'*(HELPER_OFFSET-len(encoded))+ITEM_HELPER))
    spans = sorted((h['code_offset'], h['code_offset']+h.get('code_capacity', 0x400)) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])) or spans[-1][1] > plan['data_offset']:
        raise ValueError('Talisman code slots overlap existing code or data')
    plan.update(tool_version='0.36', talisman_items_revision=1,
                stage='elemental_talisman_and_shrine_return_pending_gameplay',
                elemental_talismans=True, shrine_return_talisman=True, signpost_talisman=False)
    return plan
