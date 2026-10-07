"""Hino-Enma prototype derived from Bryanyora's character-change mechanism.

The original eight hooks have passed the user's first-level replacement test.
The scoped kick-box and current key-door fallbacks passed the user's first-level tests.
"""

DATA_SIZE = 0x1000
BLOCK_SIZE = 0x400

# Data: selected 0x00, resolved 0x04, player pointer 0x10, counters 0x18..0x24,
# input support 0x28/0x29, interaction fallback 0x2A,
# kick-box counter 0x2C, current key-door counter 0x30.
HOOKS = [
    {
        "name": "HE_Preload", "rva": 0x89B424, "length": 12,
        "purpose": "Preload the selected boss alongside William during character resource setup",
        "asm": """
sub rsp, 0x30
mov dword ptr [rsp+0x20], eax
xor r8d, r8d
mov edx, eax
mov ecx, eax
call {preload}
mov qword ptr [rsp+0x28], rax
cmp dword ptr [rsp+0x20], 0x64
jne preload_done
mov r11, {data}
mov dword ptr [r11+0x04], 0
mov ecx, dword ptr [r11]
cmp ecx, 0x58E5E
je preload_selected
cmp ecx, 0x51BE1
jne preload_done
preload_selected:
call {variant}
mov r11, {data}
mov dword ptr [r11+0x04], eax
mov ecx, eax
mov edx, eax
xor r8d, r8d
call {preload}
mov r11, {data}
inc dword ptr [r11+0x18]
preload_done:
mov rax, qword ptr [rsp+0x28]
add rsp, 0x30
jmp {return}
""",
    },
    {
        "name": "HE_Spawn", "rva": 0x8A28FB, "length": 11,
        "purpose": "Use the preloaded boss template with the original player instance number",
        "asm": """
xor r8d, r8d
lea ecx, [rdx+0x63]
mov r11, {data}
cmp dword ptr [r11+0x04], 0
je spawn_original
mov ecx, dword ptr [r11+0x04]
spawn_original:
call {spawn}
mov r11, {data}
mov qword ptr [r11+0x10], rax
inc dword ptr [r11+0x1C]
jmp {return}
""",
    },
    {
        "name": "HE_PlayerInit", "rva": 0x760B33, "length": 5,
        "purpose": "Initialize the player-specific component for the selected boss instance",
        "asm": """
cmp ebx, 0x64
je player_init_yes
push rax
mov rax, {data}
cmp dword ptr [rax+0x04], 0
je player_init_no
cmp ebx, dword ptr [rax+0x04]
jne player_init_no
cmp word ptr [rsi+0x06], 1
jne player_init_no
mov qword ptr [rax+0x10], rsi
inc dword ptr [rax+0x20]
pop rax
jmp player_init_yes
player_init_no:
pop rax
jmp {init_skip}
player_init_yes:
jmp {return}
""",
    },
    {
        "name": "HE_Skin", "rva": 0x7BC3E9, "length": 6,
        "purpose": "Keep the selected boss model from being overridden by William's appearance setting",
        "asm": """
pushfq
push rcx
mov rcx, {data}
cmp dword ptr [rcx+0x04], 0
je skin_original
xor eax, eax
jmp skin_done
skin_original:
mov eax, dword ptr [rbx+0xB5308]
skin_done:
pop rcx
popfq
jmp {return}
""",
    },
    {
        "name": "HE_Equipment", "rva": 0x8A2A31, "length": 7,
        "purpose": "Skip William's weapon-slot setup for the selected boss player",
        "asm": """
push rax
mov rax, {data}
cmp dword ptr [rax+0x04], 0
je equipment_original
cmp rdi, qword ptr [rax+0x10]
jne equipment_original
pop rax
jmp {equipment_skip}
equipment_original:
pop rax
cmp byte ptr [rbx+0x101], 0
jmp {return}
""",
    },
    {
        "name": "HE_EquipmentPrepare", "rva": 0x882639, "length": 7,
        "purpose": "Preserve the old table's special character equipment preparation path",
        "asm": """
push rax
mov rax, {data}
cmp dword ptr [rax+0x04], 0
je equipment_prepare_original
pop rax
jmp {equipment_prepare_next}
equipment_prepare_original:
pop rax
cmp byte ptr [rsi+0x5CD], r14b
jmp {return}
""",
    },
    {
        "name": "HE_InputA", "rva": 0x721044, "length": 5,
        "purpose": "Port optional boss input support, constrained to the captured player instance",
        "asm": """
movsx r8d, byte ptr [rdx+0x0C]
push rax
mov rax, {data}
mov rdx, qword ptr [rbx+0x50]
test rdx, rdx
je input_a_done
cmp dword ptr [rax+0x04], 0
je input_a_done
cmp rdx, qword ptr [rax+0x10]
jne input_a_done
cmp word ptr [rdx+0x06], 1
jne input_a_done
cmp dword ptr [rdx+0xEF0], 0
jne input_a_done
mov rdx, qword ptr [rdx+0xE90]
test rdx, rdx
je input_a_done
test byte ptr [rdx+0x04], 1
jne input_a_done
test byte ptr [rdx+0x04], 2
jne input_a_done
test r10d, r10d
jne input_a_done
cmp r8d, 1
jne input_a_done
cmp byte ptr [rdi+0x0E], 1
jne input_a_done
cmp byte ptr [rdi+0x12], 0
jne input_a_done
inc dword ptr [rax+0x24]
xor edx, edx
cmp byte ptr [rax+0x28], 1
cmove r8d, edx
cmp byte ptr [rdi+0x0D], 6
jne input_a_attack
cmp byte ptr [rax+0x29], 2
je input_a_done
mov edx, 0x2D
cmp ecx, 0
cmove ecx, edx
mov edx, 0x2E
cmp ecx, 1
cmove ecx, edx
jmp input_a_done
input_a_attack:
cmp ecx, 6
jne input_a_done
cmp byte ptr [rax+0x29], 2
je input_a_mode_two
cmp byte ptr [rax+0x29], 1
jne input_a_done
mov edx, 0x0B
jmp input_a_remap
input_a_mode_two:
mov edx, 0x26
input_a_remap:
cmp byte ptr [rdi+0x0D], 0
cmove ecx, edx
cmp byte ptr [rdi+0x0D], 1
cmove ecx, edx
input_a_done:
pop rax
jmp {return}
""",
    },
    {
        "name": "HE_InputB", "rva": 0x721099, "length": 5,
        "purpose": "Port the second input support path for the captured player instance",
        "asm": """
movsx r8d, byte ptr [rdi+0x0E]
push rax
mov rax, {data}
mov rdx, qword ptr [rbx+0x50]
test rdx, rdx
je input_b_done
cmp dword ptr [rax+0x04], 0
je input_b_done
cmp rdx, qword ptr [rax+0x10]
jne input_b_done
cmp word ptr [rdx+0x06], 1
jne input_b_done
cmp dword ptr [rdx+0xEF0], 0
jne input_b_done
mov rdx, qword ptr [rdx+0xE90]
test rdx, rdx
je input_b_done
test byte ptr [rdx+0x04], 1
jne input_b_done
test byte ptr [rdx+0x04], 2
jne input_b_done
test r10d, r10d
jne input_b_done
cmp r8d, 1
jne input_b_done
cmp byte ptr [rdi+0x0C], 1
jne input_b_done
cmp byte ptr [rdi+0x10], 0
jne input_b_done
inc dword ptr [rax+0x24]
xor edx, edx
cmp byte ptr [rax+0x28], 1
cmove r8d, edx
cmp byte ptr [rdi+0x0B], 6
jne input_b_attack
cmp byte ptr [rax+0x29], 2
je input_b_done
mov edx, 0x2D
cmp ecx, 0
cmove ecx, edx
mov edx, 0x2E
cmp ecx, 1
cmove ecx, edx
jmp input_b_done
input_b_attack:
cmp ecx, 6
jne input_b_done
cmp byte ptr [rax+0x29], 2
je input_b_mode_two
cmp byte ptr [rax+0x29], 1
jne input_b_done
mov edx, 0x0B
jmp input_b_remap
input_b_mode_two:
mov edx, 0x26
input_b_remap:
cmp byte ptr [rdi+0x0B], 0
cmove ecx, edx
cmp byte ptr [rdi+0x0B], 1
cmove ecx, edx
input_b_done:
pop rax
jmp {return}
""",
    },
    {
        "name": "HE_Interaction", "rva": 0x751156, "length": 10,
        "purpose": "Use the game's immediate path for the captured Hino-Enma player's type-2 kick-box interaction, or the observed action-0 key door with object id 1 and instance 1",
        "asm": """
push r10
push r11
mov r11, {data}
cmp byte ptr [r11+0x2A], 1
jne kick_box_original
cmp dword ptr [r11+0x04], 0
je kick_box_original
mov r10, qword ptr [rdi+0x50]
test r10, r10
je kick_box_original
cmp r10, qword ptr [r11+0x10]
jne kick_box_original
cmp word ptr [r10+0x06], 1
jne kick_box_original
cmp dword ptr [r10], 0x58E5E
je kick_box_player
cmp dword ptr [r10], 0x51BE1
jne kick_box_original
kick_box_player:
test r8, r8
je kick_box_original
cmp word ptr [r8+0x04], 2
jne kick_box_original
cmp dword ptr [rax+0x48], 6
jne key_door_check
inc dword ptr [r11+0x2C]
jmp interaction_ready
key_door_check:
cmp dword ptr [rax+0x48], 0
jne kick_box_original
cmp dword ptr [r8], 1
jne kick_box_original
cmp word ptr [r8+0x06], 1
jne kick_box_original
inc dword ptr [r11+0x30]
interaction_ready:
pop r11
pop r10
jmp {return}
kick_box_original:
pop r11
pop r10
cmp dword ptr [rax+0x48], -1
jne {interaction_animated}
jmp {return}
""",
    },
]

TARGETS = {
    "variant": 0x8B0560, "preload": 0x8B13E0, "spawn": 0x755160,
    "init_skip": 0x760BAE, "equipment_skip": 0x8A2A9A,
    "equipment_prepare_next": 0x882642,
    "interaction_animated": 0x751242,
    "object_actor_setter": 0x744D50,
    "item_use_ready": 0x75188F,
    "player_slot": 0x18A0490,
    "item_assets": 0x1871720,
    "item_lookup": 0x7324E0,
    "effect_lookup": 0x7656B0,
}

# Separate experiment: start type-2 objects through the native immediate path.
# The original scoped hook above remains the default profile. No hot character
# swapping is attempted. Nondefault ladder-bone configuration is excluded.
# Experimental data: generic count 0x34, last dispatch field 0x38, object id 0x3C.
GENERIC_OBJECT_INTERACTION = {
    "name": "HE_Interaction", "rva": 0x751156, "length": 10,
    "purpose": "Experimental native immediate start for captured Hino-Enma type-2 objects; exclude started requests, negative dispatch fields, and configured ladder bones",
    "asm": """
push r10
push r11
mov r11, {data}
cmp byte ptr [r11+0x2A], 1
je generic_player_check
cmp byte ptr [r11+0x2A], 2
jne generic_original
generic_player_check:
cmp dword ptr [r11+0x04], 0
je generic_original
mov r10, qword ptr [rdi+0x50]
test r10, r10
je generic_original
cmp r10, qword ptr [r11+0x10]
jne generic_original
cmp word ptr [r10+0x06], 1
jne generic_original
cmp dword ptr [r10], 0x58E5E
je generic_object_check
cmp dword ptr [r10], 0x51BE1
jne generic_original
generic_object_check:
test r8, r8
je generic_original
cmp word ptr [r8+0x04], 2
jne generic_original
cmp byte ptr [r11+0x2A], 2
je generic_extended_check
cmp dword ptr [rax+0x48], 6
jne generic_scoped_key
inc dword ptr [r11+0x2C]
jmp generic_ready
generic_scoped_key:
cmp dword ptr [rax+0x48], 0
jne generic_original
cmp dword ptr [r8], 1
jne generic_original
cmp word ptr [r8+0x06], 1
jne generic_original
inc dword ptr [r11+0x30]
jmp generic_ready
generic_extended_check:
cmp byte ptr [rax+0x0A], 0
jne generic_original
cmp dword ptr [rax+0x48], 0
jl generic_original
cmp qword ptr [rax+0x4C], 0
jne generic_original
cmp dword ptr [rax+0x48], 15
jne generic_immediate
cmp dword ptr [r8], 2
je generic_original
generic_immediate:
inc dword ptr [r11+0x34]
mov r10d, dword ptr [rax+0x48]
mov dword ptr [r11+0x38], r10d
mov r10d, dword ptr [r8]
mov dword ptr [r11+0x3C], r10d
generic_ready:
pop r11
pop r10
jmp {return}
generic_original:
pop r11
pop r10
cmp dword ptr [rax+0x48], -1
jne {interaction_animated}
jmp {return}
""",
}

QUEUED_DOOR_INTERACTION = {
    "name": "HE_QueuedDoor", "rva": 0x75129F, "length": 11,
    "purpose": "Keep the native queued reference for type-2 object 2 dispatch 15 doors, then reproduce the native start event for the captured Hino-Enma player",
    "asm": """
mov qword ptr [rdi+0x530], -1
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
pushfq
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne queued_door_done
cmp dword ptr [r11+0x04], 0
je queued_door_done
mov rdx, qword ptr [rdi+0x50]
test rdx, rdx
je queued_door_done
cmp rdx, qword ptr [r11+0x10]
jne queued_door_done
cmp word ptr [rdx+0x06], 1
jne queued_door_done
cmp dword ptr [rdx], 0x58E5E
je queued_door_object
cmp dword ptr [rdx], 0x51BE1
jne queued_door_done
queued_door_object:
mov rcx, qword ptr [rdi+0x510]
test rcx, rcx
je queued_door_done
cmp word ptr [rcx+0x04], 2
jne queued_door_done
cmp dword ptr [rcx], 2
jne queued_door_done
mov r10, qword ptr [rdi+0x528]
test r10, r10
je queued_door_done
cmp qword ptr [r10], rcx
jne queued_door_done
cmp word ptr [r10+0x08], 0x0101
jne queued_door_done
cmp byte ptr [r10+0x0A], 0
jne queued_door_done
cmp dword ptr [r10+0x48], 15
jne queued_door_done
cmp qword ptr [r10+0x4C], 0
jne queued_door_done
sub rsp, 0x80
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov byte ptr [r10+0x0A], 1
call {object_actor_setter}
mov r11, {data}
inc dword ptr [r11+0x40]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x80
queued_door_done:
popfq
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
jmp {return}
""",
}

# The old table's YoukaiCamera_A read corresponds to this verified new-version
# action flag query. The next native instruction tests only bit 0 of the shifted
# value. Suppress that bit for the captured player; preserve every other bit,
# register and the original SHR flags. Shared action parameters are never edited.
# Experimental data: suppressed action-camera queries 0x44.
PLAYER_ACTION_CAMERA = {
    "name": "HE_ActionCamera", "rva": 0x855FF7, "length": 6,
    "purpose": "Port the old yokai camera bypass for the captured Hino-Enma player; prevent action-driven downward camera steering",
    "asm": """
mov eax, dword ptr [rcx]
shr rax, 0x0A
pushfq
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0x04], 0
je action_camera_done
cmp rdx, qword ptr [r11+0x10]
jne action_camera_done
test rdx, rdx
je action_camera_done
cmp word ptr [rdx+0x06], 1
jne action_camera_done
cmp dword ptr [rdx], 0x58E5E
je action_camera_role
cmp dword ptr [rdx], 0x51BE1
jne action_camera_done
action_camera_role:
cmp dword ptr [rdx+0xEF0], 0
jne action_camera_done
mov r10, qword ptr [rdx+0xE90]
test r10, r10
je action_camera_done
cmp dword ptr [r10+0x0C], 1
jne action_camera_done
test al, 1
je action_camera_done
and eax, 0xFFFFFFFE
inc dword ptr [r11+0x44]
action_camera_done:
pop r11
pop r10
popfq
jmp {return}
""",
}

# The user's confirmed bag request identified Himorogi Fragment as item 0x1817,
# category 1, effect 0x92/type 12. The native update cancels its accepted request
# at 0x75185D when the boss has no William item animation. Continue through the
# existing cooldown/status checks, effect dispatch and inventory commit instead.
# No item, inventory, shared action definition or mission state is written here.
# Experimental data: accepted fragment animation fallbacks 0x48.
PLAYER_HIMOROGI_FRAGMENT = {
    "name": "HE_HimorogiFragment", "rva": 0x75185D, "length": 5,
    "purpose": "Allow only the captured Hino-Enma player's accepted Himorogi Fragment request to reach the native item effect and commit path without William's missing use animation",
    "asm": """
test r14b, r14b
jne {item_use_ready}
pushfq
push rax
push r10
push r11
mov r11, {data}
cmp dword ptr [r11+0x04], 0
je fragment_original
mov r10, qword ptr [rdi+0x50]
test r10, r10
je fragment_original
cmp r10, qword ptr [r11+0x10]
jne fragment_original
mov rax, {player_slot}
cmp r10, qword ptr [rax]
jne fragment_original
cmp word ptr [r10+0x06], 1
jne fragment_original
cmp dword ptr [r10], 0x58E5E
je fragment_role
cmp dword ptr [r10], 0x51BE1
jne fragment_original
fragment_role:
cmp dword ptr [r10+0xEF0], 0
jne fragment_original
mov rax, qword ptr [r10+0xE90]
test rax, rax
je fragment_original
cmp dword ptr [rax+0x0C], 1
jne fragment_original
cmp byte ptr [rdi+0x555], 1
jne fragment_original
cmp dword ptr [rdi+0x548], 0x1817
jne fragment_original
cmp dword ptr [rdi+0x54C], 1
jne fragment_original
cmp dword ptr [rdi+0x550], 1
jne fragment_original
cmp byte ptr [rdi+0x554], 0
jne fragment_original
inc dword ptr [r11+0x48]
pop r11
pop r10
pop rax
popfq
jmp {item_use_ready}
fragment_original:
pop r11
pop r10
pop rax
popfq
jmp {return}
""",
}

# The observed Kodama request uses dispatch 36. Its script checks the native
# current-interaction reference (Interaction::IsPlayerInteraction), so the
# immediate type-2 path alone cannot finish it. Preserve the native queued
# reference and supply the same start event and actor setter as that path.
# Only a completed, selected type-2 request for the current Hino-Enma qualifies.
# Experimental data: Kodama queued-start fallbacks 0x4C.
PLAYER_KODAMA_INTERACTION = {
    "name": "HE_Kodama", "rva": 0x751160, "length": 10,
    "purpose": "Keep the native queued interaction reference for the captured Hino-Enma player's completed dispatch-36 Kodama request and emit its native start event",
    "asm": """
mov rax, r13
test r8, r8
cmovne rax, rdx
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
pushfq
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne kodama_original
cmp dword ptr [r11+0x04], 0
je kodama_original
mov r10, qword ptr [rdi+0x50]
test r10, r10
je kodama_original
cmp r10, qword ptr [r11+0x10]
jne kodama_original
mov rcx, {player_slot}
cmp r10, qword ptr [rcx]
jne kodama_original
cmp word ptr [r10+0x06], 1
jne kodama_original
cmp dword ptr [r10], 0x58E5E
je kodama_player
cmp dword ptr [r10], 0x51BE1
jne kodama_original
kodama_player:
cmp dword ptr [r10+0xEF0], 0
jne kodama_original
mov rcx, qword ptr [r10+0xE90]
test rcx, rcx
je kodama_original
cmp dword ptr [rcx+0x0C], 1
jne kodama_original
test r8, r8
je kodama_original
test rax, rax
je kodama_original
cmp word ptr [r8+0x04], 2
jne kodama_original
cmp qword ptr [rax], r8
jne kodama_original
cmp word ptr [rax+0x08], 0x0101
jne kodama_original
cmp byte ptr [rax+0x0A], 0
jne kodama_original
cmp dword ptr [rax+0x48], 36
jne kodama_original
cmp qword ptr [rax+0x4C], 0
jne kodama_original
cmp byte ptr [rdi+0x4E9], 1
jne kodama_original
sub rsp, 0x80
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov byte ptr [rax+0x0A], 1
mov rcx, r8
mov rdx, r10
call {object_actor_setter}
mov r11, {data}
inc dword ptr [r11+0x4C]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x80
popfq
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
jmp {interaction_animated}
kodama_original:
popfq
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
jmp {return}
""",
}

# Native A83AD0 handlers for these types restore HP, remove status ailments or
# apply a status to the recipient's +0x240 component. This deliberately omits
# currency, mission warps, projectiles and weapon setup. Names are not inferred
# from numeric IDs. The current native catalogue contains 17 matching items.
SELF_RECOVERY_EFFECT_TYPES = (1, 2, 23, 31, 32, 33, 34, 37, 42, 49, 54, 55, 61, 62, 71, 226)
SELF_RECOVERY_CATEGORIES = (1, 2, 3)

_CONSUMABLE_RESTORE = """
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x90
pop rsi
pop rbx
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
"""

# Append after the existing Fragment gate. Native ready/category-0 routes are
# unchanged. Only accepted, single-use, ordinary self consumables qualify;
# lookup and validate all three effects through the game's own definition API.
# The original eligibility, cooldown, effect and inventory-commit functions run
# unchanged. Data +0x50 counts fallbacks; +0x54 records the last accepted item.
PLAYER_SELF_CONSUMABLES = {
    "name": "HE_Consumables", "rva": 0x751862, "length": 9,
    "purpose": "Continue accepted ordinary recovery and self-buff consumables through native effects and inventory commit when Hino-Enma lacks William's use animation",
    "asm": """
cmp dword ptr [rdi+0x54C], 0
je {item_use_ready}
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
push rsi
sub rsp, 0x90
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov byte ptr [rsp+0x80], 0
mov r11, {data}
cmp dword ptr [r11+0x04], 0
je consumable_original
mov r10, qword ptr [rdi+0x50]
test r10, r10
je consumable_original
cmp r10, qword ptr [r11+0x10]
jne consumable_original
mov rax, {player_slot}
cmp r10, qword ptr [rax]
jne consumable_original
cmp word ptr [r10+0x06], 1
jne consumable_original
cmp dword ptr [r10], 0x58E5E
je consumable_role
cmp dword ptr [r10], 0x51BE1
jne consumable_original
consumable_role:
cmp dword ptr [r10+0xEF0], 0
jne consumable_original
mov rax, qword ptr [r10+0xE90]
test rax, rax
je consumable_original
cmp dword ptr [rax+0x0C], 1
jne consumable_original
cmp byte ptr [rdi+0x555], 1
jne consumable_original
cmp dword ptr [rdi+0x548], 0
jl consumable_original
cmp dword ptr [rdi+0x550], 1
jne consumable_original
cmp byte ptr [rdi+0x554], 0
jne consumable_original
mov eax, dword ptr [rdi+0x54C]
sub eax, 1
cmp eax, 2
ja consumable_original
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je consumable_original
mov rcx, qword ptr [rcx+0x20]
test rcx, rcx
je consumable_original
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je consumable_original
mov edx, dword ptr [rdi+0x548]
call {item_lookup}
test rax, rax
je consumable_original
mov ecx, dword ptr [rdi+0x548]
cmp dword ptr [rax], ecx
jne consumable_original
cmp word ptr [rax+0x04], 1
jne consumable_original
test byte ptr [rax+0x104], 1
je consumable_original
mov ecx, dword ptr [rdi+0x54C]
cmp dword ptr [rax+0x10C], ecx
jne consumable_original
mov rsi, rax
xor ebx, ebx
consumable_effect:
mov edx, dword ptr [rsi+rbx*4+0x110]
test edx, edx
je consumable_next
mov dword ptr [rsp+0x84], edx
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je consumable_original
mov rcx, qword ptr [rcx+0x148]
test rcx, rcx
je consumable_original
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je consumable_original
call {effect_lookup}
test rax, rax
je consumable_original
mov ecx, dword ptr [rsp+0x84]
cmp dword ptr [rax], ecx
jne consumable_original
mov ecx, dword ptr [rax+0x04]
cmp ecx, 64
jae consumable_high_type
mov rdx, SELF_EFFECT_MASK
bt rdx, rcx
jnc consumable_original
jmp consumable_approved
consumable_high_type:
cmp ecx, 71
je consumable_approved
cmp ecx, 226
jne consumable_original
consumable_approved:
mov byte ptr [rsp+0x80], 1
consumable_next:
inc ebx
cmp ebx, 3
jb consumable_effect
cmp byte ptr [rsp+0x80], 1
jne consumable_original
mov r11, {data}
inc dword ptr [r11+0x50]
mov eax, dword ptr [rdi+0x548]
mov dword ptr [r11+0x54], eax
""".replace("SELF_EFFECT_MASK", hex(sum(1 << t for t in SELF_RECOVERY_EFFECT_TYPES if t < 64)))
    + _CONSUMABLE_RESTORE + "jmp {item_use_ready}\nconsumable_original:\n"
    + _CONSUMABLE_RESTORE + "jmp {return}\n",
}

EXPERIMENTAL_HOOKS = [
    dict(GENERIC_OBJECT_INTERACTION if hook["name"] == "HE_Interaction" else hook)
    for hook in HOOKS
] + [QUEUED_DOOR_INTERACTION, PLAYER_ACTION_CAMERA, PLAYER_HIMOROGI_FRAGMENT, PLAYER_KODAMA_INTERACTION, PLAYER_SELF_CONSUMABLES]
