"""A fresh9 may request another idle guardian while our native LW stays active.

Mode5 is a confirmed appearance, not an attack. The active path never restarts
the native core, writes its gauge/charge, or interrupts a pending guardian.
Native LW+54 is a retained exhaustion/exit boolean, not an animation handle.
Accept its known 0/1 values; the original initializer clears it on the next start.
LW+55 remains the independent attachment-applied latch and must still be zero.
"""


def guardian_repeat_hooks():
    from hinoenma_guardian_spirit import guardian_living_weapon_hooks
    hooks=guardian_living_weapon_hooks()
    first=dict(hooks[0])
    marker='cmp dword ptr [rdx+0xB0], 0\njne living_weapon_done\n'
    if first['asm'].count(marker)!=1:
        raise ValueError('Native Living Weapon state gate changed.')
    first['asm']=first['asm'].replace(marker,
        'cmp dword ptr [rdx+0xB0], 1\nje living_weapon_guardian_repeat\n'+marker)
    marker='cmp word ptr [rdx+0x104], 0\njne living_weapon_done\n'
    if first['asm'].count(marker)!=1:
        raise ValueError('Native Living Weapon retained/attachment flags changed.')
    first['asm']=first['asm'].replace(marker,'''cmp byte ptr [rdx+0x104], 1
ja living_weapon_done
cmp byte ptr [rdx+0x105], 0
jne living_weapon_done
''')
    marker='living_weapon_failed:\n'
    if first['asm'].count(marker)!=1:
        raise ValueError('Native Living Weapon failure label changed.')
    first['asm']=first['asm'].replace(marker,'''living_weapon_guardian_repeat:
cmp dword ptr [r11+0xE50], 1
jne living_weapon_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE4C]
jne living_weapon_done
cmp dword ptr [r11+0xE5C], 0
jne living_weapon_done
cmp byte ptr [rdx+0xB4], 0
jne living_weapon_done
cmp byte ptr [rdx+0x104], 1
ja living_weapon_done
cmp byte ptr [rdx+0x105], 0
jne living_weapon_done
cmp qword ptr [rdx+0x110], 0
jne living_weapon_done
cmp qword ptr [rdx+0x118], 0
jne living_weapon_done
cmp qword ptr [r10+0x2C0], 0
je living_weapon_done
cmp qword ptr [r10+0x2C8], 0
je living_weapon_done
mov rcx, r10
call living_weapon_guardian_start
jmp living_weapon_done
'''+marker)
    first['purpose']+='; accept the native retained exhaustion boolean0/1 but not installed attachments; fresh9 during this owned active epoch may repeat idle mode5 appearance without restarting native LW; attack not added'
    return [first,*hooks[1:]]
