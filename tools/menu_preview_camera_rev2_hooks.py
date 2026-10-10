"""Uninstalled, distance-only trial for the completed map Hino preview.

The native GameCameraMode menu mode4 computes a distance of580. This private
hook computes740 only for the exact logical map actor already bound by the
frozen visual and revision4 appearance supplements. It never calls a native
helper or writes a camera, actor, resource, equipment or production property.
The installer pins a fresh selected/owner/actor/body binding after revision4
has suppressed construction gear. A selection or binding change restores the
native distance until this separate trial is reinstalled. The installer must
verify the frozen supplements and fresh ready-body capture before pinning it.
"""
from __future__ import annotations

ALLOCATION_SIZE, DATA_OFFSET, CODE_CAPACITY, OWN_DATA_SIZE = 0x2000, 0x1000, 0x1000, 0x30
HOOK_RVA, ORIGINAL = 0x856565, 'F3 0F 10 15 17 80 99 00'
HOOK_NAME = 'HE_MapPreviewCameraDistancePrivate'
HOOKS = ((HOOK_NAME, HOOK_RVA, ORIGINAL, 0),)
NATIVE_DISTANCE, TRIAL_DISTANCE = 580.0, 740.0
TARGET_RVAS = dict(camera_vtable=0x11EE120, base_mode_vtable=0x11FB588,
    player_slot=0x18A0490, native_distance=0x11EE584)
NATIVE_SPANS = ((HOOK_RVA, 8), (0x8552DA, 0x27), (0x85531C, 0x3F),
    (0x856501, 0x87), (0x858454, 0x28), (0x84E67C, 0x2F),
    (0x11EE584, 4))
# Own private data: only D0 entries, D4 overrides, D8 fallbacks are mutated.
# The installer initializes a fixed float and binding, which the hook only reads.
BINDING_SCHEMA = dict(selected=(0x10, 4), epoch=(0x14, 4),
    owner=(0x18, 8), actor=(0x20, 8), body=(0x28, 8))
_DISPLACEMENT_MARKER = '0x123456'


def _pointer(register: str) -> str:
    return f'''cmp {register}, 0x10000
jb camera_native
mov r10, 0x800000000000
cmp {register}, r10
jae camera_native
'''


def _guard(*, recheck=False) -> str:
    # First pass captures selected/owner/actor/body. The last pass compares
    # all four identities again, including mode, flags and both private pairs.
    source = _pointer('rdi') + '''mov rax, {camera_vtable}
cmp qword ptr [rdi], rax
jne camera_native
cmp dword ptr [rdi+0x158], 4
jne camera_native
cmp dword ptr [rdi+0x15C], 4
jne camera_native
mov rax, {production_data}
mov r8d, dword ptr [rax]
cmp r8d, 0x58E5E
je CAMERA_SELECTED
cmp r8d, 0x51BE1
jne camera_native
CAMERA_SELECTED:
mov r11, {data}
cmp dword ptr [r11+0x10], r8d
jne camera_native
cmp dword ptr [r11+0x14], 1
jne camera_native
'''
    source += ('cmp r8d, dword ptr [rsp]\njne camera_native\n' if recheck
        else 'mov dword ptr [rsp], r8d\n')
    source += '''mov r11, {visual_data}
cmp dword ptr [r11+8], r8d
jne camera_native
cmp dword ptr [r11+0x14], 7
jne camera_native
cmp dword ptr [r11+0x20], 0
jne camera_native
cmp dword ptr [r11+0x28], 0
je camera_native
mov ecx, dword ptr [r11+0x2C]
test ecx, ecx
je camera_native
cmp dword ptr [r11+0x30], ecx
jne camera_native
cmp dword ptr [r11+0x38], 1
jne camera_native
cmp r8d, 0x58E5E
jne CAMERA_VARIANT
cmp dword ptr [r11+0x18], 232
jne camera_native
jmp CAMERA_PACKAGE
CAMERA_VARIANT:
cmp dword ptr [r11+0x18], 233
jne camera_native
CAMERA_PACKAGE:
mov rcx, qword ptr [r11]
''' + _pointer('rcx') + '''mov rax, {base_mode_vtable}
cmp qword ptr [rcx], rax
jne camera_native
cmp dword ptr [rcx+0x1C], 1
jne camera_native
mov rax, {data}
cmp qword ptr [rax+0x18], rcx
jne camera_native
'''
    source += ('cmp qword ptr [rsp+8], rcx\njne camera_native\n' if recheck
        else 'mov qword ptr [rsp+8], rcx\n')
    source += '''mov rax, {player_slot}
mov rdx, qword ptr [rax]
''' + _pointer('rdx') + '''cmp qword ptr [rdi+0x208], rdx
jne camera_native
cmp dword ptr [rdx], 100
jne camera_native
cmp dword ptr [rdx+4], 0x10000
jne camera_native
cmp byte ptr [rdx+0x434], 0
jne camera_native
cmp byte ptr [rdx+0x435], 0
jne camera_native
mov rax, {data}
cmp qword ptr [rax+0x20], rdx
jne camera_native
'''
    source += ('cmp qword ptr [rsp+0x10], rdx\njne camera_native\n' if recheck
        else 'mov qword ptr [rsp+0x10], rdx\n')
    source += '''mov r11, {appearance_data}
cmp dword ptr [r11+0x3C], 0
je camera_native
cmp qword ptr [r11+0x10], rdx
jne camera_native
mov r9, qword ptr [r11+0x18]
''' + _pointer('r9') + '''mov rax, qword ptr [rdx+0x18]
''' + _pointer('rax') + '''cmp qword ptr [rax], rdx
jne camera_native
cmp qword ptr [rax+0x188], r9
jne camera_native
mov rax, {data}
cmp qword ptr [rax+0x28], r9
jne camera_native
'''
    source += ('cmp qword ptr [rsp+0x18], r9\njne camera_native\n' if recheck
        else 'mov qword ptr [rsp+0x18], r9\n')
    for label in ('CAMERA_SELECTED', 'CAMERA_VARIANT', 'CAMERA_PACKAGE'):
        source = source.replace(label, label.lower() + ('_recheck' if recheck else ''))
    return source


def camera_asm() -> str:
    # Only these volatile GPRs/flags are used. XMM2 is assigned solely by
    # memory MOVSS, preserving the original upper96-zero semantics. The
    # thirty-two-byte local frame is private stack memory below native RSP.
    source = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0x20
mov r11, {data}
inc dword ptr [r11]
'''
    source += _guard() + 'camera_recheck:\n' + _guard(recheck=True)
    source += '''mov r11, {data}
inc dword ptr [r11+4]
movss xmm2, dword ptr [r11+0xC]
jmp camera_restore
camera_native:
mov r11, {data}
inc dword ptr [r11+8]
movss xmm2, dword ptr [rip + 0x123456]
camera_restore:
add rsp, 0x20
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {return}
'''
    return source


def build_plan(base: int, production_data: int, visual_data: int,
               appearance_data: int, allocation: int, *, scope_binding=None) -> dict:
    """Pure absolute-address plan. No process access or installation occurs."""
    from build_hinoenma import assemble
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    from capstone.x86_const import X86_REG_RIP
    addresses = (base, production_data, visual_data, appearance_data, allocation)
    if any(type(a) is not int or not 0x10000 <= a < 0x800000000000 for a in addresses):
        raise ValueError('Require absolute user-space addresses')
    if base & 0xFFF or allocation & 0xFFF:
        raise ValueError('Module and camera allocation must be page aligned')
    if scope_binding is not None:
        if not isinstance(scope_binding, dict) or set(scope_binding) != set(BINDING_SCHEMA):
            raise ValueError('Require exact selected/epoch/owner/actor/body binding')
        if (type(scope_binding['selected']) is not int or scope_binding['selected'] not in (0x58E5E, 0x51BE1)
                or type(scope_binding['epoch']) is not int or scope_binding['epoch'] != 1):
            raise ValueError('Require a selected Hino variant and completed epoch1')
        if any(type(scope_binding[k]) is not int or not 0x10000 <= scope_binding[k] < 0x800000000000
               for k in ('owner', 'actor', 'body')):
            raise ValueError('Require absolute user-space binding pointers')
        scope_binding = dict(scope_binding)
    spans = [(production_data, 0x10), (visual_data, 0x3C),
             (appearance_data, 0x40), (allocation, ALLOCATION_SIZE)]
    if any(a < b + m and b < a + n for i, (a, n) in enumerate(spans)
           for b, m in spans[i + 1:]):
        raise ValueError('Camera/private/production data must not overlap')
    for target in (base + HOOK_RVA, base + HOOK_RVA + 8, base + TARGET_RVAS['native_distance']):
        if any(not -(1 << 31) < target - edge < (1 << 31)
               for edge in (allocation, allocation + CODE_CAPACITY)):
            raise ValueError('Camera code must remain in native rel32 range')
    plan = dict(tool_version='menu-camera-distance-private-2',
        allocation_size=ALLOCATION_SIZE, data_offset=DATA_OFFSET,
        own_data_size=OWN_DATA_SIZE, trial_allocation=allocation,
        native_distance=NATIVE_DISTANCE, trial_distance=TRIAL_DISTANCE,
        native_actor_identity_preserved=True, game_properties_read_only=True,
        native_calls=False, production_data_read_only=True, visual_data_read_only=True,
        appearance_data_read_only=True, scope_binding=scope_binding,
        binding_schema={key:dict(offset=offset,size=size) for key,(offset,size) in BINDING_SCHEMA.items()},
        binding_required_for_install=True,
        trial_contract='Fixed verified selection/owner/actor/body; fallback on transition; reinstall after rebinding',
        data_initializations=_initializations(scope_binding),
        targets=dict(TARGET_RVAS, production_data=production_data-base,
            visual_data=visual_data-base, appearance_data=appearance_data-base),
        hooks=[dict(name=HOOK_NAME, rva=HOOK_RVA, original=ORIGINAL, length=8,
            code_offset=0, code_capacity=CODE_CAPACITY, asm=camera_asm(),
            purpose='Compute740 distance only for completed Hino map menu mode4')])
    # Resolve the exact RIP operand from the assembled fallback instruction.
    # The final payload remains one native memory MOVSS of its real constant.
    provisional = assemble(plan, base, allocation)[0]
    disasm = Cs(CS_ARCH_X86, CS_MODE_64); disasm.detail = True
    candidates = [i for i in disasm.disasm(provisional['payload'], allocation)
        if i.mnemonic == 'movss' and any(o.type == 3 and o.mem.base == X86_REG_RIP
            and o.mem.disp == int(_DISPLACEMENT_MARKER, 16) for o in i.operands)]
    if len(candidates) != 1 or candidates[0].size != 8:
        raise ValueError('Expected exactly one eight-byte native MOVSS fallback')
    fallback = candidates[0]
    displacement = base + TARGET_RVAS['native_distance'] - (fallback.address + 8)
    plan['hooks'][0]['asm'] = plan['hooks'][0]['asm'].replace(_DISPLACEMENT_MARKER, hex(displacement))
    final = assemble(plan, base, allocation)[0]
    if len(final['payload']) != len(provisional['payload']):
        raise ValueError('Relocation changed private layout')
    offset = fallback.address - allocation
    instruction = next(disasm.disasm(final['payload'][offset:offset+8], fallback.address))
    if instruction.address + instruction.size + instruction.operands[1].mem.disp != base + TARGET_RVAS['native_distance']:
        raise ValueError('Native MOVSS constant relocation failed')
    plan['fallback_instruction'] = fallback.address
    return plan


def _initializations(binding):
    import struct
    rows = [dict(offset=0xC, size=4, value=TRIAL_DISTANCE,
        hex=struct.pack('<f', TRIAL_DISTANCE).hex(), name='trial_distance')]
    for name, (offset, size) in BINDING_SCHEMA.items():
        value = 0 if binding is None else binding[name]
        rows.append(dict(offset=offset, size=size, value=value,
            hex=value.to_bytes(size, 'little').hex(), name='pinned_' + name))
    return rows


def native_signatures(code=None) -> list[dict]:
    if code is None:
        from code_inspect import CodeImage
        code = CodeImage()
    at = code.file_offset(HOOK_RVA)
    if bytes(code.data[at:at+8]) != bytes.fromhex(ORIGINAL):
        raise ValueError('Native menu distance instruction differs')
    import struct
    at = code.file_offset(TARGET_RVAS['native_distance'])
    if struct.unpack('<f', code.data[at:at+4])[0] != NATIVE_DISTANCE:
        raise ValueError('Native menu distance constant differs')
    return [dict(rva=rva, length=n,
        original=bytes(code.data[code.file_offset(rva):code.file_offset(rva)+n]).hex())
        for rva, n in NATIVE_SPANS]
