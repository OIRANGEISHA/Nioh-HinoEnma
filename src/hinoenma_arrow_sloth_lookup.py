"""Resolve two item casts in the common bank despite Boss action-ID collisions.

The original bank ordering remains intact. Only an accepted Arrowproof64367 or
Sloth4998 request belonging to the live player can resolve41/110 or42/111 in
bank2. This covers both the preflight and common172's native transition lookup.
All rejections tail-call the previous lookup wrapper with its entry ABI intact.
"""
from copy import deepcopy

from hinoenma_arrow_sloth import ITEM_SPECS, SCHEDULE_HEX, EVENT_GUARDS, HELPER_ASM
from hinoenma_special_item_actions import _definition_scope, _schedules, _once

LOOKUP_OFFSET = 0x66800
CARRIER_NAME = 'HE_LivingWeaponDigitNine'
CHANGED_HOOKS = (CARRIER_NAME, 'HE_LadderCommonLookup')
LOOKUP_SCHEDULES = {key: SCHEDULE_HEX[key] for key in (41, 42)}
LOOKUP_EVENT_GUARDS = {key: EVENT_GUARDS[key] for key in (41, 42)}


def _restore(success):
    text = '''ldmxcsr dword ptr [rsp+0x90]
movdqu xmm0, xmmword ptr [rsp+0x20]
movdqu xmm1, xmmword ptr [rsp+0x30]
movdqu xmm2, xmmword ptr [rsp+0x40]
movdqu xmm3, xmmword ptr [rsp+0x50]
movdqu xmm4, xmmword ptr [rsp+0x60]
movdqu xmm5, xmmword ptr [rsp+0x70]
add rsp, 0x168
pop rbx
pop rdi
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''
    return text + ('ret\n' if success else 'jmp {data} + 0x43F00\n')


_PREFIX = '''arrow_sloth_lookup_entry:
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rdi
push rbx
sub rsp, 0x168
movdqu xmmword ptr [rsp+0x20], xmm0
movdqu xmmword ptr [rsp+0x30], xmm1
movdqu xmmword ptr [rsp+0x40], xmm2
movdqu xmmword ptr [rsp+0x50], xmm3
movdqu xmmword ptr [rsp+0x60], xmm4
movdqu xmmword ptr [rsp+0x70], xmm5
stmxcsr dword ptr [rsp+0x90]
cmp edx, 41
je arrow_sloth_lookup_role
cmp edx, 42
jne arrow_sloth_lookup_restore
arrow_sloth_lookup_role:
mov r11, {data}
mov eax, dword ptr [r11+0x1C]
test eax, eax
je arrow_sloth_lookup_restore
mov dword ptr [rsp+0xA0], eax
mov rbx, qword ptr [r11+0x10]
test rbx, rbx
je arrow_sloth_lookup_restore
mov rax, {player_slot}
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
cmp dword ptr [rbx+4], 0x10000
jne arrow_sloth_lookup_restore
mov eax, dword ptr [rbx]
cmp eax, 0x58E5E
je arrow_sloth_lookup_template
cmp eax, 0x51BE1
jne arrow_sloth_lookup_restore
arrow_sloth_lookup_template:
cmp dword ptr [r11+4], eax
jne arrow_sloth_lookup_restore
mov dword ptr [rsp+0x9C], eax
mov qword ptr [rsp+0xA8], rbx
cmp dword ptr [rbx+0xEF0], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rbx+0xE90]
test rax, rax
je arrow_sloth_lookup_restore
mov edx, dword ptr [rbx]
cmp dword ptr [rax], edx
jne arrow_sloth_lookup_restore
cmp dword ptr [rax+0xC], 1
jne arrow_sloth_lookup_restore
mov qword ptr [rsp+0xB0], rax
mov rax, qword ptr [rbx+0x240]
test rax, rax
je arrow_sloth_lookup_restore
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+0x108], rbx
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+0x20], 0
jle arrow_sloth_lookup_restore
mov qword ptr [rsp+0xB8], rax
mov rax, qword ptr [rbx+0x230]
test rax, rax
je arrow_sloth_lookup_restore
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
mov qword ptr [rsp+0xF8], rax
mov rdi, qword ptr [rax+8]
test rdi, rdi
je arrow_sloth_lookup_restore
cmp qword ptr [rdi+0x50], rbx
jne arrow_sloth_lookup_restore
lea rax, [rdi+0x70]
cmp rcx, rax
jne arrow_sloth_lookup_restore
mov qword ptr [rsp+0x88], rdi
cmp dword ptr [rdi+0x550], 1
jne arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x554], 0
jne arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x555], 1
ja arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x556], 1
ja arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x557], 0
jne arrow_sloth_lookup_restore
mov eax, dword ptr [rdi+0x554]
mov dword ptr [rsp+0xF0], eax
cmp qword ptr [rdi+0x558], 0
jne arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x570], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rdi+0x80]
test rax, rax
je arrow_sloth_lookup_restore
mov qword ptr [rsp+0x80], rax
mov ecx, dword ptr [rax+0x130]
test ecx, ecx
je arrow_sloth_lookup_restore
cmp ecx, 0x1000
ja arrow_sloth_lookup_restore
mov dword ptr [rsp+0x108], ecx
mov rdx, qword ptr [rax+0x128]
test rdx, rdx
je arrow_sloth_lookup_restore
mov qword ptr [rsp+0x100], rdx
mov rax, qword ptr [rdi+0x58]
test rax, rax
je arrow_sloth_lookup_restore
mov qword ptr [rsp+0xD8], rax
cmp byte ptr [rax+0x40], 0
je arrow_sloth_lookup_restore
mov ecx, dword ptr [rax]
mov dword ptr [rsp+0x120], ecx
mov rdx, qword ptr [rax+0x20]
test rdx, rdx
je arrow_sloth_lookup_restore
mov qword ptr [rsp+0xE8], rdx
test ecx, ecx
je arrow_sloth_lookup_idle
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x38], rcx
jne arrow_sloth_lookup_restore
cmp dword ptr [rax], 172
jne arrow_sloth_lookup_existing_cast
cmp dword ptr [rdx+0x20], -1
jne arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_definition
arrow_sloth_lookup_existing_cast:
mov ecx, dword ptr [rsp+0x198]
cmp dword ptr [rax], ecx
jne arrow_sloth_lookup_restore
add ecx, 69
cmp dword ptr [rdx+0x20], ecx
jne arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_definition
arrow_sloth_lookup_idle:
cmp byte ptr [rdi+0x555], 1
jne arrow_sloth_lookup_restore
mov rcx, qword ptr [rdi+0x78]
test rcx, rcx
je arrow_sloth_lookup_restore
cmp qword ptr [rax+0x38], rcx
jne arrow_sloth_lookup_restore
mov qword ptr [rsp+0x118], rcx
test byte ptr [rdx], 1
je arrow_sloth_lookup_restore
test byte ptr [rdx+1], 8
jne arrow_sloth_lookup_restore
cmp qword ptr [rdi+0x728], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rdi+0x720]
test rax, rax
je arrow_sloth_lookup_restore
cmp qword ptr [rax], rax
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+8], rax
jne arrow_sloth_lookup_restore
arrow_sloth_lookup_definition:
'''

_SCAN = '''mov eax, dword ptr [rsp+0x94]
cmp dword ptr [rsp+0x198], eax
jne arrow_sloth_lookup_restore
mov r8, qword ptr [rsp+0x80]
mov r9, qword ptr [rsp+0x100]
mov ecx, dword ptr [rsp+0x108]
xor r10d, r10d
arrow_sloth_lookup_scan:
mov rdx, qword ptr [r9]
test rdx, rdx
je arrow_sloth_lookup_scan_next
cmp dword ptr [rdx], eax
jne arrow_sloth_lookup_scan_next
cmp byte ptr [rdx+0x40], 0
je arrow_sloth_lookup_scan_next
cmp qword ptr [rdx+0x38], r8
jne arrow_sloth_lookup_restore
test r10, r10
jne arrow_sloth_lookup_restore
mov r10, rdx
arrow_sloth_lookup_scan_next:
add r9, 8
dec ecx
jne arrow_sloth_lookup_scan
test r10, r10
je arrow_sloth_lookup_restore
mov qword ptr [rsp+0x110], r10
mov rax, qword ptr [r10+0x20]
test rax, rax
je arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x98]
cmp dword ptr [rax+0x20], ecx
jne arrow_sloth_lookup_restore
cmp dword ptr [rax+0x34], -1
jne arrow_sloth_lookup_restore
mov qword ptr [rsp+0xD0], rax
mov edx, dword ptr [rsp+0x94]
call arrow_sloth_lookup_schedule
test al, al
je arrow_sloth_lookup_restore
mov rcx, qword ptr [rbx+0x38]
test rcx, rcx
je arrow_sloth_lookup_restore
cmp dword ptr [rcx+0x50], 1
ja arrow_sloth_lookup_restore
mov qword ptr [rsp+0xE0], rcx
mov edx, dword ptr [rsp+0x98]
call {data} + 0x3E00
test al, al
je arrow_sloth_lookup_restore
'''

_POST = '''mov r11, {data}
mov eax, dword ptr [rsp+0xA0]
cmp dword ptr [r11+0x1C], eax
jne arrow_sloth_lookup_restore
mov rbx, qword ptr [rsp+0xA8]
cmp qword ptr [r11+0x10], rbx
jne arrow_sloth_lookup_restore
mov rax, {player_slot}
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
mov eax, dword ptr [rsp+0x9C]
cmp dword ptr [r11+4], eax
jne arrow_sloth_lookup_restore
cmp dword ptr [rbx], eax
jne arrow_sloth_lookup_restore
cmp dword ptr [rbx+4], 0x10000
jne arrow_sloth_lookup_restore
cmp dword ptr [rbx+0xEF0], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xB0]
cmp qword ptr [rbx+0xE90], rax
jne arrow_sloth_lookup_restore
cmp dword ptr [rax+0xC], 1
jne arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x9C]
cmp dword ptr [rax], ecx
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xB8]
cmp qword ptr [rbx+0x240], rax
jne arrow_sloth_lookup_restore
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+0x108], rbx
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+0x20], 0
jle arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xF8]
cmp qword ptr [rbx+0x230], rax
jne arrow_sloth_lookup_restore
cmp qword ptr [rax], rbx
jne arrow_sloth_lookup_restore
mov rdi, qword ptr [rsp+0x88]
cmp qword ptr [rax+8], rdi
jne arrow_sloth_lookup_restore
cmp qword ptr [rdi+0x50], rbx
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xC0]
cmp qword ptr [rdi+0x548], rax
jne arrow_sloth_lookup_restore
cmp dword ptr [rdi+0x550], 1
jne arrow_sloth_lookup_restore
mov eax, dword ptr [rsp+0xF0]
cmp dword ptr [rdi+0x554], eax
jne arrow_sloth_lookup_restore
cmp qword ptr [rdi+0x558], 0
jne arrow_sloth_lookup_restore
cmp byte ptr [rdi+0x570], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xE0]
cmp qword ptr [rbx+0x38], rax
jne arrow_sloth_lookup_restore
cmp dword ptr [rax+0x50], 1
ja arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xD8]
cmp qword ptr [rdi+0x58], rax
jne arrow_sloth_lookup_restore
cmp byte ptr [rax+0x40], 0
je arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x120]
cmp dword ptr [rax], ecx
jne arrow_sloth_lookup_restore
mov rdx, qword ptr [rsp+0xE8]
cmp qword ptr [rax+0x20], rdx
jne arrow_sloth_lookup_restore
test ecx, ecx
je arrow_sloth_lookup_post_idle
mov rcx, qword ptr [rsp+0x80]
cmp qword ptr [rax+0x38], rcx
jne arrow_sloth_lookup_restore
cmp dword ptr [rax], 172
jne arrow_sloth_lookup_post_cast
cmp dword ptr [rdx+0x20], -1
jne arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_post_bank
arrow_sloth_lookup_post_cast:
mov ecx, dword ptr [rsp+0x94]
cmp dword ptr [rax], ecx
jne arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x98]
cmp dword ptr [rdx+0x20], ecx
jne arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_post_bank
arrow_sloth_lookup_post_idle:
mov rcx, qword ptr [rsp+0x118]
cmp qword ptr [rdi+0x78], rcx
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+0x38], rcx
jne arrow_sloth_lookup_restore
test byte ptr [rdx], 1
je arrow_sloth_lookup_restore
test byte ptr [rdx+1], 8
jne arrow_sloth_lookup_restore
cmp qword ptr [rdi+0x728], 0
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rdi+0x720]
test rax, rax
je arrow_sloth_lookup_restore
cmp qword ptr [rax], rax
jne arrow_sloth_lookup_restore
cmp qword ptr [rax+8], rax
jne arrow_sloth_lookup_restore
arrow_sloth_lookup_post_bank:
mov r8, qword ptr [rsp+0x80]
cmp qword ptr [rdi+0x80], r8
jne arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x108]
cmp dword ptr [r8+0x130], ecx
jne arrow_sloth_lookup_restore
mov r9, qword ptr [rsp+0x100]
cmp qword ptr [r8+0x128], r9
jne arrow_sloth_lookup_restore
mov eax, dword ptr [rsp+0x94]
xor r10d, r10d
arrow_sloth_lookup_post_scan:
mov rdx, qword ptr [r9]
test rdx, rdx
je arrow_sloth_lookup_post_scan_next
cmp dword ptr [rdx], eax
jne arrow_sloth_lookup_post_scan_next
cmp byte ptr [rdx+0x40], 0
je arrow_sloth_lookup_post_scan_next
cmp qword ptr [rdx+0x38], r8
jne arrow_sloth_lookup_restore
test r10, r10
jne arrow_sloth_lookup_restore
mov r10, rdx
arrow_sloth_lookup_post_scan_next:
add r9, 8
dec ecx
jne arrow_sloth_lookup_post_scan
cmp qword ptr [rsp+0x110], r10
jne arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xD0]
cmp qword ptr [r10+0x20], rax
jne arrow_sloth_lookup_restore
mov ecx, dword ptr [rsp+0x98]
cmp dword ptr [rax+0x20], ecx
jne arrow_sloth_lookup_restore
cmp dword ptr [rax+0x34], -1
jne arrow_sloth_lookup_restore
mov edx, dword ptr [rsp+0x94]
call arrow_sloth_lookup_schedule
test al, al
je arrow_sloth_lookup_restore
mov rax, qword ptr [rsp+0xC8]
'''


def _post_definition():
    """Recheck exact definition bytes after the resource callbacks, without calls."""
    text = ''
    for ident, *_ in ITEM_SPECS:
        text += f'cmp dword ptr [rdi+0x548], {ident}\nje arrow_sloth_lookup_post_definition_{ident}\n'
    text += 'jmp arrow_sloth_lookup_restore\n'
    for ident, kind, sub, cat, flags, effects, spawn, action, motion, query in ITEM_SPECS:
        text += f'arrow_sloth_lookup_post_definition_{ident}:\n'
        for off, value in ((0, ident), (4, kind | sub << 8), (0x104, flags),
                           (0x10C, cat), *((0x110+i*4, v) for i, v in enumerate(effects)),
                           (0x11C, spawn)):
            width = 'word' if off == 4 else 'dword'
            text += f'cmp {width} ptr [rax+{off}], {value}\njne arrow_sloth_lookup_restore\n'
        text += 'jmp arrow_sloth_lookup_success\n'
    return text


LOOKUP_ASM = (_PREFIX
    + _definition_scope(ITEM_SPECS).replace('special_item_', 'arrow_sloth_lookup_')
    + _SCAN + _POST + _post_definition()
    + '''arrow_sloth_lookup_success:
mov rax, qword ptr [rsp+0x110]
mov qword ptr [rsp+0x1A8], rax
mov r8, qword ptr [rsp+0x190]
test r8, r8
je arrow_sloth_lookup_success_restore
mov dword ptr [r8], 2
arrow_sloth_lookup_success_restore:
''' + _restore(True)
    + 'arrow_sloth_lookup_restore:\n' + _restore(False)
    + _schedules(LOOKUP_SCHEDULES, LOOKUP_EVENT_GUARDS).replace(
        'special_item_', 'arrow_sloth_lookup_'))


def apply_arrow_sloth_lookup(previous):
    """Pure transform; add a scoped resolver in unused executable carrier space."""
    if (len(previous['hooks']) != 82 or previous.get('arrow_sloth_revision') != 1
            or previous.get('arrow_sloth_lookup_revision')
            or previous.get('data_offset') != 0xF000):
        raise ValueError('Expected validated82-hook Arrowproof/Sloth revision1')
    plan = deepcopy(previous)
    carrier = next(h for h in plan['hooks'] if h['name'] == CARRIER_NAME)
    lookup = next(h for h in plan['hooks'] if h['name'] == 'HE_LadderCommonLookup')
    if ((carrier['code_offset'], carrier['code_capacity']) != (0x61000, 0x8000)
            or not carrier['asm'].endswith(HELPER_ASM)
            or (lookup['code_offset'], lookup['code_capacity']) != (0xE800, 0x800)):
        raise ValueError('Unexpected prior item/lookup carrier layout')
    anchor = 'jmp {data} + 0x43F00\n'
    if not lookup['asm'].startswith(anchor):
        raise ValueError('Expected the exact previous scoped lookup entry')
    lookup['asm'] = _once(lookup['asm'], anchor, 'jmp {data} + 0x57800\n')
    from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
    ks = Ks(KS_ARCH_X86, KS_MODE_64)
    values = {key: 0x140000000 + rva for key, rva in plan['targets'].items()}
    values['data'] = 0x144000000 + plan['data_offset']
    values['return'] = 0x140000000 + carrier['rva'] + carrier['length']
    old, _ = ks.asm(carrier['asm'].format(**values), addr=0x144000000+carrier['code_offset'])
    padding = LOOKUP_OFFSET - carrier['code_offset'] - len(old)
    if padding < 0:
        raise ValueError('Existing item helper overlaps scoped lookup region')
    carrier['asm'] += '\n' + 'nop\n' * padding + LOOKUP_ASM
    for hook in (carrier, lookup):
        values['return'] = 0x140000000 + hook['rva'] + hook['length']
        code, _ = ks.asm(hook['asm'].format(**values), addr=0x144000000+hook['code_offset'])
        if len(code) > hook['code_capacity']:
            raise ValueError('Scoped item lookup exceeds carrier: ' + hook['name'])
        if hook is carrier and bytes(code[:len(old)]) != bytes(old):
            raise ValueError('Previous carrier code was changed')
    carrier['purpose'] += '; scoped common41/42 item lookup after complete owner/resource checks'
    plan.update(arrow_sloth_lookup_revision=1,
                arrow_sloth_lookup_direct_actor_item_inventory_save_writes=False,
                arrow_sloth_lookup_gameplay_confirmation_pending=True)
    return plan
