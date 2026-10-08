"""Add native enchant scaling to Hino's four successful life-drain hits.

The native successful-grab descriptors already inherit component1118/111C,
but their elemental coefficient1D is zero. At the damage and accumulation
loads, replace only the transient XMM coefficient for the current Hino's
exact four action857/motion1101 descriptors while a matching buff is active.
Use the observed ordinary-attack coefficient10 (native multiplier0.01).
Keep descriptors, physical damage, native special100% path, animation,
paralysis attributes, healing and all other attacks unchanged.
"""
from copy import deepcopy

from hinoenma_tutorial import player_guard

COEFFICIENT = 10
HOOKS = (
    ('HE_GrabElementDamage', 0x727874, '0F B6 48 1D 66 0F 6E C9', 0x900, 'xmm1'),
    ('HE_GrabElementAccumulation', 0x727936, '0F B6 48 1D 66 0F 6E D1', 0xD00, 'xmm2'),
)
CODE_CAPACITY = 0x300


def coefficient_asm(xmm):
    if xmm not in ('xmm1', 'xmm2'):
        raise ValueError('Unexpected native elemental coefficient register')
    return ('''movzx ecx, byte ptr [rax+0x1D]
movd XMM, ecx
pushfq
push rax
push rcx
push rdx
push r10
push r11
test ecx, ecx
jne grab_element_done
mov r11, {data}
'''+player_guard('grab_element')+'''cmp r10, qword ptr [r15+0x28]
jne grab_element_done
cmp r10, qword ptr [r15+0xE8]
jne grab_element_done
cmp byte ptr [r15+0x145], 0
jne grab_element_done
mov rax, qword ptr [r10+0x240]
test rax, rax
je grab_element_done
cmp r10, qword ptr [rax]
jne grab_element_done
cmp r10, qword ptr [rax+0x108]
jne grab_element_done
cmp qword ptr [rax+0x20], 0
jle grab_element_done
mov edx, dword ptr [r15+0x18]
cmp edx, 4
ja grab_element_done
cmp edx, dword ptr [rax+0x1118]
jne grab_element_done
mov edx, dword ptr [r15+0x1C]
test edx, edx
jle grab_element_done
cmp edx, dword ptr [rax+0x111C]
jne grab_element_done
mov rax, qword ptr [r10+0x230]
test rax, rax
je grab_element_done
cmp r10, qword ptr [rax]
jne grab_element_done
mov rax, qword ptr [rax+0x08]
test rax, rax
je grab_element_done
cmp r10, qword ptr [rax+0x50]
jne grab_element_done
mov rdx, qword ptr [rax+0x5B0]
test rdx, rdx
je grab_element_done
cmp rdx, qword ptr [r15+0x100]
jne grab_element_done
mov rdx, qword ptr [rax+0x58]
test rdx, rdx
je grab_element_done
cmp dword ptr [rdx], 857
jne grab_element_done
cmp byte ptr [rdx+0x40], 1
jne grab_element_done
mov rax, qword ptr [rdx+0x20]
test rax, rax
je grab_element_done
cmp dword ptr [rax+0x20], 1101
jne grab_element_done
cmp word ptr [rdx+0x52], 4
jne grab_element_done
movzx ecx, word ptr [rdx+0x50]
cmp ecx, 4096
ja grab_element_done
mov rdx, qword ptr [rdx+0x48]
test rdx, rdx
je grab_element_done
mov rax, qword ptr [r15+0xE0]
cmp rax, qword ptr [r15]
jne grab_element_done
test word ptr [rax+0x44], 0x2000
je grab_element_done
bt qword ptr [rax], 43
jc grab_element_done
lea rdx, [rdx+rcx*8]
cmp rax, qword ptr [rdx]
je grab_element_accept
cmp rax, qword ptr [rdx+0x08]
je grab_element_accept
cmp rax, qword ptr [rdx+0x10]
je grab_element_accept
cmp rax, qword ptr [rdx+0x18]
jne grab_element_done
grab_element_accept:
mov ecx, 10
movd XMM, ecx
grab_element_done:
pop r11
pop r10
pop rdx
pop rcx
pop rax
popfq
jmp {return}
''').replace('XMM', xmm)


def apply_grab_elements(previous):
    if previous.get('tool_version') != '0.38' or len(previous['hooks']) != 43:
        raise ValueError('Life-drain elements require complete v0.38')
    plan = deepcopy(previous)
    for name, offset in (('HE_PlayerInit', 0x800), ('HE_Skin', 0xC00)):
        existing = next(h for h in plan['hooks'] if h['name'] == name)
        if existing['code_offset'] != offset or existing.get('code_capacity', 0x400) != 0x400:
            raise ValueError('Unexpected reserved code slot')
        existing['code_capacity'] = 0x100
    for name, rva, original, offset, xmm in HOOKS:
        plan['hooks'].append(dict(name=name, rva=rva, length=8, original=original,
            code_offset=offset, code_capacity=CODE_CAPACITY,
            purpose='Scoped native enchant coefficient for current Hino successful life-drain; original physical damage, attributes, animation and healing retained',
            asm=coefficient_asm(xmm)))
    spans = sorted((h['code_offset'], h['code_offset']+h.get('code_capacity', 0x400)) for h in plan['hooks'])
    if any(a[1] > b[0] for a, b in zip(spans, spans[1:])) or spans[-1][1] > plan['data_offset']:
        raise ValueError('Life-drain elemental code overlaps existing code or data')
    plan.update(tool_version='0.39', grab_element_inheritance_revision=1,
                grab_element_coefficient=COEFFICIENT,
                stage='grab_element_coefficient_pending_gameplay')
    return plan
