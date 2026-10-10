"""Uninstalled, appearance-only map preview supplement.

Suppress one visual gear binder only for the current native map placeholder
whose body is the selected Hino package and whose private construction ticket
has completed. All saved equipment, stats, actor flags, body and motion data
are read-only. Two scoped hooks retain Hino's native motion bank and select
its native idle resources. The renderer still needs to validate the animation.
"""
from __future__ import annotations

from menu_preview_preload_hooks import _pointer

ALLOCATION_SIZE, DATA_OFFSET = 0x5000, 0x4000
HOOK_RVA, ORIGINAL = 0x7C8302, 'E8 69 88 FE FF'
IDLE_RVA, IDLE_ORIGINAL = 0x9530BA, '48 8B 47 20 48 89 43 28'
IDLE_SELECT_RVA, IDLE_SELECT_ORIGINAL = 0x70ED46, '8B 56 68 8B CA'
LOADOUT_RVA, LOADOUT_ORIGINAL = 0x75724F, 'E8 1C 99 05 00'
HOOKS = (('HE_MapAppearancePrivate', HOOK_RVA, ORIGINAL, 0),
         ('HE_MapNativeIdlePrivate', IDLE_RVA, IDLE_ORIGINAL, 0x1000),
         ('HE_MapIdleSelectionPrivate', IDLE_SELECT_RVA, IDLE_SELECT_ORIGINAL, 0x2000),
         ('HE_MapLoadoutAppearancePrivate', LOADOUT_RVA, LOADOUT_ORIGINAL, 0x3000))
TARGET_RVAS = dict(base_mode_vtable=0x11FB588, player_slot=0x18A0490,
    package_ids=0x1766128, package_handles=0x1766110,
    package_get=0xF90760, package_handle=0xF90930, gear_binder=0x7B0B70,
    initial_stats_return=0x8C5493, motion_inner_return=0x9512E0,
    motion_ctor_return=0x760758, ctor_return=0x75525E,
    idle_selection_return=0x7060AD, map_idle_return=0x8C5454)
NATIVE_SPANS = ((0x7C82F8, 0x29), (0x7B0B70, 0x9A8),
                (0xF90760, 0x57), (0xF90930, 0x4A), (0x7C7EB0, 0x13),
                (0x8C5487, 0xC), (0x952F20, 0x1A2), (0x951270, 0x93),
                (0x760745, 0x13), (0x706070, 0x4B), (0x70ECE0, 0xFA),
                (0x8C5442, 0x12), (0x964216, 0x29), (0x9693B0, 8),
                (0x7571C0, 0xBB), (0xAF3F32, 0x54), (0x7B16B3, 0x622))
# Own private data: D0 entries,D4 suppressed,D8 native calls;
# Q10 last suppressed actor,Q18 last suppressed package body;
# D20 scoped native motion banks retained,D24 native bank overrides replayed.
# D28 scoped native idle resource selections,D2C original selections replayed.
# D30 loadout binder entries,D34 suppressed,D38 native calls.
# The frozen visual ticket is only read: Q0 owner,D8 selected,D14 status7,
# D20 lock0,D28 prepared>0,D2C swaps>0 == D30 restores,D38 epoch observed1.


def _save():
    return '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xA0
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
mov dword ptr [rsp+0x8C], 0
'''


def _restore():
    return '''movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0xA0
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''


def _ticket(*, recheck=False):
    source = '''mov r11, {visual_data}
mov rax, qword ptr [r11]
'''
    if recheck:
        source += '''cmp rax, qword ptr [rsp+0x98]
jne appearance_done
'''
    source += _pointer('rax', 'appearance_done') + '''mov rcx, {base_mode_vtable}
cmp qword ptr [rax], rcx
jne appearance_done
cmp dword ptr [rax+0x1C], 0
je APPEARANCE_INITIAL
cmp dword ptr [rax+0x1C], 1
jne appearance_done
cmp dword ptr [r11+0x38], 1
jne appearance_done
jmp APPEARANCE_OWNER_READY
APPEARANCE_INITIAL:
mov rcx, {initial_stats_return}
cmp qword ptr [rsp+0x228], rcx
jne appearance_done
APPEARANCE_OWNER_READY:
cmp dword ptr [r11+0x14], 7
jne appearance_done
cmp dword ptr [r11+0x20], 0
jne appearance_done
cmp dword ptr [r11+0x28], 0
je appearance_done
mov ecx, dword ptr [r11+0x2C]
test ecx, ecx
je appearance_done
cmp dword ptr [r11+0x30], ecx
jne appearance_done
mov ecx, dword ptr [rsp+0x88]
cmp dword ptr [r11+8], ecx
jne appearance_done
mov r10, {production_data}
cmp dword ptr [r10], ecx
jne appearance_done
'''
    source = source.replace('APPEARANCE_INITIAL', 'appearance_initial_recheck' if recheck else 'appearance_initial')
    source = source.replace('APPEARANCE_OWNER_READY', 'appearance_owner_recheck' if recheck else 'appearance_owner_ready')
    if not recheck:
        source += 'mov qword ptr [rsp+0x98], rax\n'
    return source


def appearance_asm():
    source = _save() + '''mov r11, {data}
inc dword ptr [r11]
'''
    source += _pointer('rsi', 'appearance_done')
    source += _pointer('rdx', 'appearance_done') + '''cmp rdx, r14
jne appearance_done
lea rax, [rsi+0x128]
cmp rcx, rax
jne appearance_done
cmp qword ptr [rsi], rdx
jne appearance_done
cmp qword ptr [rdx+0x240], rsi
jne appearance_done
cmp dword ptr [rdx], 100
jne appearance_done
cmp dword ptr [rdx+4], 0x10000
jne appearance_done
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne appearance_done
mov qword ptr [rsp+0x90], rdx
mov rax, {production_data}
mov eax, dword ptr [rax]
cmp eax, 0x58E5E
je appearance_selected
cmp eax, 0x51BE1
jne appearance_done
appearance_selected:
mov dword ptr [rsp+0x88], eax
'''
    source += _ticket() + '''mov rdx, qword ptr [rsp+0x90]
mov rax, qword ptr [rdx+0x18]
'''
    source += _pointer('rax', 'appearance_done') + '''cmp qword ptr [rax], rdx
jne appearance_done
mov rcx, qword ptr [rax+0x188]
'''
    source += _pointer('rcx', 'appearance_done') + '''mov qword ptr [rsp+0x80], rcx
mov rax, {package_ids}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'appearance_done') + '''mov rax, qword ptr [rcx+0x10]
'''
    source += _pointer('rax', 'appearance_done') + '''mov rax, qword ptr [rax+8]
'''
    source += _pointer('rax', 'appearance_done') + '''mov edx, dword ptr [rsp+0x88]
xor r8d, r8d
call {package_get}
cmp dword ptr [rsp+0x88], 0x58E5E
jne appearance_variant
cmp eax, 232
jne appearance_done
jmp appearance_package_ok
appearance_variant:
cmp eax, 233
jne appearance_done
appearance_package_ok:
mov edx, eax
mov rax, {package_handles}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'appearance_done') + '''mov rax, qword ptr [rcx]
'''
    source += _pointer('rax', 'appearance_done') + '''mov rax, qword ptr [rax+8]
'''
    source += _pointer('rax', 'appearance_done') + '''xor r8d, r8d
call {package_handle}
'''
    source += _pointer('rax', 'appearance_done') + '''cmp byte ptr [rax+0x160], 0
je appearance_done
mov rax, qword ptr [rax+8]
cmp qword ptr [rsp+0x80], rax
jne appearance_done
'''
    # Loading helpers may interleave with a native map transition. Revalidate
    # the exact ticket epoch and actor/body pair before suppressing anything.
    source += _ticket(recheck=True) + '''mov rdx, qword ptr [rsp+0x90]
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne appearance_done
cmp qword ptr [rdx+0x240], rsi
jne appearance_done
mov rax, qword ptr [rdx+0x18]
'''
    source += _pointer('rax', 'appearance_done') + '''cmp qword ptr [rax], rdx
jne appearance_done
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x188], rcx
jne appearance_done
mov r11, {data}
inc dword ptr [r11+4]
mov qword ptr [r11+0x10], rdx
mov qword ptr [r11+0x18], rcx
mov dword ptr [rsp+0x8C], 1
appearance_done:
cmp dword ptr [rsp+0x8C], 0
jne appearance_skip
mov r11, {data}
inc dword ptr [r11+8]
'''
    source += _restore() + '''call {gear_binder}
jmp {return}
appearance_skip:
'''
    return source + _restore() + 'jmp {return}\n'


def loadout_appearance_asm():
    """Keep the saved equipment copy, suppress only its visual application.

7571C0 obtains the native player slot then copies eleven equipped records.
Its call75724F uses RSI=RDX=actor and RBP=RCX=stats+128, unlike the stats
refresh site's RSI=stats/R14=actor. Only a completed state1 map can skip it.
"""
    source = appearance_asm()
    begin = source.index(_pointer('rsi', 'appearance_done'))
    end = source.index('mov qword ptr [rsp+0x90], rdx\n',begin)
    guard = _pointer('rdx','appearance_done') + '''cmp rdx, rsi
jne appearance_done
cmp rcx, rbp
jne appearance_done
mov r11, qword ptr [rdx+0x240]
'''
    guard += _pointer('r11','appearance_done') + '''cmp qword ptr [r11], rdx
jne appearance_done
lea rax, [r11+0x128]
cmp rcx, rax
jne appearance_done
cmp dword ptr [rdx], 100
jne appearance_done
cmp dword ptr [rdx+4], 0x10000
jne appearance_done
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne appearance_done
'''
    source = source[:begin] + guard + source[end:]
    old = 'cmp qword ptr [rdx+0x240], rsi\njne appearance_done\n'
    recheck = '''mov rax, qword ptr [rdx+0x240]
'''+_pointer('rax','appearance_done')+'''cmp qword ptr [rax], rdx
jne appearance_done
lea rax, [rax+0x128]
cmp rax, rbp
jne appearance_done
'''
    if source.count(old) != 1: raise ValueError('Loadout recheck source boundary changed')
    source = source.replace(old,recheck)
    source = source.replace('je appearance_initial\n','je appearance_done\n')
    source = source.replace('je appearance_initial_recheck\n','je appearance_done\n')
    source = source.replace('inc dword ptr [r11]\n',
                            'inc dword ptr [r11]\ninc dword ptr [r11+0x30]\n')
    source = source.replace('inc dword ptr [r11+4]\n',
                            'inc dword ptr [r11+4]\ninc dword ptr [r11+0x34]\n')
    source = source.replace('inc dword ptr [r11+8]\n',
                            'inc dword ptr [r11+8]\ninc dword ptr [r11+0x38]\n')
    return source


def idle_asm():
    """Retain the bank already initialized from Hino's motion package.

Native loader 952F20 installs package+18 into motion+28, then overwrites it
with common human bank9. Only that final store is skipped in a proved map
construction ancestry. The native load's RAX and all flags remain identical.
"""
    source = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
lea r11, [rsp+0x40]
mov rax, {motion_inner_return}
cmp qword ptr [r11+0x28], rax
jne idle_native
mov rax, {motion_ctor_return}
cmp qword ptr [r11+0x68], rax
jne idle_native
mov rax, {ctor_return}
cmp qword ptr [r11+0x138], rax
jne idle_native
mov rax, {wrapper_continuation}
cmp qword ptr [r11+0x1A8], rax
jne idle_native
lea rax, [r11+0xE1]
cmp qword ptr [r11+0x78], rax
jne idle_native
cmp dword ptr [r11+0x1D0], 2
jne idle_native
cmp qword ptr [r11+0x1E8], rsi
jne idle_native
cmp qword ptr [r11+0x1E0], r13
jne idle_native
'''
    source += _pointer('rsi', 'idle_native') + _pointer('rbx', 'idle_native')
    source += _pointer('r13', 'idle_native') + '''cmp dword ptr [rsi], 100
jne idle_native
cmp dword ptr [rsi+4], 0x10000
jne idle_native
cmp byte ptr [rsi+0x434], 0
jne idle_native
cmp byte ptr [rsi+0x435], 0
jne idle_native
cmp qword ptr [rbx], rsi
jne idle_native
cmp byte ptr [r13+0x160], 0
je idle_native
mov rcx, qword ptr [r13+0x18]
'''
    source += _pointer('rcx', 'idle_native') + '''cmp qword ptr [rbx+0x28], rcx
jne idle_native
mov rax, qword ptr [rsi+0x18]
'''
    source += _pointer('rax', 'idle_native') + '''cmp qword ptr [rax], rsi
jne idle_native
mov rcx, qword ptr [r13+8]
'''
    source += _pointer('rcx', 'idle_native') + '''cmp qword ptr [rax+0x188], rcx
jne idle_native
mov rax, qword ptr [r11+0x1D8]
'''
    source += _pointer('rax', 'idle_native') + '''mov rcx, {base_mode_vtable}
cmp qword ptr [rax], rcx
jne idle_native
cmp dword ptr [rax+0x1C], 0
jne idle_native
mov r8, {visual_data}
cmp qword ptr [r8], rax
jne idle_native
cmp dword ptr [r8+0x14], 7
jne idle_native
cmp dword ptr [r8+0x28], 0
je idle_native
mov ecx, dword ptr [r11+0x1F8]
cmp ecx, 0x58E5E
je idle_selected
cmp ecx, 0x51BE1
jne idle_native
idle_selected:
cmp dword ptr [r8+8], ecx
jne idle_native
mov rax, {production_data}
cmp dword ptr [rax], ecx
jne idle_native
mov rax, {data}
inc dword ptr [rax+0x20]
'''
    pops = '''pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''
    source += pops + '''mov rax, qword ptr [rdi+0x20]
jmp {return}
idle_native:
mov rax, {data}
inc dword ptr [rax+0x24]
'''
    return source + pops + '''mov rax, qword ptr [rdi+0x20]
mov qword ptr [rbx+0x28], rax
jmp {return}
'''


def _idle_selection_ticket():
    return '''mov rax, {visual_data}
mov rcx, qword ptr [rsp+0x98]
cmp qword ptr [rax], rcx
jne idle_select_done
mov rdx, {base_mode_vtable}
cmp qword ptr [rcx], rdx
jne idle_select_done
cmp dword ptr [rcx+0x1C], 0
je IDLE_TICKET_READY
cmp dword ptr [rcx+0x1C], 1
jne idle_select_done
cmp dword ptr [rax+0x38], 1
jne idle_select_done
IDLE_TICKET_READY:
cmp dword ptr [rax+0x14], 7
jne idle_select_done
cmp dword ptr [rax+0x20], 0
jne idle_select_done
cmp dword ptr [rax+0x28], 0
je idle_select_done
mov edx, dword ptr [rax+0x2C]
test edx, edx
je idle_select_done
cmp dword ptr [rax+0x30], edx
jne idle_select_done
mov ecx, dword ptr [rsp+0x88]
cmp dword ptr [rax+8], ecx
jne idle_select_done
mov rax, {production_data}
cmp dword ptr [rax], ecx
jne idle_select_done
'''


def _idle_selection_record():
    source = _pointer('r8', 'idle_select_done') + '''cmp qword ptr [rsi+0x58], r8
jne idle_select_done
cmp byte ptr [r8+0x40], 0
je idle_select_done
cmp dword ptr [r8], 0
jne idle_select_done
mov rax, qword ptr [rsi+0x80]
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp qword ptr [r8+0x38], rax
jne idle_select_done
mov rax, qword ptr [r8+0x20]
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp dword ptr [rax+0x20], 0
jne idle_select_done
test byte ptr [rax], 0x10
jne idle_select_done
cmp dword ptr [rsi+0x68], 2
jne idle_select_done
'''
    return source


def idle_selection_asm():
    """Select native Hino resource bank0 only for BaseMode's initial idle.

Runtime action bank1 is translated by the original code into resource bank0
for motion/action/timing. Controller bank2 and its enabled action0 record
stay native; only the two input registers to this native selection change.
"""
    source = _save() + '''mov qword ptr [rsp+0x90], rax
test r15d, r15d
jne idle_select_done
mov rax, {visual_data}
mov rax, qword ptr [rax]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov rcx, {base_mode_vtable}
cmp qword ptr [rax], rcx
jne idle_select_done
cmp dword ptr [rax+0x1C], 1
je idle_select_ongoing
mov rax, {idle_selection_return}
cmp qword ptr [rsp+0x188], rax
jne idle_select_done
mov rax, {map_idle_return}
cmp qword ptr [rsp+0x1B8], rax
jne idle_select_done
mov rax, qword ptr [rsp+0x1A0]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov rcx, {base_mode_vtable}
cmp qword ptr [rax], rcx
jne idle_select_done
cmp dword ptr [rax+0x1C], 0
jne idle_select_done
idle_select_ongoing:
mov qword ptr [rsp+0x98], rax
mov rax, qword ptr [rsp+0x90]
'''
    source += _pointer('rax', 'idle_select_done') + _pointer('rsi', 'idle_select_done')
    source += '''cmp qword ptr [rsi+0x50], rax
jne idle_select_done
cmp dword ptr [rax], 100
jne idle_select_done
cmp dword ptr [rax+4], 0x10000
jne idle_select_done
cmp byte ptr [rax+0x434], 0
jne idle_select_done
cmp byte ptr [rax+0x435], 0
jne idle_select_done
mov rcx, {player_slot}
cmp qword ptr [rcx], rax
jne idle_select_done
cmp qword ptr [rax+0x38], rbp
jne idle_select_done
cmp qword ptr [rax+0x48], rbx
jne idle_select_done
cmp qword ptr [rax+0x68], rdi
jne idle_select_done
mov rcx, qword ptr [rax+0x230]
'''
    source += _pointer('rcx', 'idle_select_done') + '''cmp qword ptr [rcx+8], rsi
jne idle_select_done
'''
    for register in ('rbp', 'rbx', 'rdi'):
        source += _pointer(register, 'idle_select_done')
    source += '''cmp qword ptr [rbp], rax
jne idle_select_done
cmp qword ptr [rbx], rax
jne idle_select_done
cmp qword ptr [rdi+8], rax
jne idle_select_done
mov rcx, qword ptr [rax+0x18]
'''
    source += _pointer('rcx', 'idle_select_done') + '''cmp qword ptr [rcx], rax
jne idle_select_done
mov rcx, qword ptr [rcx+0x188]
'''
    source += _pointer('rcx', 'idle_select_done') + '''mov qword ptr [rsp+0x80], rcx
mov rax, {production_data}
mov eax, dword ptr [rax]
cmp eax, 0x58E5E
je idle_select_selected
cmp eax, 0x51BE1
jne idle_select_done
idle_select_selected:
mov dword ptr [rsp+0x88], eax
'''
    source += _idle_selection_ticket().replace('IDLE_TICKET_READY','idle_ticket_ready') + _idle_selection_record()
    source += '''mov rax, {package_ids}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'idle_select_done') + '''mov rax, qword ptr [rcx+0x10]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov rax, qword ptr [rax+8]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov edx, dword ptr [rsp+0x88]
xor r8d, r8d
call {package_get}
cmp dword ptr [rsp+0x88], 0x58E5E
jne idle_select_variant
cmp eax, 232
jne idle_select_done
jmp idle_select_package
idle_select_variant:
cmp eax, 233
jne idle_select_done
idle_select_package:
mov edx, eax
mov rax, {package_handles}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'idle_select_done') + '''mov rax, qword ptr [rcx]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov rax, qword ptr [rax+8]
'''
    source += _pointer('rax', 'idle_select_done') + '''xor r8d, r8d
call {package_handle}
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp byte ptr [rax+0x160], 0
je idle_select_done
mov rcx, qword ptr [rax+8]
cmp qword ptr [rsp+0x80], rcx
jne idle_select_done
mov rcx, qword ptr [rax+0x18]
'''
    source += _pointer('rcx', 'idle_select_done') + '''cmp qword ptr [rbp+8], rcx
jne idle_select_done
mov rcx, qword ptr [rax+0x30]
'''
    source += _pointer('rcx', 'idle_select_done') + '''cmp qword ptr [rbx+8], rcx
jne idle_select_done
mov rax, qword ptr [rax+0xA0]
'''
    source += _pointer('rax', 'idle_select_done') + '''mov rax, qword ptr [rax+0x468]
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp qword ptr [rdi+0x10], rax
jne idle_select_done
'''
    source += _idle_selection_ticket().replace('IDLE_TICKET_READY','idle_ticket_recheck_ready') + '''mov r8, qword ptr [rsp+0xB8]
''' + _idle_selection_record()
    source += '''mov rdx, qword ptr [rsp+0x90]
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne idle_select_done
cmp dword ptr [rdx], 100
jne idle_select_done
cmp dword ptr [rdx+4], 0x10000
jne idle_select_done
cmp byte ptr [rdx+0x434], 0
jne idle_select_done
cmp byte ptr [rdx+0x435], 0
jne idle_select_done
cmp qword ptr [rsi+0x50], rdx
jne idle_select_done
cmp qword ptr [rdx+0x38], rbp
jne idle_select_done
cmp qword ptr [rdx+0x48], rbx
jne idle_select_done
cmp qword ptr [rdx+0x68], rdi
jne idle_select_done
cmp qword ptr [rbp], rdx
jne idle_select_done
cmp qword ptr [rbx], rdx
jne idle_select_done
cmp qword ptr [rdi+8], rdx
jne idle_select_done
mov rax, qword ptr [rdx+0x230]
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp qword ptr [rax+8], rsi
jne idle_select_done
mov rax, qword ptr [rdx+0x18]
'''
    source += _pointer('rax', 'idle_select_done') + '''cmp qword ptr [rax], rdx
jne idle_select_done
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x188], rcx
jne idle_select_done
mov rax, {data}
inc dword ptr [rax+0x28]
mov dword ptr [rsp+0x8C], 1
idle_select_done:
cmp dword ptr [rsp+0x8C], 0
jne idle_select_override
mov rax, {data}
inc dword ptr [rax+0x2C]
'''
    source += _restore() + '''mov edx, dword ptr [rsi+0x68]
mov ecx, edx
jmp {return}
idle_select_override:
'''
    return source + _restore() + '''mov edx, 1
mov ecx, edx
jmp {return}
'''


def build_plan(base: int, production_data: int, visual_data: int, allocation: int) -> dict:
    from menu_preview_visual_hooks import build_plan as visual_plan, DATA_OFFSET as VISUAL_DATA_OFFSET
    for address in (base, production_data, visual_data, allocation):
        if not isinstance(address, int) or not 0x10000 <= address < 0x800000000000:
            raise ValueError('Require absolute user-space pointers')
    if base & 0xFFF or allocation & 0xFFF:
        raise ValueError('Module and private allocation must be page aligned')
    if any(allocation <= address < allocation + ALLOCATION_SIZE
           for address in (production_data, visual_data)):
        raise ValueError('Appearance allocation must not overlap frozen data')
    relative = [base + rva for rva in (HOOK_RVA, IDLE_RVA, IDLE_SELECT_RVA, LOADOUT_RVA, TARGET_RVAS['gear_binder'],
                 TARGET_RVAS['package_get'], TARGET_RVAS['package_handle'])]
    if any(not -(1 << 31) < target - arena < (1 << 31)
           for target in relative for arena in (allocation, allocation + DATA_OFFSET)):
        raise ValueError('Private code must stay within native relative branch range')
    wrapper_continuation = visual_plan(base, production_data,
                                     visual_data-VISUAL_DATA_OFFSET)['wrapper_continuation']
    return dict(tool_version='menu-appearance-private-2', allocation_size=ALLOCATION_SIZE,
        data_offset=DATA_OFFSET, trial_allocation=allocation,
        production_data_read_only=True, visual_data_read_only=True,
        native_actor_identity_preserved=True, native_stats_preserved=True,
        native_equipment_preserved=True, native_flags_preserved=True,
        wrapper_continuation=wrapper_continuation,
        targets=dict(TARGET_RVAS, production_data=production_data-base,
                     visual_data=visual_data-base,
                     wrapper_continuation=wrapper_continuation-base), hooks=[dict(
            name='HE_MapAppearancePrivate', rva=HOOK_RVA, original=ORIGINAL,
            length=5, code_offset=0, code_capacity=0x1000, asm=appearance_asm(),
            purpose='Suppress visual gear binder only for completed native map Hino body'), dict(
            name='HE_MapNativeIdlePrivate', rva=IDLE_RVA, original=IDLE_ORIGINAL,
            length=8, code_offset=0x1000, code_capacity=0x1000, asm=idle_asm(),
            purpose='Retain Hino motion bank during exactly scoped native map construction'), dict(
            name='HE_MapIdleSelectionPrivate', rva=IDLE_SELECT_RVA, original=IDLE_SELECT_ORIGINAL,
            length=5, code_offset=0x2000, code_capacity=0x1000, asm=idle_selection_asm(),
            purpose='Use native Hino resource banks for scoped initial/ongoing map action0 idle'), dict(
            name='HE_MapLoadoutAppearancePrivate', rva=LOADOUT_RVA, original=LOADOUT_ORIGINAL,
            length=5, code_offset=0x3000, code_capacity=0x1000, asm=loadout_appearance_asm(),
            purpose='Suppress bypassing loadout visual binder for completed current Hino map actor')])


def native_signatures(code=None):
    if code is None:
        from code_inspect import CodeImage
        code = CodeImage()
    fixed = ((HOOK_RVA, ORIGINAL), (IDLE_RVA, IDLE_ORIGINAL),
        (IDLE_SELECT_RVA, IDLE_SELECT_ORIGINAL),
        (LOADOUT_RVA, LOADOUT_ORIGINAL),
        (0x7C82F8, '48 8D 8E 28 01 00 00 49 8B D6'),
        (0x7C8307, '48 8B 96 98 0B 00 00 48 8D 8E D8 09 00 00 48 8B C2'),
        (0x7B0B70, '48 89 5C 24 10 48 89 6C 24 18 56 57 41 54 41 56 41 57 48 83 EC 40'))
    for rva, expected in fixed:
        at, expected = code.file_offset(rva), bytes.fromhex(expected)
        if bytes(code.data[at:at+len(expected)]) != expected:
            raise ValueError(f'Appearance native signature differs at {rva:X}')
    return [dict(rva=rva, length=length,
                 original=bytes(code.data[code.file_offset(rva):code.file_offset(rva)+length]).hex())
            for rva, length in NATIVE_SPANS]
