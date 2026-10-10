"""Uninstalled map-display visual-resource construction trial.

William's logical actor identity, native spawner arguments and constructor
flags remain native.  Only the coherent visual-resource portion of the map
actor constructor sees Hino-Enma's package.  The original William package is
restored before AI/control-resource creation.  Every per-call binding lives
in the native spawner wrapper's own stack frame, not in global scratch.
"""
from __future__ import annotations

from menu_preview_preload_hooks import (
    TARGET_RVAS as PRELOAD_TARGETS, preload_asm, native_signatures as preload_signatures,
    _pointer,
)

ALLOCATION_SIZE, DATA_OFFSET = 0x5000, 0x4000
MAX_WAIT_FRAMES = 480
WRAPPER_FRAME_SIZE = 0x120
HOOKS = (
    ('HE_MapVisualReadyPrivate', 0x8C536F, '8B 46 1C 45 33 E4', 0),
    ('HE_MapVisualSpawnPrivate', 0x8C5407, 'E8 54 FD E8 FF', 0x1000),
    ('HE_MapVisualResourcePrivate', 0x7604E7, '48 85 C0 0F 84 50 03 00 00', 0x2000),
    ('HE_MapVisualRestorePrivate', 0x760778, '49 8B 85 C0 00 00 00', 0x3000),
)
TARGET_RVAS = dict(PRELOAD_TARGETS, package_handles=0x1766110,
    character_ready=0x8B0B10, package_handle=0xF90930, spawn=0x755160,
    ctor_return=0x75525E, no_visual_resources=0x760840,
    map_wait=0x8C61CA)
NATIVE_SPANS = ((0x8C5407, 5), (0x7604E7, 9), (0x760778, 7),
    (0x8B0B10, 595), (0xF90930, 74), (0x755160, 0x17A),
    (0x75FC80, 0xBC0), (0x8C61CA, 0x29))
STATUS = {'requested': 1, 'tracked': 2, 'bad_package': 3, 'bad_world': 4,
          'bad_ids': 5, 'fallback': 6, 'ready': 7}
# Private counters +0C requests,+10 tracked,+1C waited frames,+24 timeouts,
# +28 wrapper preparations,+2C visual swaps,+30 restores; lock is +20.
# +38 records an observed state-1 epoch, resetting the same-owner ticket
# when native BaseMode returns to construction state 0 after map unloading.


def _replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('Preload-only source boundary changed')
    return source.replace(old, new)


def ready_asm():
    """Use the native dependency-ready predicate; bounded wait never hangs map."""
    source = preload_asm()
    source = _replace_once(source,
        'cmp dword ptr [rsi+0x1C], 1\nja preload_probe_done',
        'cmp dword ptr [rsi+0x1C], 1\nje visual_ready_epoch_seen\n'
        'cmp dword ptr [rsi+0x1C], 0\njne preload_probe_done')
    begin = 'mov rax, {player_slot}\nmov rax, qword ptr [rax]\n'
    end = 'mov rax, {production_data}\n'
    first, last = source.index(begin), source.index(end, source.index(begin))
    source = source[:first] + '''mov rax, {player_slot}
cmp qword ptr [rax], 0
jne preload_probe_done
''' + source[last:]
    source = _replace_once(source,
        'je preload_probe_unlock\npreload_probe_first:',
        'je visual_ready_check\npreload_probe_first:')
    source = _replace_once(source,
        'cmp qword ptr [r11], rsi\n',
        'cmp dword ptr [r11+0x38], 0\njne preload_probe_first\n'
        'cmp qword ptr [r11], rsi\n')
    source = _replace_once(source,
        'inc dword ptr [r11+0x1C]',
        'mov dword ptr [r11+0x1C], 0\nmov dword ptr [r11+0x38], 0')
    source = _replace_once(source,
        'call {preload}\njmp preload_probe_unlock',
        'call {preload}\njmp visual_ready_check')
    readiness = '''visual_ready_check:
mov r11, {data}
cmp dword ptr [r11+0x14], 6
je preload_probe_unlock
mov ecx, dword ptr [rsp+0x80]
call {character_ready}
test al, al
jne visual_ready_yes
mov r11, {data}
inc dword ptr [r11+0x1C]
cmp dword ptr [r11+0x1C], 480
jae visual_ready_timeout
mov dword ptr [rsp+0x88], 1
jmp preload_probe_unlock
visual_ready_timeout:
mov dword ptr [r11+0x14], 6
inc dword ptr [r11+0x24]
jmp preload_probe_unlock
visual_ready_yes:
mov r11, {data}
mov dword ptr [r11+0x14], 7
'''
    source = _replace_once(source, 'preload_probe_unlock:\n', readiness + '''preload_probe_unlock:
mov r11, {data}
cmp dword ptr [r11+0x14], 3
jb visual_ready_unlock
cmp dword ptr [r11+0x14], 5
ja visual_ready_unlock
mov dword ptr [r11+0x14], 6
inc dword ptr [r11+0x24]
visual_ready_unlock:
''')
    # Tracked success falls through to the readiness check above; failed
    # package/tree guards jump directly to unlock and take native fallback.
    source = _replace_once(source,
        'movdqu xmmword ptr [rsp+0x70], xmm5\n',
        'movdqu xmmword ptr [rsp+0x70], xmm5\nmov dword ptr [rsp+0x88], 0\n')
    source = _replace_once(source,
        'add rsp, 0xA0\npop r11',
        'cmp dword ptr [rsp+0x88], 0\njne visual_ready_wait_restore\nadd rsp, 0xA0\npop r11')
    # The wait path restores the exact saved entry state before jumping to
    # the native early epilogue; it does not execute any map-spawn code.
    source += '''visual_ready_wait_restore:
add rsp, 0xA0
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {map_wait}
visual_ready_epoch_seen:
mov r11, {data}
cmp qword ptr [r11], rsi
jne preload_probe_done
mov dword ptr [r11+0x38], 1
jmp preload_probe_done
'''
    return source


def _wrapper_restore():
    return '''movdqu xmm0, xmmword ptr [rsp+0x90]
movdqu xmm1, xmmword ptr [rsp+0xA0]
movdqu xmm2, xmmword ptr [rsp+0xB0]
movdqu xmm3, xmmword ptr [rsp+0xC0]
movdqu xmm4, xmmword ptr [rsp+0xD0]
movdqu xmm5, xmmword ptr [rsp+0xE0]
push qword ptr [rsp+0x88]
popfq
mov r11, qword ptr [rsp+0x80]
mov r10, qword ptr [rsp+0x78]
mov r9, qword ptr [rsp+0x70]
mov r8, qword ptr [rsp+0x68]
mov rdx, qword ptr [rsp+0x60]
mov rcx, qword ptr [rsp+0x58]
mov rax, qword ptr [rsp+0x50]
'''


def spawn_asm():
    source = '''pushfq
sub rsp, 0x118
mov qword ptr [rsp+0x50], rax
mov qword ptr [rsp+0x58], rcx
mov qword ptr [rsp+0x60], rdx
mov qword ptr [rsp+0x68], r8
mov qword ptr [rsp+0x70], r9
mov qword ptr [rsp+0x78], r10
mov qword ptr [rsp+0x80], r11
mov rax, qword ptr [rsp+0x118]
mov qword ptr [rsp+0x88], rax
movdqu xmmword ptr [rsp+0x90], xmm0
movdqu xmmword ptr [rsp+0xA0], xmm1
movdqu xmmword ptr [rsp+0xB0], xmm2
movdqu xmmword ptr [rsp+0xC0], xmm3
movdqu xmmword ptr [rsp+0xD0], xmm4
movdqu xmmword ptr [rsp+0xE0], xmm5
mov qword ptr [rsp+0x20], 0
mov qword ptr [rsp+0x28], rsi
mov qword ptr [rsp+0x30], 0
mov qword ptr [rsp+0x38], 0
mov qword ptr [rsp+0x40], 0
mov qword ptr [rsp+0x48], 0
'''
    source += _pointer('rsi', 'visual_spawn_native') + '''mov rax, {base_mode_vtable}
cmp qword ptr [rsi], rax
jne visual_spawn_native
cmp dword ptr [rsi+0x1C], 0
jne visual_spawn_native
cmp qword ptr [rsp+0x58], 100
jne visual_spawn_native
cmp qword ptr [rsp+0x60], 1
jne visual_spawn_native
cmp qword ptr [rsp+0x68], 0
jne visual_spawn_native
cmp qword ptr [rsp+0x70], 0
jne visual_spawn_native
mov rax, {player_slot}
cmp qword ptr [rax], 0
jne visual_spawn_native
mov rax, {production_data}
mov eax, dword ptr [rax]
cmp eax, 0x58E5E
je visual_spawn_selected
cmp eax, 0x51BE1
jne visual_spawn_native
visual_spawn_selected:
mov dword ptr [rsp+0x48], eax
mov r11, {data}
cmp qword ptr [r11], rsi
jne visual_spawn_check_ready
cmp dword ptr [r11+8], eax
jne visual_spawn_check_ready
cmp dword ptr [r11+0x14], 6
je visual_spawn_native
visual_spawn_check_ready:
mov ecx, eax
call {character_ready}
test al, al
je visual_spawn_native
mov rax, {package_ids}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'visual_spawn_native') + '''mov rax, qword ptr [rcx+0x10]
''' + _pointer('rax', 'visual_spawn_native') + '''mov rax, qword ptr [rax+8]
''' + _pointer('rax', 'visual_spawn_native') + '''mov edx, dword ptr [rsp+0x48]
xor r8d, r8d
call {package_get}
cmp dword ptr [rsp+0x48], 0x58E5E
jne visual_spawn_variant_package
cmp eax, 232
jne visual_spawn_native
jmp visual_spawn_package_ok
visual_spawn_variant_package:
cmp eax, 233
jne visual_spawn_native
visual_spawn_package_ok:
mov edx, eax
mov rax, {package_handles}
mov rcx, qword ptr [rax]
'''
    source += _pointer('rcx', 'visual_spawn_native') + '''mov rax, qword ptr [rcx]
''' + _pointer('rax', 'visual_spawn_native') + '''mov rax, qword ptr [rax+8]
''' + _pointer('rax', 'visual_spawn_native') + '''xor r8d, r8d
call {package_handle}
''' + _pointer('rax', 'visual_spawn_native') + '''cmp byte ptr [rax+0x160], 0
je visual_spawn_native
mov rcx, qword ptr [rax+8]
''' + _pointer('rcx', 'visual_spawn_native') + '''mov qword ptr [rsp+0x30], rax
mov dword ptr [rsp+0x20], 1
mov r11, {data}
inc dword ptr [r11+0x28]
visual_spawn_native:
'''
    source += _wrapper_restore() + '''call {spawn}
visual_spawn_continuation:
lea rsp, [rsp+0x120]
jmp {return}
'''
    return source


def _ctor_scope(rejected, *, restore=False):
    source = '''mov rax, {ctor_return}
cmp qword ptr [rbp+0x57], rax
jne REJECT
mov rax, {wrapper_continuation}
cmp qword ptr [rbp+0xC7], rax
jne REJECT
'''.replace('REJECT', rejected)
    if restore:
        source += f'''cmp dword ptr [rbp+0xEF], 2
jne {rejected}
cmp qword ptr [rbp+0x107], rsi
jne {rejected}
cmp qword ptr [rbp+0xFF], r13
jne {rejected}
mov rax, qword ptr [rbp+0x10F]
'''
        return source + _pointer('rax', rejected)
    source += f'''cmp dword ptr [rbp+0xEF], 1
jne {rejected}
cmp qword ptr [rbp+0x107], 0
jne {rejected}
'''
    source += _pointer('rsi', rejected) + f'''
cmp dword ptr [rsi], 100
jne {rejected}
cmp dword ptr [rsi+4], 0x10000
jne {rejected}
cmp byte ptr [rsi+0x434], 0
jne {rejected}
cmp byte ptr [rsi+0x435], 0
jne {rejected}
mov rax, qword ptr [rbp+0xF7]
'''
    source += _pointer('rax', rejected) + f'''mov rcx, {{base_mode_vtable}}
cmp qword ptr [rax], rcx
jne {rejected}
cmp dword ptr [rax+0x1C], 0
jne {rejected}
mov ecx, dword ptr [rbp+0x117]
cmp ecx, 0x58E5E
je visual_ctor_selected
cmp ecx, 0x51BE1
jne {rejected}
visual_ctor_selected:
mov rax, {{production_data}}
cmp dword ptr [rax], ecx
jne {rejected}
mov rax, qword ptr [rbp+0xFF]
'''
    source += _pointer('rax', rejected) + f'''cmp byte ptr [rax+0x160], 0
je {rejected}
mov rcx, qword ptr [rax+8]
'''
    return source + _pointer('rcx', rejected)


def _save_gpr():
    return 'pushfq\npush rax\npush rcx\npush rdx\npush r8\npush r9\npush r10\npush r11\n'


def _restore_gpr():
    return 'pop r11\npop r10\npop r9\npop r8\npop rdx\npop rcx\npop rax\npopfq\n'


def ctor_asm():
    source = _save_gpr() + '''cmp rax, r13
jne visual_ctor_done
'''
    source += _pointer('r13', 'visual_ctor_done')
    source += _ctor_scope('visual_ctor_done') + '''mov qword ptr [rbp+0x40+0xCF], r13
mov qword ptr [rbp+0x38+0xCF], rsi
mov r13, rax
mov dword ptr [rbp+0x20+0xCF], 2
mov r11, {data}
inc dword ptr [r11+0x2C]
visual_ctor_done:
'''
    return source + _restore_gpr() + '''test rax, rax
je visual_ctor_no_resources
jmp {return}
visual_ctor_no_resources:
jmp {no_visual_resources}
'''


def restore_asm():
    source = _save_gpr() + _ctor_scope('visual_restore_done', restore=True)
    source += '''mov r13, rax
mov dword ptr [rbp+0x20+0xCF], 3
mov r11, {data}
inc dword ptr [r11+0x30]
visual_restore_done:
'''
    return source + _restore_gpr() + '''mov rax, qword ptr [r13+0xC0]
jmp {return}
'''


def build_plan(base: int, production_data: int, allocation: int) -> dict:
    from build_hinoenma import assemble
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    for address in (base, production_data, allocation):
        if not isinstance(address, int) or not 0x10000 <= address < 0x800000000000:
            raise ValueError('Require absolute user-space addresses')
    if base & 0xFFF or allocation & 0xFFF:
        raise ValueError('Module and trial allocation must be page aligned')
    if allocation <= production_data < allocation + ALLOCATION_SIZE:
        raise ValueError('Trial allocation overlaps production data')
    # Every CALL/JMP encoded by the private source is a signed rel32. Check
    # both ends of the code arena before asking Keystone to encode them.
    relative_targets = [base + rva for _, rva, _, _ in HOOKS]
    relative_targets += [base + TARGET_RVAS[key] for key in (
        'package_get', 'package_tracked', 'preload', 'character_ready',
        'package_handle', 'spawn', 'no_visual_resources', 'map_wait')]
    if any(not -(1 << 31) < target - arena < (1 << 31)
           for target in relative_targets for arena in (allocation, allocation + DATA_OFFSET)):
        raise ValueError('All private code must stay in native relative branch range')
    plan = dict(tool_version='map-visual-resource-private-1',
        allocation_size=ALLOCATION_SIZE, data_offset=DATA_OFFSET,
        trial_allocation=allocation, production_data_read_only=True,
        native_actor_identity_preserved=True, native_flags_preserved=True,
        native_cpose_preserved=True, max_wait_frames=MAX_WAIT_FRAMES,
        wrapper_frame_size=WRAPPER_FRAME_SIZE,
        targets=dict(TARGET_RVAS, production_data=production_data - base), hooks=[])
    sources = (ready_asm(), spawn_asm(), ctor_asm(), restore_asm())
    plan['hooks'] = [dict(name=name, rva=rva, original=original,
        length=len(bytes.fromhex(original)), code_offset=offset,
        code_capacity=0x1000, asm=sources[index],
        purpose='Private scoped map display visual-resource construction')
        for index, (name, rva, original, offset) in enumerate(HOOKS)]
    # Resolve the unique wrapper continuation from actual assembled CALL bytes
    # rather than relying on source length or a magic cross-hook displacement.
    wrapper_only = dict(plan, hooks=[plan['hooks'][1]])
    wrapper = assemble(wrapper_only, base, allocation)[0]
    calls = [i for i in Cs(CS_ARCH_X86, CS_MODE_64).disasm(wrapper['payload'], wrapper['target'])
             if i.mnemonic == 'call' and int(i.op_str, 16) == base + TARGET_RVAS['spawn']]
    if len(calls) != 1 or calls[0].size != 5:
        raise ValueError('Wrapper must contain exactly one direct native spawner call')
    continuation = calls[0].address + calls[0].size
    plan['targets']['wrapper_continuation'] = continuation - base
    plan['wrapper_continuation'] = continuation
    return plan


def native_signatures(code=None):
    if code is None:
        from code_inspect import CodeImage
        code = CodeImage()
    guards = preload_signatures(code)
    for _, rva, original, _ in HOOKS:
        at = code.file_offset(rva)
        if bytes(code.data[at:at + len(bytes.fromhex(original))]) != bytes.fromhex(original):
            raise ValueError(f'Visual trial native overwrite differs at {rva:X}')
    for rva, length in NATIVE_SPANS:
        at = code.file_offset(rva)
        guards.append(dict(rva=rva, length=length, original=bytes(code.data[at:at + length]).hex()))
    return guards
