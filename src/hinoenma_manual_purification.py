"""Fresh F6 invokes native purification in normal play, without lesson scope.

The invocation marker is set only around synchronous native helper calls.
Root callbacks still verify the current player, spawn, controller and resource.
Menu fields mirror the registered UI::IsMenuOpen callback at RVA 8AB120.
"""
import copy

from hinoenma_attributes import VOLATILE_SAVE, VOLATILE_RESTORE
from hinoenma_purification import PURIFICATION_HOOKS, PURIFICATION_TICK, hint_scope
from hinoenma_tutorial import player_guard

MANUAL_KEY_SCAN = 0x40  # Native DirectInput keyboard scan code for F6.
MENU_FIELDS = ((0x48,0x60),(0xA0,0x60),(0xA8,0x60),(0xC0,0x60),
    (0xB0,0x60),(0xB8,0x60),(0x260,0x60),(0x2E0,0x60),(0x2E8,0x60),
    (0x358,0x60),(0x360,0x60),(0x990,0x60),(0x308,0x60),(0x120,0x150),
    (0x160,0x60),(0x498,0x60),(0x4A8,0x60))
SUBMENU_FIELDS = ((0x158,0x68),(0x1B8,0x68),(0x1C0,0x68),(0x1C8,0x68),
    (0x1D0,0x60),(0x1D8,0x60),(0x1E8,0x70),(0x1F8,0x68),(0x200,0x68),
    (0x208,0x60),(0x218,0x60),(0x988,0x60))


def menu_guard():
    lines=['mov r8, {tutorial_ui_owner}', 'mov r8, qword ptr [r8]',
           'test r8, r8', 'je manual_purify_block_input']
    for owner, state in MENU_FIELDS:
        lines += [f'mov rax, qword ptr [r8+0x{owner:X}]', 'test rax, rax',
                  'je manual_purify_block_input', f'cmp dword ptr [rax+0x{state:X}], 0',
                  'jne manual_purify_block_input']
    # ACD9C0 treats state 5 as closed, unlike the other menu widgets.
    lines += ['mov rax, qword ptr [r8+0x318]', 'test rax, rax',
              'je manual_purify_block_input', 'mov eax, dword ptr [rax+0x60]',
              'test eax, eax', 'je manual_purify_aux_closed', 'cmp eax, 5',
              'jne manual_purify_block_input', 'manual_purify_aux_closed:']
    for owner, state in SUBMENU_FIELDS:
        lines += [f'mov rax, qword ptr [r8+0x{owner:X}]', 'test rax, rax',
                  'je manual_purify_block_input', f'cmp dword ptr [rax+0x{state:X}], 0',
                  'jne manual_purify_block_input']
    return '\n'.join(lines)+'\n'


def manual_epoch_scope(prefix):
    return f'''cmp dword ptr [r11+0xE60], 1
jne {prefix}_lesson_epoch
cmp r10, qword ptr [r11+0xE68]
jne {prefix}_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE70]
jne {prefix}_done
mov rax, qword ptr [r10+0x230]
test rax, rax
je {prefix}_done
mov rax, qword ptr [rax+8]
test rax, rax
je {prefix}_done
cmp rax, qword ptr [r11+0xE78]
jne {prefix}_done
cmp r10, qword ptr [rax+0x50]
jne {prefix}_done
jmp {prefix}_epoch_ready
{prefix}_lesson_epoch:
'''


def authorize_manual_root(spec):
    result=copy.deepcopy(spec)
    prefix='purify_origin' if spec['name']=='HE_PurificationOrigin' else 'purify_collision'
    asm=result['asm']
    old=f'cmp dword ptr [r11+0xFB8], 1\njne {prefix}_done\n'
    assert asm.count(old)==1
    asm=asm.replace(old,f'cmp dword ptr [r11+0xE60], 1\nje {prefix}_active\n'+old+f'{prefix}_active:\n',1)
    start='cmp r10, qword ptr [r11+0xF98]\n'
    # The later hidden-hint branch repeats this epoch check; extend only
    # the main owner guard, keeping the original lesson branch intact.
    assert asm.count(start)==2
    asm=asm.replace(start,manual_epoch_scope(prefix)+start,1)
    end=(f'cmp eax, dword ptr [r11+0xFA0]\njne {prefix}_done\n'
         if prefix=='purify_origin' else
         f'cmp rax, qword ptr [r11+0xF90]\njne {prefix}_done\n')
    assert asm.count(end)==1
    asm=asm.replace(end,end+f'{prefix}_epoch_ready:\n',1)
    old_hint=f'mov rdx, qword ptr [r11+0xFB0]\ntest rdx, rdx\nje {prefix}_done\n'+hint_scope(prefix,'rdx')
    assert asm.count(old_hint)==1
    asm=asm.replace(old_hint,f'cmp dword ptr [r11+0xE60], 1\nje {prefix}_hint_ready\n'+old_hint+f'{prefix}_hint_ready:\n',1)
    result['asm']=asm
    if prefix=='purify_collision':
        # Keep the established target at 9000 and enlarge only its reserved
        # tail; the newly appended manual handler starts after this slot.
        result['code_capacity']=0x800
    result['purpose']+='; also accept a synchronous F6 invocation with matching current player, spawn and controller'
    return result


RESOURCE_GUARDS=PURIFICATION_TICK['asm'].split('mov rax, qword ptr [r10+0x230]\n',1)[1].split('sub rsp, 0x80\n',1)[0]
RESOURCE_GUARDS=('mov rax, qword ptr [r10+0x230]\n'+RESOURCE_GUARDS).replace('purify_tick','manual_purify')

MANUAL_PURIFICATION = {
    'name':'HE_ManualPurification', 'rva':0x715D43, 'length':8,
    'code_capacity':0x800,
    'purpose':'Fresh F6 in normal gameplay creates the native purification VFX and sphere; only the current Hino-Enma player, outside native menus, with ready input and verified resources',
    'asm': VOLATILE_SAVE.replace('{frame}','0x80')+'''mov r11, {data}
mov r10, qword ptr [r11+0x10]
cmp r10, qword ptr [rsi+0x50]
jne manual_purify_done
'''+player_guard('manual_purify').replace('manual_purify_done','manual_purify_block_input')+'''cmp dword ptr [r11+0xE60], 0
jne manual_purify_done
cmp qword ptr [rsi+0x58], 0
je manual_purify_block_input
inc dword ptr [r11+0xE80]
cmp r10, qword ptr [r11+0xE68]
jne manual_purify_new_epoch
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xE70]
jne manual_purify_new_epoch
cmp rsi, qword ptr [r11+0xE78]
je manual_purify_epoch_ready
manual_purify_new_epoch:
mov qword ptr [r11+0xE68], r10
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0xE70], eax
mov qword ptr [r11+0xE78], rsi
mov dword ptr [r11+0xE64], 1
manual_purify_epoch_ready:
mov rax, {native_window_owner}
mov rax, qword ptr [rax]
test rax, rax
je manual_purify_block_input
cmp byte ptr [rax+0x4A], 1
jne manual_purify_block_input
mov rax, {native_input_manager}
mov rax, qword ptr [rax]
test rax, rax
je manual_purify_block_input
mov r9, qword ptr [rax+8]
test r9, r9
je manual_purify_block_input
cmp byte ptr [r9], 1
jne manual_purify_block_input
'''+menu_guard()+'''test byte ptr [r9+0x41], 0x80
je manual_purify_key_released
cmp dword ptr [r11+0xE64], 0
jne manual_purify_done
mov dword ptr [r11+0xE64], 1
mov rcx, rsi
'''+RESOURCE_GUARDS+'''inc dword ptr [r11+0xE84]
mov dword ptr [r11+0xE60], 1
mov rcx, rsi
mov edx, 1
call {native_purification_wave}
mov r11, {data}
mov eax, dword ptr [rsp]
mov dword ptr [r11+0xE8C], eax
mov rcx, rsi
call {native_purification_visual}
mov r11, {data}
mov dword ptr [r11+0xE60], 0
inc dword ptr [r11+0xE88]
jmp manual_purify_done
manual_purify_key_released:
mov dword ptr [r11+0xE64], 0
jmp manual_purify_done
manual_purify_block_input:
mov dword ptr [r11+0xE64], 1
manual_purify_done:
'''+VOLATILE_RESTORE.replace('{frame}','0x80')+'''mov rbx, qword ptr [r11+0x28]
mov rbp, qword ptr [r11+0x30]
jmp {return}
''',
}


def manual_purification_hooks():
    return [authorize_manual_root(spec) if spec['name'] in
        ('HE_PurificationOrigin','HE_PurificationCollisionOrigin') else copy.deepcopy(spec)
        for spec in PURIFICATION_HOOKS]+[copy.deepcopy(MANUAL_PURIFICATION)]
