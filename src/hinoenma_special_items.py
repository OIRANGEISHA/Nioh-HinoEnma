"""Eight finite item routes, retaining native eligibility/effects/consumption.

Six generated-item actions are supplied by special_item_actions. The two
ordinary items below retain 767080 -> A83AD0 -> 763410; no warp, lost-flag,
guardian-mode, inventory, mission, health or resource field is written here.
"""
from copy import deepcopy

EFFECT_HELPER_OFFSET = 0x12B00
EFFECT_HELPER_CAPACITY = 0x300
EFFECT_TARGETS = {'special_item_saved_manager': 0x189F408,
                  'special_item_guardian_pool_slot': 0x2C5A260}
EFFECT_SIGNATURE_SPANS = (
    ('special_item_native_effect_then_commit', 0x75188F, 0xB7),
    ('special_item_native_request_reset', 0x751951, 0x40),
    ('special_item_guardian_pool_getter', 0xFA6FF0, 0xD),
    ('special_item_himorogi_wood_factory', 0xA849DB, 0xB7),
    ('special_item_candle_factory', 0xA8559E, 0x81),
    ('special_item_bowl_opcode14_shared',0x708D51,0x1C),
    ('special_item_bowl_opcode14_mode',0x708D72,0x1C),
    ('special_item_bowl_opcode18',0x708D93,0x10),
    ('special_item_bowl_opcode32',0x709282,0x29),
    ('special_item_bowl_attach',0x724790,0x43E),
    ('special_item_bowl_release',0x726040,0xD3),
    ('special_item_bowl_spawn',0x724DE0,0x2C9),
)

EFFECT_HELPER_ASM = '''special_item_effect_helper:
push rcx
push rdx
push r10
push r11
cmp ecx, 13
je special_item_effect_wood
cmp ecx, 30
jne special_item_effect_no
cmp dword ptr [rdi+0x548], 33287
jne special_item_effect_no
cmp dword ptr [rsi], 33287
jne special_item_effect_no
cmp dword ptr [rsi+0x114], 5779
jne special_item_effect_no
cmp edx, 5779
jne special_item_effect_no
jmp special_item_effect_shared
special_item_effect_wood:
cmp dword ptr [rdi+0x548], 46858
jne special_item_effect_no
cmp dword ptr [rsi], 46858
jne special_item_effect_no
cmp dword ptr [rsi+0x114], 60833
jne special_item_effect_no
cmp edx, 60833
jne special_item_effect_no
special_item_effect_shared:
cmp dword ptr [rdi+0x54C], 1
jne special_item_effect_no
cmp dword ptr [rsi+0x10C], 1
jne special_item_effect_no
cmp word ptr [rsi+4], 1
jne special_item_effect_no
test byte ptr [rsi+0x104], 1
je special_item_effect_no
cmp dword ptr [rsi+0x110], 0
jne special_item_effect_no
cmp dword ptr [rsi+0x118], 0
jne special_item_effect_no
cmp dword ptr [rsi+0x11C], 0
jne special_item_effect_no
cmp dword ptr [rdi+0x550], 1
jne special_item_effect_no
cmp word ptr [rdi+0x554], 0x100
jne special_item_effect_no
cmp word ptr [rdi+0x556], 0
jne special_item_effect_no
mov r10, qword ptr [rdi+0x50]
test r10, r10
je special_item_effect_no
cmp dword ptr [r10+4], 0x10000
jne special_item_effect_no
mov r11, {data}
cmp qword ptr [r11+0x10], r10
jne special_item_effect_no
mov edx, dword ptr [r10]
cmp edx, dword ptr [r11+4]
jne special_item_effect_no
cmp edx, 0x58E5E
je special_item_effect_owner
cmp edx, 0x51BE1
jne special_item_effect_no
special_item_effect_owner:
mov r11, {player_slot}
cmp qword ptr [r11], r10
jne special_item_effect_no
cmp dword ptr [r10+0xEF0], 0
jne special_item_effect_no
mov r11, qword ptr [r10+0xE90]
test r11, r11
je special_item_effect_no
cmp dword ptr [r11], edx
jne special_item_effect_no
cmp dword ptr [r11+0xC], 1
jne special_item_effect_no
mov r11, qword ptr [r10+0x230]
test r11, r11
je special_item_effect_no
cmp qword ptr [r11], r10
jne special_item_effect_no
cmp qword ptr [r11+8], rdi
jne special_item_effect_no
mov r11, qword ptr [r10+0x240]
test r11, r11
je special_item_effect_no
cmp qword ptr [r11], r10
jne special_item_effect_no
cmp qword ptr [r11+0x108], r10
jne special_item_effect_no
cmp qword ptr [r11+0x20], 0
jle special_item_effect_no
cmp ecx, 13
je special_item_effect_yes
mov r11, {special_item_saved_manager}
mov r11, qword ptr [r11]
test r11, r11
je special_item_effect_no
cmp byte ptr [r11+0x74], 0
je special_item_effect_no
mov r11, qword ptr [r10+0x2C0]
test r11, r11
je special_item_effect_no
test r11, 0xF
jne special_item_effect_no
mov rdx, {native_guardian_vtable}
cmp qword ptr [r11], rdx
jne special_item_effect_no
cmp qword ptr [r11+0x10], r10
jne special_item_effect_no
mov rdx, {special_item_guardian_pool_slot}
mov rdx, qword ptr [rdx]
test rdx, rdx
je special_item_effect_no
lea rdx, [rdx+0x1D0]
test rdx, rdx
je special_item_effect_no
cmp qword ptr [r10+0x2C8], rdx
jne special_item_effect_no
special_item_effect_yes:
mov eax, 1
jmp special_item_effect_restore
special_item_effect_no:
xor eax, eax
special_item_effect_restore:
pop r11
pop r10
pop rdx
pop rcx
ret
'''

def apply_special_items(previous):
    from hinoenma_special_item_actions import apply_special_item_actions
    seed = deepcopy(previous)
    seed['targets'].update(EFFECT_TARGETS)
    plan = apply_special_item_actions(seed, effect_helper=EFFECT_HELPER_ASM)
    plan['targets'].update(EFFECT_TARGETS)
    hook = plan['hooks'][13]
    marker = 'consumable_regular_effect:\ncmp ecx, 64\n'
    if hook['name'] != 'HE_Consumables' or hook['code_offset'] != 0x3400 or hook['asm'].count(marker) != 1:
        raise ValueError('Frozen consumable effect guard differs')
    hook['asm'] = hook['asm'].replace(marker, '''consumable_regular_effect:
mov edx, dword ptr [rsp+0x84]
call {data} + 0x3B00
test al, al
jne consumable_approved
cmp ecx, 64
''')
    hook['purpose'] += '; exact accepted Himorogi Branch and owned lost-guardian Summoner Candle use native factories and native inventory commit'
    plan.update(tool_version='0.52',special_items_revision=1,
        special_item_ids=[12084,50129,7739,7696,22295,49379,46858,33287],
        special_items_gameplay_confirmation_pending=True)
    return plan
