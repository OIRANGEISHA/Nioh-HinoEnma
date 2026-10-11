"""Scene-bound native heavy transition, owned weapon bank and motion read views.

This trial leaves the production payload, actor identity, weapon slots, shared
resources, HP and mission state intact. A validated current scene binding is
required. The game's real heavy input returns the common native transition to
3008; its native queries select armed-weapon action3491. Its native terminal
3000 request resolves to the captured Hino idle. No native action is forced.
"""
from copy import deepcopy

MAGIC = 0x4643524F
BIND_SIZE = 0x100

SAVE = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
push rsi
push rdi
sub rsp, 0x80
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
'''
RESTORE = '''movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x80
pop rdi
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
'''


def player_guard(prefix):
    return f'''mov r11, {{data}}
cmp dword ptr [r11], 0x{MAGIC:X}
jne {prefix}_original
mov r9, {{production_data}}
mov eax, dword ptr [r9+0x1C]
cmp eax, dword ptr [r11+4]
jne {prefix}_original
mov r10, qword ptr [r11+8]
cmp r10, qword ptr [r9+0x10]
jne {prefix}_original
mov rax, {{player_slot}}
cmp r10, qword ptr [rax]
jne {prefix}_original
mov rax, qword ptr [r11+0xA0]
cmp rax, qword ptr [r10]
jne {prefix}_original
cmp dword ptr [r10+0xEF0], 0
jne {prefix}_original
mov rax, qword ptr [r10+0x240]
test rax, rax
je {prefix}_original
cmp qword ptr [rax], r10
jne {prefix}_original
cmp qword ptr [rax+0x20], 0
jle {prefix}_original
mov rax, qword ptr [r10+0x230]
test rax, rax
je {prefix}_original
cmp qword ptr [rax], r10
jne {prefix}_original
mov r8, qword ptr [r11+0x10]
cmp qword ptr [rax+8], r8
jne {prefix}_original
cmp qword ptr [r8+0x50], r10
jne {prefix}_original
'''


def resources_guard(prefix):
    # Read only the bound still-owned loaded package. No resource pointer is
    # accepted from an old report without the installer's live preflight.
    return f'''mov rax, qword ptr [r11+0x28]
mov r9, {{weapon_package_vtable}}
cmp qword ptr [rax], r9
jne {prefix}_original
mov r9, qword ptr [r11+0x30]
cmp qword ptr [rax+0x1B8], r9
jne {prefix}_original
mov rdx, qword ptr [r11+0x38]
cmp qword ptr [r9+0x468], rdx
jne {prefix}_original
mov r9, qword ptr [r11+0x40]
cmp qword ptr [rax+0x188], r9
jne {prefix}_original
mov r9, qword ptr [r11+0x48]
cmp qword ptr [rax+0x190], r9
jne {prefix}_original
mov rax, qword ptr [r11+0x60]
cmp dword ptr [rax], 3008
jne {prefix}_original
cmp byte ptr [rax+0x40], 1
jne {prefix}_original
cmp qword ptr [rax+0x38], rdx
jne {prefix}_original
mov rax, qword ptr [r11+0x68]
cmp dword ptr [rax], 3491
jne {prefix}_original
cmp byte ptr [rax+0x40], 1
jne {prefix}_original
cmp qword ptr [rax+0x38], rdx
jne {prefix}_original
'''


def ready_guard(prefix):
    return f'''mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x640], r9
jne {prefix}_original
mov rax, qword ptr [r11+0x20]
cmp qword ptr [r9], rax
jne {prefix}_original
mov rax, qword ptr [r9+0x230]
test rax, rax
je {prefix}_original
cmp qword ptr [rax], r9
jne {prefix}_original
mov rax, qword ptr [rax+8]
cmp rax, qword ptr [r11+0xA8]
jne {prefix}_original
cmp qword ptr [rax+0x50], r9
jne {prefix}_original
mov rax, qword ptr [rax+0x58]
test rax, rax
je {prefix}_original
cmp dword ptr [rax], 3205
jne {prefix}_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je {prefix}_original
test byte ptr [rax+0x19], 1
je {prefix}_original
'''


def heavy_hook(menu_guard):
    menu = menu_guard.replace('manual_purify', 'oh_menu').replace(
        'oh_menu_block_input', 'oh_original')
    return dict(name='HE_OrochiHeavyTransition', rva=0x73F860, length=5,
        original='48895c2408', code_offset=0, code_capacity=0x1000,
        asm=SAVE + player_guard('oh') + '''cmp rcx, r8
jne oh_original
cmp dword ptr [r11+0x74], 0
jne oh_original
cmp qword ptr [r8+0x58], rdx
jne oh_original
cmp rdx, qword ptr [r11+0x58]
jne oh_original
cmp dword ptr [rdx], 0
jne oh_original
cmp qword ptr [r8+0x5B0], 0
jne oh_original
cmp qword ptr [r8+0x5D8], 0
jne oh_original
cmp qword ptr [r8+0x510], 0
jne oh_original
''' + ready_guard('oh') + resources_guard('oh') + '''mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je oh_original
cmp byte ptr [rax+0x4A], 1
jne oh_original
''' + menu + '''mov r11, {data}
mov rdx, qword ptr [r11+0x50]
cmp qword ptr [rdx], -1
jne oh_original
cmp word ptr [rdx+8], 0xFFFF
jne oh_original
cmp byte ptr [rdx+0xA], 0
jne oh_original
cmp dword ptr [rdx+0xB], 0xFFFF0101
jne oh_original
cmp byte ptr [rdx+0xF], 0
jne oh_original
cmp dword ptr [rdx+0x10], 0
jne oh_original
cmp word ptr [rdx+0x14], 3008
jne oh_original
cmp dword ptr [rdx+0x1C], 0
jne oh_original
cmp dword ptr [rdx+0x2C], -1
jne oh_original
mov rcx, qword ptr [r11+0x10]
call {orochi_native_input}
test al, al
je oh_original
mov r11, {data}
mov dword ptr [r11+0x74], 1
inc dword ptr [r11+0x78]
mov rax, qword ptr [r11+0x50]
mov qword ptr [rsp+0xC8], rax
''' + RESTORE + '''ret
oh_original:
''' + RESTORE + '''mov qword ptr [rsp+8], rbx
jmp {return}
''', purpose='Return the actual common heavy transition only for the bound final-ready Orochi head and idle local Hino; native input, dispatcher and query380/381 remain authoritative')


def bank_hook():
    return dict(name='HE_OrochiWeaponBankRead', rva=0x73FA92, length=7,
        original='488b0cc64885c9', code_offset=0x1000, code_capacity=0x800,
        asm=SAVE + player_guard('ob') + '''cmp dword ptr [r11+0x74], 1
jne ob_original
lea rax, [r8+0x70]
cmp rsi, rax
jne ob_original
test ebx, ebx
jne ob_original
cmp dword ptr [rsp+0xA0], 3000
je ob_finish_idle
cmp dword ptr [rsp+0xA0], 3008
je ob_borrow
cmp dword ptr [rsp+0xA0], 3491
jne ob_original
ob_borrow:
''' + resources_guard('ob') + '''mov rax, qword ptr [r11+0x38]
mov qword ptr [rsp+0xC0], rax
inc dword ptr [r11+0x80]
''' + RESTORE + '''test rcx, rcx
jmp {return}
ob_finish_idle:
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne ob_original
mov qword ptr [rsp+0xA0], 0
mov dword ptr [r11+0x74], 0
inc dword ptr [r11+0x84]
ob_original:
''' + RESTORE + '''mov rcx, qword ptr [rsi+rax*8]
test rcx, rcx
jmp {return}
''', purpose='Borrow only the bound native armed finisher bank as a register read view for3008/3491; resolve its terminal3000 to the real Hino idle without writing controller banks')


def motion_hook():
    return dict(name='HE_OrochiWeaponMotionRead', rva=0x954F0B, length=5,
        original='488b5ccf08', code_offset=0x1800, code_capacity=0x800,
        asm=SAVE + player_guard('om') + '''cmp dword ptr [r11+0x74], 1
jne om_original
mov rax, qword ptr [r10+0x38]
cmp rdi, rax
jne om_original
cmp dword ptr [rsp+0xB8], 1200
jne om_original
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
je om_record_ready
cmp qword ptr [r8+0x60], rax
jne om_original
om_record_ready:
''' + resources_guard('om') + '''mov rcx, qword ptr [rsp+0xC0]
test rcx, rcx
je om_primary
cmp rcx, 4
jne om_original
mov rax, qword ptr [r11+0x48]
jmp om_selected
om_primary:
mov rax, qword ptr [r11+0x40]
om_selected:
mov qword ptr [rsp+0x90], rax
inc dword ptr [r11+0x7C]
''' + RESTORE + '''jmp {return}
om_original:
''' + RESTORE + '''mov rbx, qword ptr [rdi+rcx*8+8]
jmp {return}
''', purpose='Use the matching native weapon motion1200 owners only for the bound Hino finisher layer; no shared motion map or actor slot writes')


def trial_plan(production, module_base, production_allocation, menu_guard):
    plan = {key: deepcopy(production[key]) for key in
            ('schema', 'disk_sha256', 'image_size', 'pe_timestamp_hex', 'product_version')}
    plan.update(tool_version='orochi-scene-trial.1', allocation_size=0x4000,
                data_offset=0x3000, hooks=[heavy_hook(menu_guard), bank_hook(), motion_hook()],
                targets=dict(player_slot=production['targets']['player_slot'],
                    production_data=production_allocation + production['data_offset'] - module_base,
                    weapon_package_vtable=0x12C5510, orochi_native_input=0x721010,
                    native_window_owner=production['targets']['native_window_owner'],
                    tutorial_ui_owner=production['targets']['tutorial_ui_owner']))
    return plan
