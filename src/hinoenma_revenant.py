"""Complete the observed blood-tomb request through the native interaction flag.

The native William animation event sets info+0x0A at RVA 0x709384.
Interaction::IsInteraction (0x9444B0) reads exactly that byte through
object+0x98 -> interaction container+0x20+index*0x120. The observed blood
tomb is object type 5, ID 0x190, dispatch 22, with zero ladder bones.

Replay the completed native queued-reference assignment, then reproduce
that event only for the captured current Boss player. The game's original
tomb controller owns spawning, eligibility and rewards. No external game
function is called and no character, gear, inventory or save flag is edited.
"""

PLAYER_REVENANT_INTERACTION = {
    'name': 'HE_Revenant', 'rva': 0x751296, 'length': 9,
    'purpose': 'Complete the captured player blood-tomb request after native hold completion, preserving the native queued reference and summon ownership',
    'asm': """
mov rax, qword ptr [rsp+0x50]
mov qword ptr [rbx+0x18], rax
pushfq
push r10
push r11
mov r11, {data}
cmp byte ptr [r11+0x2A], 2
jne revenant_done
cmp dword ptr [r11+0x04], 0
je revenant_done
lea r10, [rdi+0x510]
cmp rbx, r10
jne revenant_done
mov r10, qword ptr [rdi+0x50]
test r10, r10
je revenant_done
cmp r10, qword ptr [r11+0x10]
jne revenant_done
push rax
mov rax, {player_slot}
cmp r10, qword ptr [rax]
pop rax
jne revenant_done
cmp word ptr [r10+0x06], 1
jne revenant_done
cmp dword ptr [r10], 0x58E5E
je revenant_role
cmp dword ptr [r10], 0x51BE1
jne revenant_done
revenant_role:
cmp dword ptr [r10+0xEF0], 0
jne revenant_done
mov r10, qword ptr [r10+0xE90]
test r10, r10
je revenant_done
test byte ptr [r10+0x04], 3
jne revenant_done
cmp dword ptr [r10+0x0C], 1
jne revenant_done
mov r10, qword ptr [rbx]
test r10, r10
je revenant_done
cmp word ptr [r10+0x04], 5
jne revenant_done
cmp dword ptr [r10], 0x190
jne revenant_done
test rax, rax
je revenant_done
cmp qword ptr [rax], r10
jne revenant_done
cmp word ptr [rax+0x08], 0x0101
jne revenant_done
cmp byte ptr [rax+0x0A], 0
jne revenant_done
cmp dword ptr [rax+0x48], 22
jne revenant_done
cmp qword ptr [rax+0x4C], 0
jne revenant_done
inc dword ptr [r11+0xC8]
push r10
movzx r10d, word ptr [rdi+0x4E8]
mov dword ptr [r11+0xCC], r10d
pop r10
cmp byte ptr [rdi+0x4E9], 1
jne revenant_done
mov byte ptr [rax+0x0A], 1
inc dword ptr [r11+0xB8]
mov qword ptr [r11+0xC0], r10
movzx r10d, word ptr [r10+0x06]
mov dword ptr [r11+0xBC], r10d
revenant_done:
pop r11
pop r10
popfq
jmp {return}
""",
}
