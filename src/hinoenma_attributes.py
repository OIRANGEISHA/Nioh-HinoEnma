"""Scoped native attribute overlay. Baseline: level 1, eight abilities at 5.

Only buffers owned by the existing stat component are initialized. Native
75F880 already frees their allocator/pointer pairs on actor destruction.
No actor metadata, weapon view, saved growth or inventory record is changed.
The temporary naked reference uses the engine's ordinary preview calculation.
"""

VOLATILE_SAVE = """
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, {frame}
movups xmmword ptr [rsp+0x20], xmm0
movups xmmword ptr [rsp+0x30], xmm1
movups xmmword ptr [rsp+0x40], xmm2
movups xmmword ptr [rsp+0x50], xmm3
movups xmmword ptr [rsp+0x60], xmm4
movups xmmword ptr [rsp+0x70], xmm5
"""

VOLATILE_RESTORE = """
movups xmm0, xmmword ptr [rsp+0x20]
movups xmm1, xmmword ptr [rsp+0x30]
movups xmm2, xmmword ptr [rsp+0x40]
movups xmm3, xmmword ptr [rsp+0x50]
movups xmm4, xmmword ptr [rsp+0x60]
movups xmm5, xmmword ptr [rsp+0x70]
add rsp, {frame}
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
"""


def guard(label):
    return """
mov r11, {{data}}
cmp byte ptr [r11+0x58], 1
jne {label}
cmp r14, qword ptr [r11+0x10]
jne {label}
mov rax, {{player_slot}}
cmp r14, qword ptr [rax]
jne {label}
mov eax, dword ptr [r14]
cmp eax, 0x58E5E
je {label}_template
cmp eax, 0x51BE1
jne {label}
{label}_template:
cmp eax, dword ptr [r11+0x04]
jne {label}
cmp word ptr [r14+0x06], 1
jne {label}
cmp dword ptr [r14+0xEF0], 0
jne {label}
cmp r14, qword ptr [rsi]
jne {label}
cmp rsi, qword ptr [r14+0x240]
jne {label}
cmp qword ptr [rsi+0xB98], 0
jne {label}
mov rax, qword ptr [r14+0xE90]
test rax, rax
je {label}
test byte ptr [rax+0x04], 3
jne {label}
cmp dword ptr [rax+0x0C], 1
jne {label}
""".format(label=label)


INIT_ASM = (
    VOLATILE_SAVE.replace('{frame}', '0x80')
    + guard('attr_init_done')
    + """
mov rax, qword ptr [rsi+0xB70]
or rax, qword ptr [rsi+0xB78]
or rax, qword ptr [rsi+0xB80]
or rax, qword ptr [rsi+0xB88]
jne attr_init_done
lea rcx, [rsi+0x9D8]
mov edx, 1
call {stats_construct}
mov r11, {data}
cmp qword ptr [rsi+0xB70], 0
je attr_init_failed
cmp qword ptr [rsi+0xB80], 0
je attr_init_failed
inc dword ptr [r11+0x5C]
jmp attr_init_done
attr_init_failed:
inc dword ptr [r11+0x88]
attr_init_done:
"""
    + VOLATILE_RESTORE.replace('{frame}', '0x80')
    + """
lea rdi, [rsi+0x9D8]
jmp {return}
"""
)

# Frame: native shadow 00..20, six volatile XMM saves 20..80,
# Boss derived fields 80..218, naked reference 220..3B8,
# fully constructed temporary gear view 3C0..C70. Every frame < one page.
# The engine's two preview calculations retain their own normal stack probes.
OVERLAY_ASM = (
    "call {boss_stats}\n"
    + VOLATILE_SAVE.replace('{frame}', '0xC80')
    + guard('attr_overlay_done')
    + """
lea rax, [rsi+0x9D8]
cmp rax, r12
jne attr_overlay_done
cmp qword ptr [r12+0x198], 0
je attr_overlay_done
cmp qword ptr [r12+0x1A8], 0
je attr_overlay_done
xor ecx, ecx
attr_copy_boss:
mov eax, dword ptr [r12+rcx]
mov dword ptr [rsp+rcx+0x80], eax
add ecx, 4
cmp ecx, 0x198
jb attr_copy_boss
lea rcx, [rsp+0x3C0]
call {equipment_construct}
mov rcx, qword ptr [r12+0x1A8]
call {growth_reset}
mov r10, qword ptr [r12+0x1A8]
mov dword ptr [r10], 1
mov rax, 0x0005000500050005
mov qword ptr [r10+0x04], rax
mov qword ptr [r10+0x0C], rax
lea rdx, [rsp+0x3C0]
mov rcx, r12
xor r8d, r8d
xor r9d, r9d
call {player_stats}
xor ecx, ecx
attr_copy_reference:
mov eax, dword ptr [r12+rcx]
mov dword ptr [rsp+rcx+0x220], eax
add ecx, 4
cmp ecx, 0x198
jb attr_copy_reference
mov rcx, qword ptr [r12+0x1A8]
call {growth_load}
mov byte ptr [r12+0x1B8], 0
lea rcx, [rsp+0x3C0]
call {equipment_load}
lea rdx, [rsp+0x3C0]
mov rcx, r12
xor r8d, r8d
xor r9d, r9d
call {player_stats}

mov r11, {data}
inc dword ptr [r11+0x60]
mov eax, dword ptr [rsp+0x80]
mov dword ptr [r11+0x64], eax
mov eax, dword ptr [r12]
sub eax, dword ptr [rsp+0x220]
mov dword ptr [r11+0x68], eax
mov eax, dword ptr [rsp+0x84]
mov dword ptr [r11+0x6C], eax
mov eax, dword ptr [r12+4]
sub eax, dword ptr [rsp+0x224]
mov dword ptr [r11+0x70], eax
mov eax, dword ptr [rsp+0x160]
mov dword ptr [r11+0x74], eax
mov eax, dword ptr [r12+0xE0]
sub eax, dword ptr [rsp+0x300]
mov dword ptr [r11+0x78], eax
mov eax, dword ptr [rsp+0x88]
mov dword ptr [r11+0x7C], eax
mov eax, dword ptr [r12+8]
sub eax, dword ptr [rsp+0x228]
mov dword ptr [r11+0x80], eax

mov edx, 8
attr_restore_boss_weapon:
mov r8d, dword ptr [r12+rdx]
sub r8d, dword ptr [rsp+rdx+0x220]
xor eax, eax
test r8d, r8d
cmovs r8d, eax
add r8d, dword ptr [rsp+rdx+0x80]
movups xmm0, xmmword ptr [rsp+rdx+0x80]
movups xmm1, xmmword ptr [rsp+rdx+0x90]
mov rax, qword ptr [rsp+rdx+0xA0]
movups xmmword ptr [r12+rdx], xmm0
movups xmmword ptr [r12+rdx+0x10], xmm1
mov qword ptr [r12+rdx+0x20], rax
mov dword ptr [r12+rdx], r8d
add edx, 0x28
cmp edx, 0xD0
jb attr_restore_boss_weapon

mov edx, 0x124
mov ecx, 0xC70
attr_save_player_thresholds:
mov ax, word ptr [r12+rdx]
mov word ptr [rsp+rcx], ax
add edx, 8
add ecx, 2
cmp edx, 0x15C
jb attr_save_player_thresholds
mov ax, word ptr [r12+0x15C]
mov word ptr [rsp+0xC7E], ax
mov edx, 0x124
attr_restore_boss_status_records:
mov eax, dword ptr [rsp+rdx+0x80]
mov dword ptr [r12+rdx], eax
add edx, 4
cmp edx, 0x170
jb attr_restore_boss_status_records

"""
)

# Confirmed scalar types only. Mixed status records keep the Boss decay,
# recovery and animation fields. Pointer and allocator fields are untouched.
DWORD_FIELDS = (0, 4, 0xD0, 0xD4, 0xD8, 0xE0, *range(0xE4, 0x124, 4),
                )
WORD_FIELDS = (*range(0x124, 0x15C, 8), 0x15C)

# Generate small integer-index tables inside the instruction stream using
# immediate moves; no relocatable data references and no unsafe packed casts.
for offset in DWORD_FIELDS:
    OVERLAY_ASM += f"""
mov eax, dword ptr [r12+0x{offset:X}]
sub eax, dword ptr [rsp+0x{0x220+offset:X}]
add eax, dword ptr [rsp+0x{0x80+offset:X}]
mov dword ptr [r12+0x{offset:X}], eax
"""
for index, offset in enumerate(WORD_FIELDS):
    OVERLAY_ASM += f"""
movzx eax, word ptr [rsp+0x{0xC70+2*index:X}]
movzx ecx, word ptr [rsp+0x{0x220+offset:X}]
sub eax, ecx
movzx ecx, word ptr [rsp+0x{0x80+offset:X}]
add eax, ecx
mov word ptr [r12+0x{offset:X}], ax
"""

for offset in (0xDC, 0x174):
    OVERLAY_ASM += f"""
movss xmm0, dword ptr [r12+0x{offset:X}]
divss xmm0, dword ptr [rsp+0x{0x220+offset:X}]
mulss xmm0, dword ptr [rsp+0x{0x80+offset:X}]
movss dword ptr [r12+0x{offset:X}], xmm0
"""

# The auxiliary player capacities have no Boss counterpart; keep their native
# complete values. +170 is an enum (80/50/20/0 from 7C99F0), not a percentage.
# Keep the Boss's existing agility tier, rather than inventing an invalid enum.
for offset in range(0x178, 0x198, 4):
    OVERLAY_ASM += f"""
mov eax, dword ptr [rsp+0x{0x80+offset:X}]
add dword ptr [r12+0x{offset:X}], eax
"""
OVERLAY_ASM += """
mov eax, dword ptr [rsp+0x1F0]
mov dword ptr [r12+0x170], eax
attr_overlay_done:
"""
OVERLAY_ASM += VOLATILE_RESTORE.replace('{frame}', '0xC80') + 'jmp {return}\n'

ATTRIBUTE_HOOKS = [
    {'name': 'HE_AttributeInit', 'rva': 0x7C7F75, 'length': 7,
     'purpose': 'Initialize missing native growth/effect buffers for the captured Boss player', 'asm': INIT_ASM},
    {'name': 'HE_AttributeOverlay', 'rva': 0x7C82DB, 'length': 5,
     'code_capacity': 0x800,
     'purpose': 'Boss baseline plus the native equipped player minus a naked level-one reference', 'asm': OVERLAY_ASM},
]

ATTRIBUTE_TARGETS = {
    'stats_construct': 0x7AE650, 'boss_stats': 0x7B8380,
    'equipment_construct': 0x7AE4B0, 'growth_reset': 0x7B3230,
    'growth_load': 0x7BC440, 'equipment_load': 0x7BBB20, 'player_stats': 0x7B8FA0,
}


def weapon_overlay_hooks():
    """Route the selected melee attack delta to the Boss's five attack views.

    Native 7B2170 maps gear +8A4 != 0 to melee slot 0, and == 0 to slot 1.
    Its ordinary hit builders (717D0F and 7E2459) consume the selected 40-byte
    record, while Boss motions can also consume their other attack views.
    Preserve every Boss record except its attack scalar. Never add both weapons
    or select the higher attack value. The native effect pass uses the same
    selection flag, so the unused weapon's affixes remain inactive.
    """
    source = OVERLAY_ASM.replace(
        'call {equipment_load}\nlea rdx, [rsp+0x3C0]',
        'call {equipment_load}\n'
        'mov al, byte ptr [rsi+0x9CC]\n'
        'mov byte ptr [rsp+0xC64], al\n'
        'lea rdx, [rsp+0x3C0]',
    ).replace(
        'mov edx, 8\nattr_restore_boss_weapon:',
        '''xor edx, edx
cmp byte ptr [rsp+0xC64], 0
sete dl
mov dword ptr [r11+0x8C], edx
imul eax, edx, 0xC8
mov eax, dword ptr [rsp+rax+0x3C0]
mov dword ptr [r11+0x98], eax
imul edx, edx, 0x28
mov eax, dword ptr [r12+rdx+8]
mov dword ptr [r11+0x90], eax
mov ecx, dword ptr [rsp+rdx+0x228]
mov dword ptr [r11+0x94], ecx
sub eax, ecx
mov dword ptr [r11+0x80], eax
inc dword ptr [r11+0x9C]
mov edx, 8
attr_restore_boss_weapon:''',
    ).replace(
        'mov r8d, dword ptr [r12+rdx]\n'
        'sub r8d, dword ptr [rsp+rdx+0x220]',
        'mov r8d, dword ptr [r11+0x80]',
    )
    hooks = [dict(hook) for hook in ATTRIBUTE_HOOKS]
    hooks[-1].update(
        asm=source, code_capacity=0xC00,
        purpose='Boss baseline plus native growth/equipment; selected melee attack delta feeds all Boss attack views',
    )
    return hooks
