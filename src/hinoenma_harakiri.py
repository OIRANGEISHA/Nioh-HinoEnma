"""Accept only the confirmed Harakiri Sword request at the native item gate.

Native eligibility/confirmation precede this gate. Native effect15, death,
inventory commit, request reset and respawn remain in game code. No actor,
inventory, HP, mission or save writes are emitted by this predicate.
"""
from copy import deepcopy

HELPER_OFFSET = 0x1E400
CARRIER_NAME = 'HE_InherentDirectElement'
CHANGED_HOOKS = ('HE_Consumables', CARRIER_NAME)
NATIVE_SPANS = ((0x738140, 0x2F), (0x75188F, 0xB7), (0x751951, 0x40),
                (0x767080, 0x98), (0xA84A9B, 0x71))

HELPER = '''harakiri_helper:
cmp dword ptr [rdi+0x54C], 10
je harakiri_exact_request
mov rax, {data}
sub rax, 0x92C0
jmp rax
harakiri_exact_request:
push rbx
push rsi
sub rsp, 0x28
cmp dword ptr [rdi+0x548], 34209
jne harakiri_no
cmp dword ptr [rdi+0x550], 1
jne harakiri_no
cmp dword ptr [rdi+0x554], 0x100
jne harakiri_no
cmp byte ptr [rdi+0x570], 0
jne harakiri_no
mov rsi, qword ptr [rdi+0x50]
test rsi, rsi
je harakiri_no
mov r11, {data}
cmp qword ptr [r11+0x10], rsi
jne harakiri_no
mov eax, dword ptr [rsi]
cmp eax, dword ptr [r11+4]
jne harakiri_no
cmp eax, 0x58E5E
je harakiri_template
cmp eax, 0x51BE1
jne harakiri_no
harakiri_template:
cmp dword ptr [rsi+4], 0x10000
jne harakiri_no
cmp dword ptr [rsi+0xEF0], 0
jne harakiri_no
mov r11, {player_slot}
cmp qword ptr [r11], rsi
jne harakiri_no
mov r11, qword ptr [rsi+0xE90]
test r11, r11
je harakiri_no
cmp dword ptr [r11], eax
jne harakiri_no
cmp dword ptr [r11+0xC], 1
jne harakiri_no
mov r11, qword ptr [rsi+0x230]
test r11, r11
je harakiri_no
cmp qword ptr [r11], rsi
jne harakiri_no
cmp qword ptr [r11+8], rdi
jne harakiri_no
mov r11, qword ptr [rsi+0x240]
test r11, r11
je harakiri_no
cmp qword ptr [r11], rsi
jne harakiri_no
cmp qword ptr [r11+0x108], rsi
jne harakiri_no
cmp qword ptr [r11+0x20], 0
jle harakiri_no
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je harakiri_no
mov rcx, qword ptr [rcx+0x20]
test rcx, rcx
je harakiri_no
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je harakiri_no
mov edx, 34209
call {item_lookup}
test rax, rax
je harakiri_no
cmp dword ptr [rax], 34209
jne harakiri_no
cmp word ptr [rax+4], 3
jne harakiri_no
cmp dword ptr [rax+0x104], 0x4047
jne harakiri_no
cmp dword ptr [rax+0x10C], 10
jne harakiri_no
cmp dword ptr [rax+0x110], 29595
jne harakiri_no
cmp qword ptr [rax+0x114], 0
jne harakiri_no
cmp dword ptr [rax+0x11C], 0x8A25D
jne harakiri_no
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je harakiri_no
mov rcx, qword ptr [rcx+0x148]
test rcx, rcx
je harakiri_no
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je harakiri_no
mov edx, 29595
call {effect_lookup}
test rax, rax
je harakiri_no
cmp dword ptr [rax], 29595
jne harakiri_no
cmp dword ptr [rax+4], 15
jne harakiri_no
cmp qword ptr [rax+8], 0
jne harakiri_no
cmp dword ptr [rax+0x10], 100
jne harakiri_no
cmp qword ptr [rax+0x14], 0
jne harakiri_no
cmp dword ptr [rax+0x1C], 100
jne harakiri_no
cmp qword ptr [rax+0x20], 0
jne harakiri_no
cmp dword ptr [rax+0x28], 0
jne harakiri_no
mov r11, {player_slot}
cmp qword ptr [r11], rsi
jne harakiri_no
cmp qword ptr [rdi+0x50], rsi
jne harakiri_no
cmp dword ptr [rdi+0x548], 34209
jne harakiri_no
cmp dword ptr [rdi+0x54C], 10
jne harakiri_no
cmp dword ptr [rdi+0x554], 0x100
jne harakiri_no
mov eax, 1
jmp harakiri_return
harakiri_no:
xor eax, eax
harakiri_return:
add rsp, 0x28
pop rsi
pop rbx
ret
'''


def apply_harakiri(previous):
    if previous.get('harakiri_revision') or len(previous['hooks']) != 82:
        raise ValueError('Expected unmodified 82-hook baseline')
    plan = deepcopy(previous)
    gate = next(h for h in plan['hooks'] if h['name'] == 'HE_Consumables')
    carrier = next(h for h in plan['hooks'] if h['name'] == CARRIER_NAME)
    anchor = 'mov rax, {data}\nsub rax, 0x92c0\ncall rax\n'
    if gate['asm'].count(anchor) != 1 or (carrier['code_offset'], carrier['code_capacity']) != (0x1E000, 0x1000):
        raise ValueError('Known gate/carrier layout required')
    # Reuse a dormant part of an owned RX slot. Original element entry remains
    # byte-identical; only this gate calls the helper at its fixed offset.
    from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
    values = {key: 0x140000000+rva for key,rva in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'], **{'return':0x140000000+carrier['rva']+carrier['length']})
    code,_ = Ks(KS_ARCH_X86,KS_MODE_64).asm(carrier['asm'].format(**values),addr=0x14401E000)
    if len(code)>0x400:raise ValueError('Carrier helper gap occupied')
    carrier['asm'] += '\nnop\n'*(0x400-len(code))+HELPER
    gate['asm'] = gate['asm'].replace(anchor,'mov rax, {data}\nadd rax, '+hex(HELPER_OFFSET-plan['data_offset'])+'\ncall rax\n')
    gate['purpose'] += '; exact confirmed Harakiri Sword uses native effect15 and death/respawn path'
    plan.update(harakiri_revision=1, harakiri_gameplay_confirmation_pending=True)
    return plan
