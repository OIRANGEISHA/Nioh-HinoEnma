"""Move only the playable Hino-Enma roar input criterion to digit 5.

Native 721010(controller, transition) tests two input conditions. Callers
keep the source/action/state checks; transition WORD+14 is the destination
action (711B0F lookup). Ground roar is 58 then automatic 59. Its 16
playable transitions have first input 6 or 0B, pressed mode1, no second
input, and zero input parameters. Air roar is 23->87->23; its player input
transition has first input 6 and the same remaining criteria. The common
151->87 automatic transition has no input and stays native. Only the two
observed player input signatures use native digit5
pressed BOOL (E631A0: keyboard+101+scan). Alt flight (target101/63/65),
automatic 58->59, other roles and all nonmatching criteria keep native code.
No forced action requests or shared resource/binding edits are made.
"""
from hinoenma_manual_purification import menu_guard
from hinoenma_tutorial import player_guard

ROAR_ACTION = 58
AIR_ROAR_ACTION = 87
ROAR_KEY_SCAN = 0x06


def restore():
    return '''pop rbx
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''


def roar_key_hook():
    menu = menu_guard().replace('manual_purify', 'roar_menu').replace(
        'roar_menu_block_input', 'roar_key_false')
    return dict(name='HE_RoarDigitFive', rva=0x721010, length=5,
        code_offset=0xB800, code_capacity=0xC00,
        purpose='Use native digit5 pressed input only for the captured Hino-Enma player ground target58 and air target87 observed criteria; preserve Alt flight, automatic transitions, other input/state eligibility and shared assets',
        asm='''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
push rbx
mov r11, {data}
''' + player_guard('roar_key').replace('roar_key_done', 'roar_key_original') + '''test rcx, rcx
je roar_key_original
cmp qword ptr [rcx+0x50], r10
jne roar_key_original
test rdx, rdx
je roar_key_original
cmp word ptr [rdx+0x14], 58
je roar_key_ground_input
cmp word ptr [rdx+0x14], 87
jne roar_key_original
cmp byte ptr [rdx+0x0B], 6
jne roar_key_original
jmp roar_key_first_input
roar_key_ground_input:
cmp byte ptr [rdx+0x0B], 6
je roar_key_first_input
cmp byte ptr [rdx+0x0B], 0x0B
jne roar_key_original
roar_key_first_input:
cmp byte ptr [rdx+0x0C], 1
jne roar_key_original
cmp word ptr [rdx+0x0D], 0xFFFF
jne roar_key_original
cmp word ptr [rdx+0x10], 0
jne roar_key_original
cmp word ptr [rdx+0x12], 0
jne roar_key_original
inc dword ptr [r11+0xE10]
mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je roar_key_false
cmp byte ptr [rax+0x4A], 1
jne roar_key_false
''' + menu + '''mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je roar_key_false
mov r9, qword ptr [rax+0x08]
test r9, r9
je roar_key_false
cmp byte ptr [r9], 1
jne roar_key_false
cmp byte ptr [r9+0x107], 0
je roar_key_false
inc dword ptr [r11+0xE14]
''' + restore() + '''mov eax, 1
ret
roar_key_false:
''' + restore() + '''mov eax, 0
ret
roar_key_original:
''' + restore() + '''mov qword ptr [rsp+0x08], rbx
jmp {return}
''')
