"""Restore the native item-use teaching count for completed fallback uses.

Native animation event 0x70A561 applies effects, commits inventory and increments
mission+0x27C. The fallback at 0x7518C9/0x751941 commits those same effects and
inventory but omits that count. Notify only after the fallback commit, with the
native animation-completed flag and current player checked to avoid duplicates.

A zero-default one-shot receipt can acknowledge an already verified completed
use during a live upgrade. The teaching getter consumes it atomically and
checks the captured player, spawn generation, manager and expected count. A
fresh launcher never queues a receipt. No mission-completion flags are changed.
"""

TUTORIAL_TARGETS = {'tutorial_manager': 0x18715E0}


def player_guard(prefix):
    return '''mov r10, qword ptr [r11+0x10]
test r10, r10
je PREFIX_done
cmp dword ptr [r11+0x04], 0
je PREFIX_done
mov rax, {player_slot}
cmp r10, qword ptr [rax]
jne PREFIX_done
cmp word ptr [r10+0x06], 1
jne PREFIX_done
cmp dword ptr [r10], 0x58E5E
je PREFIX_role
cmp dword ptr [r10], 0x51BE1
jne PREFIX_done
PREFIX_role:
cmp dword ptr [r10+0xEF0], 0
jne PREFIX_done
mov rax, qword ptr [r10+0xE90]
test rax, rax
je PREFIX_done
cmp dword ptr [rax+0x0C], 1
jne PREFIX_done
'''.replace('PREFIX', prefix)


CONSUMABLE_NOTICE = {
    'name': 'HE_ConsumableNotice', 'rva': 0x751946, 'length': 11,
    'purpose': 'Notify the native teaching count after completed Hino-Enma fallback item effects and inventory commit, without repeating an animation event',
    'asm': '''pushfq
push rax
push r10
push r11
mov r11, {data}
''' + player_guard('item_notice') + '''cmp r10, qword ptr [rdi+0x50]
jne item_notice_done
test r14b, r14b
jne item_notice_done
cmp byte ptr [rdi+0x556], 0
jne item_notice_done
cmp byte ptr [rdi+0x555], 1
jne item_notice_done
cmp byte ptr [rdi+0x554], 0
jne item_notice_done
cmp dword ptr [rdi+0x550], 1
jne item_notice_done
mov eax, dword ptr [rdi+0x54C]
sub eax, 1
cmp eax, 2
ja item_notice_done
mov eax, dword ptr [rdi+0x548]
test eax, eax
js item_notice_done
cmp eax, dword ptr [r11+0x54]
jne item_notice_done
mov r10, {tutorial_manager}
mov r10, qword ptr [r10]
test r10, r10
je item_notice_done
inc dword ptr [r10+0x27C]
inc dword ptr [r11+0xF04]
mov dword ptr [r11+0xF08], eax
item_notice_done:
pop r11
pop r10
pop rax
popfq
mov qword ptr [rdi+0x548], -1
jmp {return}
''',
}


TUTORIAL_RECEIPT = {
    'name': 'HE_TutorialReceipt', 'rva': 0x8AA312, 'length': 6,
    'purpose': 'Consume a private one-shot receipt for a verified completed item use in the same player spawn, before the native teaching getter reads its count; fresh startup queues no receipt',
    'asm': '''pushfq
push rax
push rcx
push r10
push r11
mov r11, {data}
xor ecx, ecx
xchg dword ptr [r11+0xF10], ecx
cmp ecx, 1
jne tutorial_receipt_done
''' + player_guard('tutorial_receipt') + '''cmp r10, qword ptr [r11+0xF20]
jne tutorial_receipt_done
mov eax, dword ptr [r11+0x1C]
cmp eax, dword ptr [r11+0xF2C]
jne tutorial_receipt_done
mov eax, dword ptr [r11+0xF28]
cmp eax, dword ptr [r11+0x54]
jne tutorial_receipt_done
mov r10, {tutorial_manager}
mov r10, qword ptr [r10]
test r10, r10
je tutorial_receipt_done
cmp r10, qword ptr [r11+0xF18]
jne tutorial_receipt_done
mov eax, dword ptr [r10+0x27C]
cmp eax, dword ptr [r11+0xF14]
jne tutorial_receipt_done
inc dword ptr [r10+0x27C]
inc dword ptr [r11+0xF0C]
mov eax, dword ptr [r11+0xF28]
mov dword ptr [r11+0xF08], eax
tutorial_receipt_done:
pop r11
pop r10
pop rcx
pop rax
popfq
mov ecx, dword ptr [rax+0x27C]
jmp {return}
''',
}

TUTORIAL_CLEAR_RECEIPT = {
    'name': 'HE_TutorialClearReceipt', 'rva': 0x8A9F3F, 'length': 7,
    'purpose': 'Invalidate a queued live-upgrade receipt whenever the native teaching script clears its action counts, preserving the original clear operation',
    'asm': '''pushfq
push r11
mov r11, {data}
mov dword ptr [r11+0xF10], 0
pop r11
popfq
mov qword ptr [rax+0x250], rcx
jmp {return}
''',
}

TUTORIAL_HOOKS = [CONSUMABLE_NOTICE, TUTORIAL_RECEIPT, TUTORIAL_CLEAR_RECEIPT]
