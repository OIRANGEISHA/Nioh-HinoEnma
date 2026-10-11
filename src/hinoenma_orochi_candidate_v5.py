"""Scene-bound native chain3008 ->3491/1200 ->4000/1201.

The recorded208 transition is the next native execution stage. Supply its
owned action, motion and event resources as register views, then resolve the
native terminal3000 to Hino idle. No input, damage or mission event is forced.
"""
from copy import deepcopy

from hinoenma_orochi_trial import SAVE, RESTORE, player_guard, resources_guard
from hinoenma_orochi_candidate_v2 import BIND_SIZE, finisher_guard, event_resources_guard
from hinoenma_orochi_trace_v4 import candidate_plan as fourth_plan


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Audited parent assembly fragment changed')
    return source.replace(before, after, 1)


def paired_resource_guard(prefix):
    return f'''mov rax, qword ptr [r11+0x1A8]
cmp dword ptr [rax], 4000
jne {prefix}_original
cmp byte ptr [rax+0x40], 1
jne {prefix}_original
mov r9, qword ptr [r11+0x38]
cmp qword ptr [rax+0x38], r9
jne {prefix}_original
mov rax, qword ptr [rax+0x20]
test rax, rax
je {prefix}_original
cmp dword ptr [rax+0x20], 1201
jne {prefix}_original
'''


def stage_guard(prefix, request):
    # The resource key must match the exact owned current/previous action.
    # Preserve the previous-record allowance needed during native blending.
    return f'''cmp dword ptr [r11+0x74], 1
jne {prefix}_original
mov eax, {request}
cmp eax, 1200
je {prefix}_stage1200
cmp eax, 1201
jne {prefix}_original
mov rax, qword ptr [r11+0x1A8]
jmp {prefix}_stage_record
{prefix}_stage1200:
mov rax, qword ptr [r11+0x68]
{prefix}_stage_record:
cmp qword ptr [r8+0x58], rax
je {prefix}_record_ready
cmp qword ptr [r8+0x60], rax
jne {prefix}_original
{prefix}_record_ready:
'''


def diagnostic_stage_guard(prefix):
    return f'''cmp dword ptr [r11+0x74], 1
jne {prefix}_original
mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x68]
je {prefix}_record_ready
cmp rax, qword ptr [r11+0x1A8]
jne {prefix}_original
{prefix}_record_ready:
'''


def event_trace():
    return dict(name='HE_OrochiScheduledEventTrace',rva=0x968730,length=6,
        original='41564883ec30',code_offset=0x4800,code_capacity=0x800,
        asm=SAVE+player_guard('et')+diagnostic_stage_guard('et')+'''mov r9, qword ptr [r11+0x1A0]
mov rax, qword ptr [r11+0xB0]
cmp qword ptr [rax+0x40], r9
jne et_original
cmp qword ptr [r9+8], r10
jne et_original
lea rax, [r9+0xA0]
cmp qword ptr [rsp+0xC0], rax
je et_queue_owned
lea rax, [r9+0x90]
cmp qword ptr [rsp+0xC0], rax
jne et_original
et_queue_owned:
mov rax, qword ptr [r9+0x20]
cmp rax, qword ptr [r11+0xF8]
je et_schedule1200
cmp rax, qword ptr [r11+0x1B0]
jne et_original
mov edx, dword ptr [r11+0x1C0]
jmp et_schedule_selected
et_schedule1200:
mov edx, dword ptr [r11+0x1C4]
et_schedule_selected:
test edx, edx
je et_original
cmp edx, 1024
ja et_original
mov ecx, dword ptr [rax+8]
add rax, rcx
mov rcx, qword ptr [rsp+0xB8]
test rcx, rcx
je et_original
mov rcx, qword ptr [rcx]
cmp rcx, rax
jb et_original
sub rcx, rax
imul edx, edx, 12
cmp rcx, rdx
jae et_original
add rcx, rax
cmp dword ptr [rcx+4], 40
je et_type40
cmp dword ptr [rcx+4], 41
jne et_original
inc dword ptr [r11+0x18C]
jmp et_frame
et_type40:
inc dword ptr [r11+0x188]
et_frame:
mov eax, dword ptr [rcx]
mov dword ptr [r11+0x190], eax
et_original:
'''+RESTORE+'''push r14
sub rsp, 0x30
jmp {return}
''',purpose='Record actual native1200/1201 type40/41 enqueue operations from the owned primary event state without changing scheduling')


def candidate_plan(production,module_base,production_allocation,menu_guard):
    plan=fourth_plan(production,module_base,production_allocation,menu_guard)
    plan.update(tool_version='orochi-scene-candidate.5',diagnostic_only_additions=False,
                native_chain=[3008,3491,4000],native_motion_ids=[1200,1201],
                uninstalled=True,gameplay_validated=False)
    hooks=plan['hooks']
    for hook,prefix in zip(hooks[:8],('oh','ob','om','op','oe','bp','br','ot')):
        marker=resources_guard(prefix)
        # The event hook has two separately guarded branches.
        if marker not in hook['asm']:
            raise ValueError('Parent resource guard missing')
        hook['asm']=hook['asm'].replace(marker,marker+paired_resource_guard(prefix))

    bank=hooks[1]
    bank['asm']=replace_once(bank['asm'],'''cmp dword ptr [rsp+0xA0], 3491
jne ob_original
ob_borrow:
''','''cmp dword ptr [rsp+0xA0], 4000
je ob_paired
cmp dword ptr [rsp+0xA0], 3491
jne ob_original
jmp ob_borrow
ob_paired:
mov rax, qword ptr [r11+0x1A8]
cmp qword ptr [r8+0x58], rax
je ob_borrow
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne ob_original
test dword ptr [r8+0x40], 0x400000
je ob_original
mov r9, qword ptr [r11+0x18]
cmp qword ptr [r8+0x5B0], r9
jne ob_original
mov rax, qword ptr [r11+0x20]
cmp qword ptr [r9], rax
jne ob_original
mov rax, qword ptr [r9+0xE90]
test rax, rax
je ob_original
cmp dword ptr [rax+0xC], 1
jne ob_original
ob_borrow:
''')
    bank['asm']=replace_once(bank['asm'],'''ob_finish_idle:
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne ob_original
''','''ob_finish_idle:
mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x68]
je ob_idle_owned
cmp rax, qword ptr [r11+0x1A8]
jne ob_original
ob_idle_owned:
''')

    motion=hooks[2]
    motion['asm']=replace_once(motion['asm'],'''cmp dword ptr [rsp+0xB8], 1200
jne om_original
mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
je om_record_ready
cmp qword ptr [r8+0x60], rax
jne om_original
om_record_ready:
''',stage_guard('om','dword ptr [rsp+0xB8]'))
    for index,prefix,request in ((3,'op','dword ptr [rsp+0xB8]'),
                                 (4,'oe','dword ptr [rsp+0xB8]'),
                                 (5,'bp','esi'),(6,'br','esi')):
        hook=hooks[index]
        hook['asm']=replace_once(hook['asm'],finisher_guard(prefix),stage_guard(prefix,request))
        key_test=(f'cmp esi, 1200\njne {prefix}_original\n' if index>=5 else
                  f'cmp dword ptr [rsp+0xB8], 1200\njne {prefix}_original\n')
        hook['asm']=replace_once(hook['asm'],key_test,'')
    outgoing=hooks[7]
    outgoing['asm']=replace_once(outgoing['asm'],'''mov rax, qword ptr [r11+0x68]
cmp qword ptr [r8+0x58], rax
jne ot_original
''','''mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x68]
je ot_record_ready
cmp rax, qword ptr [r11+0x1A8]
jne ot_original
ot_record_ready:
''')
    outgoing['asm']=replace_once(outgoing['asm'],'inc dword ptr [r11+0x140]\n',
        '''inc dword ptr [r11+0x140]
mov rax, qword ptr [r8+0x58]
mov eax, dword ptr [rax]
mov dword ptr [r11+0x1C8], eax
''')
    hooks[8]=event_trace()
    return deepcopy(plan)
