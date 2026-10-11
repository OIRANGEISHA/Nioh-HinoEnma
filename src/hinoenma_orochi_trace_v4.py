"""Revision3 behavior with private diagnostics for its premature native exit.

The two added probes preserve native execution and write only their own
allocation. They record the selected outgoing transition and whether the
owned1200 schedule enqueues type40/type41. They do not force an event.
"""
from copy import deepcopy
from hinoenma_orochi_trial import SAVE,RESTORE,player_guard,resources_guard
from hinoenma_orochi_candidate_v2 import BIND_SIZE,finisher_guard
from hinoenma_orochi_candidate_v3 import candidate_plan as third_plan


def transition_trace():
    return dict(name='HE_OrochiOutgoingTransitionTrace',rva=0x73F9FB,length=5,
        original='488bc3ebba',code_offset=0x4000,code_capacity=0x800,
        asm=SAVE+player_guard('ot')+'''cmp dword ptr [r11+0x74], 1
jne ot_original
cmp rdi, r8
jne ot_original
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne ot_original
'''+resources_guard('ot')+'''inc dword ptr [r11+0x140]
movsx eax, word ptr [rbx+0x14]
mov dword ptr [r11+0x144], eax
movd dword ptr [r11+0x148], xmm6
mov qword ptr [r11+0x150], rbx
mov eax, dword ptr [r8+0x24]
mov dword ptr [r11+0x158], eax
mov r9, qword ptr [r11+0x1A0]
mov rax, qword ptr [r11+0xB0]
cmp qword ptr [rax+0x40], r9
jne ot_motion
cmp qword ptr [r9+8], r10
jne ot_motion
mov eax, dword ptr [r9+0x40]
mov dword ptr [r11+0x160], eax
mov eax, dword ptr [r9+0x44]
mov dword ptr [r11+0x164], eax
mov rax, qword ptr [r9+0x20]
mov qword ptr [r11+0x168], rax
ot_motion:
mov r9, qword ptr [r10+0x38]
mov eax, dword ptr [r9+0x60]
mov dword ptr [r11+0x170], eax
mov eax, dword ptr [r9+0xF0]
mov dword ptr [r11+0x174], eax
mov eax, dword ptr [r9+0xF4]
mov dword ptr [r11+0x178], eax
mov rax, qword ptr [r8+0x5D8]
mov qword ptr [r11+0x180], rax
ot_original:
'''+RESTORE+'''mov rax, rbx
jmp {orochi_transition_epilogue}
''',purpose='Record the real native outgoing finisher transition, frame and motion/event timing without changing the selected transition')


def event_trace():
    return dict(name='HE_OrochiScheduledEventTrace',rva=0x968730,length=6,
        original='41564883ec30',code_offset=0x4800,code_capacity=0x800,
        asm=SAVE+player_guard('et')+finisher_guard('et')+'''mov r9, qword ptr [r11+0x1A0]
mov rax, qword ptr [r11+0xB0]
cmp qword ptr [rax+0x40], r9
jne et_original
cmp qword ptr [r9+8], r10
jne et_original
lea rax, [r9+0xA0]
cmp qword ptr [rsp+0xC0], rax
jne et_original
mov rax, qword ptr [r11+0xF8]
cmp qword ptr [r9+0x20], rax
jne et_original
mov rdx, qword ptr [rsp+0xB8]
test rdx, rdx
je et_original
mov rdx, qword ptr [rdx]
lea rax, [rax+0x24]
cmp rdx, rax
jb et_original
add rax, 18*12
cmp rdx, rax
ja et_original
cmp dword ptr [rdx+4], 40
je et_type40
cmp dword ptr [rdx+4], 41
jne et_original
inc dword ptr [r11+0x18C]
jmp et_frame
et_type40:
inc dword ptr [r11+0x188]
et_frame:
mov eax, dword ptr [rdx]
mov dword ptr [r11+0x190], eax
et_original:
'''+RESTORE+'''push r14
sub rsp, 0x30
jmp {return}
''',purpose='Count native1200 type40/type41 enqueue operations for the owned current finisher event state; preserve original event and scheduling')


def candidate_plan(production,module_base,production_allocation,menu_guard):
    plan=third_plan(production,module_base,production_allocation,menu_guard)
    plan.update(tool_version='orochi-scene-diagnostic.4',allocation_size=0x6000,
                data_offset=0x5000,diagnostic_only_additions=True)
    plan['targets']['orochi_transition_epilogue']=0x73F9BA
    plan['hooks'].extend((transition_trace(),event_trace()))
    return deepcopy(plan)
