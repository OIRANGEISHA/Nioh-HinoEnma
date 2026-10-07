"""Read saved weapons for Boss statistics and the native weapon HUD.

The HUD's C80180..C8062F function only dereferences RDI for its gear records
and selection bytes after C801D7. Its original epilogue restores the caller's
RDI. Redirect that local read view, never the real actor/component equipment.
"""
from hinoenma_attributes import VOLATILE_SAVE, VOLATILE_RESTORE, weapon_overlay_hooks

HUD_VIEW_OFFSET = 0x200
HUD_VIEW_SIZE = 0x9D8


def sole_weapon_selection(base, flag, label):
    """Keep AL's native selection unless that slot is empty and the other isn't.

    base points to the first C8-byte melee record, flag to the output byte.
    Canonicalize only the fallback. A nonempty selected slot always wins.
    """
    return f"""
test al, al
je {label}_second
cmp dword ptr [{base}], -1
jne {label}_done
cmp dword ptr [{base}+0xC8], -1
je {label}_done
xor eax, eax
jmp {label}_done
{label}_second:
cmp dword ptr [{base}+0xC8], -1
jne {label}_done
cmp dword ptr [{base}], -1
je {label}_done
mov al, 1
{label}_done:
mov byte ptr [{flag}], al
"""


def compatible_weapon_hooks():
    hooks = weapon_overlay_hooks()
    selected = 'mov byte ptr [rsp+0xC64], al\n'
    assert hooks[-1]['asm'].count(selected) == 1
    hooks[-1]['asm'] = hooks[-1]['asm'].replace(selected, sole_weapon_selection(
        'rsp+0x3C0', 'rsp+0xC64', 'attr_sole_weapon'))
    hooks[-1]['purpose'] = ('Boss baseline plus native growth/equipment; use selected melee '
                             'weapon, or the sole equipped weapon if the selected slot is empty')
    return hooks


HUD_ASM = (
    'mov qword ptr [rsp+0x88], rsi\n'
    + VOLATILE_SAVE.replace('{frame}', '0x80')
    + """
mov r11, {data}
cmp byte ptr [r11+0x58], 1
jne weapon_hud_done
mov r10, qword ptr [rdi]
cmp r10, qword ptr [r11+0x10]
jne weapon_hud_done
mov rax, {player_slot}
cmp r10, qword ptr [rax]
jne weapon_hud_done
mov eax, dword ptr [r10]
cmp eax, 0x58E5E
je weapon_hud_template
cmp eax, 0x51BE1
jne weapon_hud_done
weapon_hud_template:
cmp eax, dword ptr [r11+4]
jne weapon_hud_done
cmp word ptr [r10+6], 1
jne weapon_hud_done
cmp dword ptr [r10+0xEF0], 0
jne weapon_hud_done
cmp rdi, qword ptr [r10+0x240]
jne weapon_hud_done
cmp qword ptr [rdi+0xB98], 0
jne weapon_hud_done
mov rax, qword ptr [r10+0xE90]
test rax, rax
je weapon_hud_done
test byte ptr [rax+4], 3
jne weapon_hud_done
cmp dword ptr [rax+0x0C], 1
jne weapon_hud_done

lea rcx, [r11+0x328]
call {equipment_construct}
mov r11, {data}
lea rcx, [r11+0x328]
call {equipment_load}
mov r11, {data}
mov ax, word ptr [rdi+0x9CC]
mov word ptr [r11+0xBCC], ax
mov ax, word ptr [rdi+0x9CE]
mov word ptr [r11+0xBCE], ax
mov al, byte ptr [rdi+0x9CC]
"""
    + sole_weapon_selection('r11+0x328', 'r11+0xBCC', 'hud_sole_weapon')
    + """
inc dword ptr [r11+0xA0]
lea rdi, [r11+0x200]
weapon_hud_done:
"""
    + VOLATILE_RESTORE.replace('{frame}', '0x80')
    + 'jmp {return}\n'
)

HUD_HOOK = {
    'name': 'HE_WeaponHud', 'rva': 0xC801D7, 'length': 8,
    'purpose': 'Native weapon icon function reads saved player gear through a private view; real Boss gear stays intact',
    'asm': HUD_ASM,
}


def refresh_view_asm(*, label, replay, destination, view_offset, widget, counter):
    """Redirect only gear reads in a native HUD continuation.

    C82200 also uses RSI+1220 for its weapon-effect list. Keep RSI real there
    and redirect its gear-only RBP. The two switch routines use RSI solely
    for gear and restore the caller's RSI in their original epilogues.
    """
    body=HUD_ASM.split('mov r11, {data}\n',1)[1].split('inc dword ptr [r11+0xA0]',1)[0]
    body=body.replace('rdi','rsi').replace('weapon_hud',label).replace('hud_sole_weapon',label+'_sole_weapon')
    return (
        replay+'\n'+VOLATILE_SAVE.replace('{frame}','0x80')
        +'mov r11, {data}\n'+body
        +f'inc dword ptr [r11+0x{counter:X}]\n'
        +f'mov qword ptr [r11+0xB0], {widget}\n'
        +f'lea {destination}, [r11+0x{view_offset:X}]\n'
        +label+'_done:\n'+VOLATILE_RESTORE.replace('{frame}','0x80')
        +'jmp {return}\n')


HUD_REFRESH_HOOKS=[
    {'name':'HE_WeaponHudRefresh','rva':0xC8226D,'length':7,
     'purpose':'Keep per-frame weapon icon comparison and refresh on saved gear; RSI remains the real component for its effect list',
     'asm':refresh_view_asm(label='hud_refresh',replay='lea rbp, [rsi+0x128]',
                            destination='rbp',view_offset=0x328,widget='rdi',counter=0xA4)},
    {'name':'HE_WeaponHudMeleeSwitch','rva':0xC81FCB,'length':9,
     'purpose':'Native melee icon switch reads the same saved gear view as initial icon setup',
     'asm':refresh_view_asm(label='hud_melee_switch',replay='mov rcx, qword ptr [rbx+0x60]\nmov edx, 0x18',
                            destination='rsi',view_offset=0x200,widget='rbx',counter=0xA8)},
    {'name':'HE_WeaponHudRangedSwitch','rva':0xC81C19,'length':9,
     'purpose':'Native ranged icon switch reads the same saved gear view as initial icon setup',
     'asm':refresh_view_asm(label='hud_ranged_switch',replay='mov rcx, qword ptr [rbx+0x60]\nmov edx, 0x16',
                            destination='rsi',view_offset=0x200,widget='rbx',counter=0xAC)},
]
