"""Private, preload-only BaseMode probe; never installs or modifies a process.

The native William display actor is deliberately kept intact.  A scoped hook
requests Hino-Enma's resources once per BaseMode owner/template, then replays
the exact original instructions.  This is evidence preparation, not a model
replacement or a release feature.  Game-owned memory is read only from this
hook; the existing native preload function manages its own resource state.
"""
from __future__ import annotations

ALLOCATION_SIZE = 0x3000
DATA_OFFSET = 0x2000
CODE_CAPACITY = 0x2000
HOOK_RVA = 0x8C536F
ORIGINAL = '8B 46 1C 45 33 E4'
TARGET_RVAS = {
    'base_mode_vtable': 0x11FB588,
    'player_slot': 0x18A0490,
    'package_ids': 0x1766128,
    'world_manager': 0x18715E0,
    'package_get': 0xF90760,
    'package_tracked': 0x8AEEB0,
    'preload': 0x8B13E0,
}
# A code snapshot guard covers complete helpers; fixed prefixes independently
# establish each helper's expected entry and the six-byte overwrite boundary.
FIXED_SIGNATURES = (
    ('BaseModeHook', HOOK_RVA, ORIGINAL),
    ('BaseModePrologue', 0x8C5330, '48 8B C4 55 53 56 41 54 41 57 48 8D 68 88 48 81 EC 50 01 00 00'),
    ('PackageIdGetter', 0xF90760, '41 0F B6 C0 4C 8B 41 10 89 54 24 08 89 44 24 0C'),
    ('PackageTrackedGetter', 0x8AEEB0, '4C 8B 89 68 05 00 00 4D 8B C1 49 8B 41 08'),
    ('PreloadEntry', 0x8B13E0, '48 89 5C 24 10 48 89 74 24 18 55 57 41 55 41 56 41 57'),
)
NATIVE_SPANS = ((HOOK_RVA, 6), (0x8C5330, 0x10A),
                (0xF90760, 0x57), (0x8AEEB0, 0x77), (0x8B13E0, 0x420))
# Private data: owner Q0, selected D8, preload calls DC, tracked skips D10,
# status D14, package D18, attempts D1C, atomic in-flight lock D20.
STATUS = {'requested': 1, 'already_tracked': 2, 'unexpected_package': 3,
          'missing_world': 4, 'missing_id_manager': 5}


def _pointer(register: str, rejected: str = 'preload_probe_done') -> str:
    return f'''cmp {register}, 0x10000
jb {rejected}
mov r10, 0x800000000000
cmp {register}, r10
jae {rejected}
'''


def preload_asm() -> str:
    # At this exact native site RSP is 16-byte aligned (five pushes and SUB150
    # in BaseMode). Eight pushes retain alignment; A0 provides shadow space,
    # six XMM saves and two local words, without touching the caller's frame.
    save = '''pushfq
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
'''
    guards = _pointer('rsi') + '''mov rax, {base_mode_vtable}
cmp qword ptr [rsi], rax
jne preload_probe_done
cmp dword ptr [rsi+0x1C], 1
ja preload_probe_done
mov rax, {player_slot}
mov rax, qword ptr [rax]
''' + _pointer('rax') + '''cmp dword ptr [rax], 0x64
jne preload_probe_done
cmp dword ptr [rax+4], 0x10000
jne preload_probe_done
mov rax, {production_data}
mov eax, dword ptr [rax]
cmp eax, 0x58E5E
je preload_probe_selected
cmp eax, 0x51BE1
jne preload_probe_done
preload_probe_selected:
mov dword ptr [rsp+0x80], eax
mov r11, {data}
xor eax, eax
mov ecx, 1
lock cmpxchg dword ptr [r11+0x20], ecx
jne preload_probe_done
cmp qword ptr [r11], rsi
jne preload_probe_first
mov eax, dword ptr [rsp+0x80]
cmp dword ptr [r11+8], eax
je preload_probe_unlock
preload_probe_first:
mov qword ptr [r11], rsi
mov eax, dword ptr [rsp+0x80]
mov dword ptr [r11+8], eax
inc dword ptr [r11+0x1C]
mov dword ptr [r11+0x14], 5
mov dword ptr [r11+0x18], 0xFFFF
mov rax, {package_ids}
mov rcx, qword ptr [rax]
'''
    lookup = _pointer('rcx', 'preload_probe_unlock') + '''mov rax, qword ptr [rcx+0x10]
''' + _pointer('rax', 'preload_probe_unlock') + '''mov rax, qword ptr [rax+8]
''' + _pointer('rax', 'preload_probe_unlock') + '''mov edx, dword ptr [rsp+0x80]
xor r8d, r8d
call {package_get}
mov dword ptr [rsp+0x84], eax
mov r11, {data}
mov dword ptr [r11+0x18], eax
mov dword ptr [r11+0x14], 3
mov edx, dword ptr [rsp+0x80]
cmp edx, 0x58E5E
jne preload_probe_variant_package
cmp eax, 232
jne preload_probe_unlock
jmp preload_probe_package_ok
preload_probe_variant_package:
cmp eax, 233
jne preload_probe_unlock
preload_probe_package_ok:
mov dword ptr [r11+0x14], 4
mov rax, {world_manager}
mov rcx, qword ptr [rax]
'''
    world = _pointer('rcx', 'preload_probe_unlock')
    for offset in (0x568, 0x578):
        world += f'mov rax, qword ptr [rcx+{hex(offset)}]\n'
        world += _pointer('rax', 'preload_probe_unlock')
        world += 'mov rax, qword ptr [rax+8]\n'
        world += _pointer('rax', 'preload_probe_unlock')
    request = '''mov edx, dword ptr [rsp+0x84]
call {package_tracked}
test al, al
jne preload_probe_tracked
mov r11, {data}
mov dword ptr [r11+0x14], 1
inc dword ptr [r11+0x0C]
mov ecx, dword ptr [rsp+0x80]
mov edx, ecx
xor r8d, r8d
call {preload}
jmp preload_probe_unlock
preload_probe_tracked:
mov r11, {data}
mov dword ptr [r11+0x14], 2
inc dword ptr [r11+0x10]
preload_probe_unlock:
mov r11, {data}
mov dword ptr [r11+0x20], 0
preload_probe_done:
movdqu xmm0, xmmword ptr [rsp+0x20]
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
mov eax, dword ptr [rsi+0x1C]
xor r12d, r12d
jmp {return}
'''
    return save + guards + lookup + world + request


def build_plan(base: int, production_data: int, allocation: int) -> dict:
    """Return an uninstalled plan compatible with build_hinoenma.assemble.

    production_data is the actual core data pointer, not the core allocation.
    All three arguments are absolute addresses; this function never reads a
    process, allocates memory, writes a profile or performs an installation.
    """
    for address in (base, production_data, allocation):
        if not isinstance(address, int) or not 0x10000 <= address < 0x800000000000:
            raise ValueError('Require valid absolute user-space pointers')
    if base & 0xFFF or allocation & 0xFFF:
        raise ValueError('Module and private allocation must be page aligned')
    if allocation <= production_data < allocation + ALLOCATION_SIZE:
        raise ValueError('Private allocation must not overlap production data')
    if not -(1 << 31) <= allocation - (base + HOOK_RVA + 5) < (1 << 31):
        raise ValueError('Private allocation must be within the jump range')
    return {
        'tool_version': 'menu-preview-preload-private-1',
        'allocation_size': ALLOCATION_SIZE, 'data_offset': DATA_OFFSET,
        'trial_allocation': allocation,
        'preload_only': True, 'changes_display_actor': False,
        'production_data_read_only': True,
        'targets': dict(TARGET_RVAS, production_data=production_data - base),
        'private_status_values': dict(STATUS),
        'hooks': [dict(name='HE_MenuPreviewPreloadPrivate', rva=HOOK_RVA,
            original=ORIGINAL, length=6, code_offset=0,
            code_capacity=CODE_CAPACITY, asm=preload_asm(),
            purpose='Preload-only readback preparation for current map display')],
    }


def native_signatures(code=None) -> list[dict]:
    """Bind full native helper guards to the validated frozen CodeImage."""
    if code is None:
        from code_inspect import CodeImage
        code = CodeImage()
    for name, rva, expected in FIXED_SIGNATURES:
        at = code.file_offset(rva)
        raw = bytes(code.data[at:at + len(bytes.fromhex(expected))])
        if raw != bytes.fromhex(expected):
            raise ValueError(f'Fixed native entry differs: {name}')
    return [dict(rva=rva, length=length,
        original=bytes(code.data[code.file_offset(rva):
            code.file_offset(rva) + length]).hex()) for rva, length in NATIVE_SPANS]
