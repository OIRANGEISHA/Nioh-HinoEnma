"""Pure, scoped Abyss Kodama guide-to-shore request46 queue candidate.

Only aura70 changes. Original ten-request checks and fixed helper entries are
preserved; compact46 checks fit unused aura padding. All native events, query
dispatch, tracked references and resource-ticket semantics remain native.
"""
from pathlib import Path
from copy import deepcopy
import json,struct,sys

ROOT=Path(__file__).resolve().parent
import hinoenma_abyss_actions as actions
import hinoenma_abyss_runtime as runtime
from hinoenma_abyss_assembly import assemble
from menu_preview_reload_portable import new_sources

EXTRA_OFFSET=0x2E540
LITERAL_OFFSET=0x33B00
CORE_OFFSET=0xF000
CHANGED_INDICES=(70,)
ROWS=json.loads((ROOT/'hinoenma_abyss_guide_resources.json').read_text('utf-8'))['records']


def gate(rows):
    text=runtime.gate(rows)
    dispatch='cmp dword ptr [r10+0x48], 10\njne abyss_actions_gate_bad\n'
    assert text.count(dispatch)==1
    text=text.replace(dispatch,'''cmp dword ptr [r10+0x48], 10
je boat_dispatch_valid
cmp dword ptr [r10+0x48], 46
jne abyss_actions_gate_bad
boat_dispatch_valid:
''')
    request_marker='cmp qword ptr [r10+0x4C], 0\njne abyss_actions_gate_bad\n'
    assert text.count(request_marker)==1
    text=text.replace(request_marker,request_marker+'''cmp dword ptr [r10+0x48], 46
jne boat_lookup_scope_valid
cmp qword ptr [rsp+0x120], 2
jne boat_lookup_scope_valid
cmp dword ptr [rsp+0xF8], 170
jne abyss_actions_gate_bad
boat_lookup_scope_valid:
''')
    cancel='mov eax, dword ptr [r9]\nsub eax, 73\ncmp eax, 2\nja abyss_actions_gate_bad\n'
    assert text.count(cancel)==1
    text=text.replace(cancel,'''mov eax, dword ptr [r9]
cmp dword ptr [r10+0x48], 46
jne boat_cancel_next_floor
sub eax, 1155
cmp eax, 2
ja abyss_actions_gate_bad
jmp abyss_cancel_request_flags_valid
boat_cancel_next_floor:
sub eax, 73
cmp eax, 2
ja abyss_actions_gate_bad
''')
    marker='mov dword ptr [rsp+0xB4], 1\ncmp qword ptr [rsp+0x120], 1\n'
    assert text.count(marker)==1
    text=text.replace(marker,'''mov r10, qword ptr [rsp+0x90]
cmp dword ptr [r10+0x48], 46
jne boat_extra_resources_checked
mov rcx, qword ptr [rsp+0x80]
mov rdx, qword ptr [rsp+0x98]
mov r8, qword ptr [rsp+0x88]
call {data} + 0x1F540
test eax, eax
je abyss_actions_gate_bad
boat_extra_resources_checked:
'''+marker)
    return text


def literal_blob(existing):
    # Existing literal positions remain unchanged. Shared generic transitions
    # point to their exact existing48-byte descriptors rather than duplicating.
    known={};offset=0x23500
    for raw in existing:
        known.setdefault(raw,offset);offset+=len(raw)
    blob=bytearray(3*16);headers=[]
    for ident in (1155,1156,1157):
        row=ROWS[str(ident)]
        param=LITERAL_OFFSET-CORE_OFFSET+len(blob)
        blob.extend(bytes.fromhex(row['parameter_raw_00_a0']))
        refs=LITERAL_OFFSET-CORE_OFFSET+len(blob)
        positions=[]
        for _ in row['transitions']:
            positions.append(len(blob));blob.extend(b'\0'*4)
        headers.append((ident,row,param,refs,positions))
    for i,(ident,row,param,refs,positions) in enumerate(headers):
        struct.pack_into('<IHHII',blob,i*16,ident,row['transition_first'],row['transition_count'],param,refs)
        for t,position in zip(row['transitions'],positions):
            raw=bytes.fromhex(t['raw'])
            if raw not in known:
                known[raw]=LITERAL_OFFSET-CORE_OFFSET+len(blob);blob.extend(raw)
            struct.pack_into('<I',blob,position,known[raw])
    event=next(e for e in ROWS['1155']['references'] if e['index']==120)
    event_delta=LITERAL_OFFSET-CORE_OFFSET+len(blob)
    blob.extend(bytes.fromhex(event['raw_00_80']))
    if len(blob)>0x34000-LITERAL_OFFSET:
        raise ValueError('New boat literals exceed unused aura tail')
    return bytes(blob),event_delta


def extra_asm(event_delta):
    bad='boat_extra_done'
    pointer=lambda reg:actions.pointer(reg,bad,scratch='r11')
    s=actions.SAVES+'''mov dword ptr [rsp+0xB4], 0
mov qword ptr [rsp+0x80], rcx
mov qword ptr [rsp+0x88], rdx
mov qword ptr [rsp+0x90], r8
mov rdi, r8
'''
    for index,bankoff in enumerate((0x70,0x78)):
        label=f'boat_lower_{index}'
        s+=f'''mov rax, qword ptr [rdi+{bankoff}]
test rax, rax
je {label}_done
'''+pointer('rax')+f'''mov edx, dword ptr [rax+0x130]
test edx, edx
je {label}_done
cmp edx, 0x1000
ja boat_extra_done
mov r9, qword ptr [rax+0x128]
'''+pointer('r9')+f'''xor ecx, ecx
{label}_loop:
mov r10, qword ptr [r9+rcx*8]
test r10, r10
je {label}_next
'''+pointer('r10')+f'''cmp byte ptr [r10+0x40], 0
je {label}_next
mov eax, dword ptr [r10]
cmp eax, 170
je boat_extra_done
sub eax, 1155
cmp eax, 2
jbe boat_extra_done
{label}_next:
inc ecx
cmp ecx, edx
jb {label}_loop
{label}_done:
'''
    s+='''mov rbx, qword ptr [rsp+0x88]
xor esi, esi
boat_rows_loop:
mov rax, {data}
add rax, 0x24B00
mov ecx, esi
shl rcx, 4
add rax, rcx
mov qword ptr [rsp+0x98], rax
mov rdi, qword ptr [rbx+0x128]
xor edx, edx
xor r8d, r8d
boat_record_loop:
mov r10, qword ptr [rdi+rdx*8]
test r10, r10
je boat_record_next
'''+pointer('r10')+'''mov r9, qword ptr [rsp+0x98]
mov eax, dword ptr [r9]
cmp dword ptr [r10], eax
jne boat_record_next
inc r8d
cmp r8d, 1
jne boat_extra_done
cmp byte ptr [r10+0x40], 1
jne boat_extra_done
cmp qword ptr [r10+0x38], rbx
jne boat_extra_done
mov qword ptr [rsp+0xA0], r10
mov r10, qword ptr [r10+0x20]
'''+pointer('r10')+'''mov eax, dword ptr [r9+8]
mov r11, {data}
add rax, r11
mov ecx, 20
call {data} + 0x20380
jnc boat_extra_done
mov r10, qword ptr [rsp+0xA0]
mov r9, qword ptr [rbx+0x50]
cmp qword ptr [r10+0x78], r9
jne boat_extra_done
mov rax, qword ptr [rsp+0x98]
movzx ecx, word ptr [rax+4]
cmp word ptr [r10+0x80], cx
jne boat_extra_done
movzx eax, word ptr [rax+6]
cmp word ptr [r10+0x82], ax
jne boat_extra_done
add eax, ecx
cmp word ptr [rbx+0x5A], ax
jb boat_extra_done
mov dword ptr [rsp+0xBC], edx
mov rax, qword ptr [rsp+0x98]
mov eax, dword ptr [rax+12]
mov r11, {data}
add rax, r11
mov qword ptr [rsp+0xA8], rax
xor edx, edx
boat_transition_loop:
mov rax, qword ptr [rsp+0x98]
movzx eax, word ptr [rax+4]
add eax, edx
mov r9, qword ptr [rbx+0x50]
mov r10, qword ptr [r9+rax*8]
'''+pointer('r10')+'''mov r9, qword ptr [rsp+0xA8]
mov eax, dword ptr [r9+rdx*4]
mov r11, {data}
add rax, r11
mov ecx, 6
call {data} + 0x20380
jnc boat_extra_done
inc edx
mov rax, qword ptr [rsp+0x98]
movzx ecx, word ptr [rax+6]
cmp edx, ecx
jb boat_transition_loop
mov edx, dword ptr [rsp+0xBC]
boat_record_next:
inc edx
cmp edx, dword ptr [rbx+0x130]
jb boat_record_loop
cmp r8d, 1
jne boat_extra_done
inc esi
cmp esi, 3
jb boat_rows_loop
cmp word ptr [rbx+0x88], 120
jbe boat_extra_done
cmp word ptr [rbx+0x88], 0x1000
ja boat_extra_done
mov r9, qword ptr [rbx+0x80]
'''+pointer('r9')+'''mov r10, qword ptr [r9+960]
'''+pointer('r10')+f'''mov rax, {{data}}
add rax, 0x{event_delta:X}
mov ecx, 16
call {{data}} + 0x20380
jnc boat_extra_done
mov rax, qword ptr [rsp+0x80]
mov r10, qword ptr [rax+0x38]
'''+pointer('r10')+'''cmp dword ptr [r10+0x50], 1
ja boat_extra_done
mov qword ptr [rsp+0xA0], r10
'''
    for slot in (2,6):
        for motion in (8,0):
            s+=f'''mov rax, qword ptr [rsp+0xA0]
mov rbx, qword ptr [rax+{8+slot*8}]
'''+pointer('rbx')+'''mov rcx, qword ptr [rbx+0x480]
'''+pointer('rcx')+'''cmp dword ptr [rcx+8], 0
je boat_extra_done
cmp dword ptr [rcx+8], 0x10000
ja boat_extra_done
mov r10, qword ptr [rcx+0x10]
'''+pointer('r10')+f'''mov edx, {motion}
mov r8d, -1
call {{native_ladder_motion_index}}
test eax, eax
js boat_extra_done
mov r10, qword ptr [rbx+0x468]
'''+pointer('r10')+'''mov rcx, qword ptr [rbx+0x470]
cmp rcx, r10
jbe boat_extra_done
sub rcx, r10
cmp rcx, 0x80000
ja boat_extra_done
test cl, 7
jne boat_extra_done
mov edx, eax
shl rdx, 3
cmp rdx, rcx
jae boat_extra_done
mov r9, qword ptr [r10+rdx]
'''+pointer('r9')
    s+='''mov dword ptr [rsp+0xB4], 1
boat_extra_done:
mov eax, dword ptr [rsp+0xB4]
mov qword ptr [rsp+0x108], rax
'''+actions.RESTORES+'ret\n'
    return s


def payload(plan,asm,offset):
    p=deepcopy(plan);h=deepcopy(p['hooks'][70]);h['asm']=asm;h['code_offset']=offset
    p['hooks']=[h]
    return assemble(p,0x140000000,0x144000000)[0]['payload']


def candidate_plan(previous_plan):
    basis=deepcopy(previous_plan)
    basis['tool_version']=runtime.VERSION
    runtime.validate_layout(basis)
    if previous_plan.get('tool_version') not in ('1.0.0-beta.5.5',runtime.VERSION) or len(previous_plan['hooks'])!=82:
        raise ValueError('Frozen Beta5.5 required')
    plan=deepcopy(previous_plan)
    plan['tool_version']=runtime.VERSION
    prefix=new_sources()[2]
    prefix_bytes=payload(plan,prefix,0x2D000)
    previous=assemble(previous_plan,0x140000000,0x144000000)
    if prefix_bytes!=previous[70]['payload'][:len(prefix_bytes)]:
        raise ValueError('Unchanged menu/aura prefix required')
    main=actions.helpers(plan,gate)
    blob,event_delta=literal_blob(list(actions.TABLES))
    extra=extra_asm(event_delta)
    extra_bytes=payload(plan,extra,EXTRA_OFFSET)
    if EXTRA_OFFSET+len(extra_bytes)>actions.HELPER_OFFSET:
        raise ValueError('Boat code overlaps fixed existing helpers')
    main_bytes=payload(plan,main,actions.HELPER_OFFSET)
    if actions.HELPER_OFFSET+len(main_bytes)>LITERAL_OFFSET:
        raise ValueError('Existing expected literals overlap boat descriptors')
    hook=plan['hooks'][70]
    hook['asm']=(prefix+'\n'+'.byte 0\n'*(EXTRA_OFFSET-0x2D000-len(prefix_bytes))+extra+
        '\n'+'.byte 0\n'*(actions.HELPER_OFFSET-EXTRA_OFFSET-len(extra_bytes))+main+
        '\n'+'.byte 0\n'*(LITERAL_OFFSET-actions.HELPER_OFFSET-len(main_bytes))+
        ''.join(f'.byte {b}\n' for b in blob))
    hook['purpose']+='; exact Abyss Kodama guide-to-shore EA6E request46 native queue with1155 family and collision/resource preflight'
    plan.update(abyss_boat_return_trial_revision=1,abyss_boat_common_actions=[170,1155,1156,1157],
        abyss_boat_request_dispatch=46,abyss_boat_motion_ids=[8,0],abyss_boat_local_event_indices=[0,120],
        abyss_boat_extra_code_offset=EXTRA_OFFSET,abyss_boat_extra_code_size=len(extra_bytes),
        abyss_boat_literal_offset=LITERAL_OFFSET,abyss_boat_literal_size=len(blob),
        abyss_boat_gameplay_validated=False,
        interaction_label='Abyss Kodama guide-to-shore / 引导至此岸',
        stage='offline_scoped_abyss_kodama_guide_candidate')
    plan['abyss_assembly_code_intervals'][hook['name']]=[[0,len(prefix_bytes)],
        [EXTRA_OFFSET-0x2D000,EXTRA_OFFSET-0x2D000+len(extra_bytes)],
        [0x2000,0x2000+plan['abyss_helper_code_size']]]
    current=assemble(plan,0x140000000,0x144000000)
    changed=tuple(i for i,(a,b) in enumerate(zip(previous,current)) if a['payload']!=b['payload'])
    if changed!=CHANGED_INDICES or any(a['patched']!=b['patched'] for a,b in zip(previous,current)):
        raise ValueError('Only aura70 private body may change')
    runtime.validate_layout(plan)
    return plan

