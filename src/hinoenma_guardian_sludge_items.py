"""Two exact item entries using existing native summon and throw schedules.

The out-of-line guard fits in owned padding; the fixed helper, effect and
resource entry addresses remain intact. Native code owns stock and effects.
"""
from copy import deepcopy
import hashlib,json,struct
from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
import hinoenma_special_item_actions as special

PARENT_SHA256='8312773f885640dc53dbc1b50887746fa65e178d59d790bd4d8b07b45f919023'
ENTRY_CARRIER='HE_SameTemplateUnloadResources'
GUARD_CARRIER='HE_MapVisualSpawnPrivate'
GUARD_OFFSET=0x21400
CHANGED=(ENTRY_CARRIER,GUARD_CARRIER)
ITEM_SPECS=(
    (62705,2,15,22,0x2005,(0,0,0),0xC2626,610,111,286),
    (20527,1,0,4,0x10005,(0,0,0),0xD890A,165,103,100),
)

def _guard():
    # RAX=definition, EDX=0 at entry or 1 after resource callbacks, RDI=ctl.
    # R8 addresses the enclosing helper's stack after two pushes + CALL.
    text='''guardian_sludge_guard:
push rbx
push rsi
lea r8, [rsp+0x18]
mov r9d, edx
'''
    for ident,*_ in ITEM_SPECS:
        text+=f'cmp dword ptr [rdi+0x548], {ident}\nje guardian_sludge_definition_{ident}\n'
    text+='''test r9d, r9d
jne guardian_sludge_true
jmp guardian_sludge_false
'''
    for ident,kind,sub,category,flags,effects,spawn,action,motion,_ in ITEM_SPECS:
        text+=f'guardian_sludge_definition_{ident}:\n'
        for off,value in ((0,ident),(4,kind|sub<<8),(0x104,flags),(0x10C,category),
                          *((0x110+i*4,v) for i,v in enumerate(effects)),(0x11C,spawn)):
            width='word' if off==4 else 'dword'
            text+=f'cmp {width} ptr [rax+{off}], {value}\njne guardian_sludge_false\n'
        text+=(f'cmp dword ptr [rdi+0x54C], {category}\njne guardian_sludge_false\n'
               f'mov r10d, {action}\nmov r11d, {motion}\njmp guardian_sludge_match\n')
    text+='''guardian_sludge_match:
cmp byte ptr [rdi+0x570], 0
jne guardian_sludge_false
test r9d, r9d
jne guardian_sludge_post
mov dword ptr [r8+0x94], r10d
mov dword ptr [r8+0x98], r11d
jmp guardian_sludge_true
guardian_sludge_post:
cmp dword ptr [r8+0x94], r10d
jne guardian_sludge_false
cmp dword ptr [r8+0x98], r11d
jne guardian_sludge_false
mov rsi, qword ptr [rdi+0x80]
test rsi, rsi
je guardian_sludge_false
cmp qword ptr [r8+0x80], rsi
jne guardian_sludge_false
mov ecx, dword ptr [rsi+0x130]
test ecx, ecx
je guardian_sludge_false
cmp ecx, 4096
ja guardian_sludge_false
mov rdx, qword ptr [rsi+0x128]
test rdx, rdx
je guardian_sludge_false
xor ebx, ebx
guardian_sludge_scan:
mov rax, qword ptr [rdx]
test rax, rax
je guardian_sludge_next
cmp dword ptr [rax], r10d
jne guardian_sludge_next
cmp byte ptr [rax+0x40], 0
je guardian_sludge_next
cmp qword ptr [rax+0x38], rsi
jne guardian_sludge_false
test rbx, rbx
jne guardian_sludge_false
mov rbx, rax
guardian_sludge_next:
add rdx, 8
dec ecx
jne guardian_sludge_scan
test rbx, rbx
je guardian_sludge_false
mov rax, qword ptr [rbx+0x20]
test rax, rax
je guardian_sludge_false
cmp qword ptr [r8+0xD0], rax
jne guardian_sludge_false
cmp dword ptr [rax+0x20], r11d
jne guardian_sludge_false
cmp dword ptr [rax+0x34], -1
jne guardian_sludge_false
cmp r10d, 610
je guardian_sludge_schedule_610
jmp guardian_sludge_schedule_165
'''
    for action in (610,165):
        text+=f'guardian_sludge_schedule_{action}:\n'
        raw=bytes.fromhex(special.SCHEDULE_HEX[action])
        for off in range(0,96,8):
            value=struct.unpack_from('<Q',raw,off)[0]
            text+=f'mov r10, {value}\ncmp qword ptr [rax+{64+off}], r10\njne guardian_sludge_false\n'
        text+='jmp guardian_sludge_true\n'
    return text+'''guardian_sludge_true:
mov eax, 1
jmp guardian_sludge_return
guardian_sludge_false:
xor eax, eax
guardian_sludge_return:
pop rsi
pop rbx
ret
'''

GUARD_ASM=_guard()

def apply_guardian_sludge_items(previous):
    digest=hashlib.sha256(json.dumps(previous,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=PARENT_SHA256:raise ValueError('Exact tested repeated-cast parent required')
    plan=deepcopy(previous);hooks={h['name']:h for h in plan['hooks']}
    entry,guard=hooks[ENTRY_CARRIER],hooks[GUARD_CARRIER]
    if entry['asm'].count(special.HELPER_ASM)!=1:raise ValueError('Fixed special-item helper differs')
    helper=special.HELPER_ASM
    last=special.ITEM_SPECS[-1][0]
    anchor=f'je special_item_definition_{last}\njmp special_item_restore\n'
    helper=special._once(helper,anchor,f'''je special_item_definition_{last}
xor edx, edx
call {{data}} + 0x12400
test al, al
je special_item_restore
jmp special_item_definition_done
''')
    helper=special._once(helper,'mov rcx, rdi\nmov edx, 172\n',
        '''mov edx, 1
mov rax, qword ptr [rsp+0xC8]
call {data} + 0x12400
test al, al
je special_item_restore
mov rcx, rdi
mov edx, 172
''')
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encoded(text,h,offset):
        values={k:0x140000000+r for k,r in plan['targets'].items()}
        values.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(text.format(**values),0x144000000+offset)[0])
    prefix,tail=entry['asm'].split(special.HELPER_ASM)
    old_size=len(encoded(special.HELPER_ASM,entry,special.HELPER_OFFSET))
    new_size=len(encoded(helper,entry,special.HELPER_OFFSET))
    limit=special.EFFECT_HELPER_OFFSET-special.HELPER_OFFSET
    padding='\n'+'nop\n'*(limit-old_size)
    if new_size>limit or not tail.startswith(padding):raise ValueError('Special-item fixed gap unavailable')
    old=encoded(entry['asm'],entry,entry['code_offset'])
    entry['asm']=prefix+helper+'\n'+'nop\n'*(limit-new_size)+tail[len(padding):]
    new=encoded(entry['asm'],entry,entry['code_offset'])
    if (old[:special.HELPER_OFFSET-entry['code_offset']]!=new[:special.HELPER_OFFSET-entry['code_offset']]
        or old[special.EFFECT_HELPER_OFFSET-entry['code_offset']:]!=new[special.EFFECT_HELPER_OFFSET-entry['code_offset']:]):
        raise ValueError('Existing fixed native-effect/resource entries changed')
    old_guard=encoded(guard['asm'],guard,guard['code_offset'])
    gap=GUARD_OFFSET-guard['code_offset']-len(old_guard)
    if gap<0:raise ValueError('Owned guard padding occupied')
    guard['asm']+='\n'+'nop\n'*gap+GUARD_ASM
    for hook in (entry,guard):
        raw=encoded(hook['asm'],hook,hook['code_offset'])
        if len(raw)>hook['code_capacity']:raise ValueError('Item extension exceeds carrier')
    if not encoded(guard['asm'],guard,guard['code_offset']).startswith(old_guard):raise ValueError('Map spawn prefix changed')
    plan['guardian_sludge_items_candidate']=dict(revision=1,item_ids=[62705,20527],
        native_common_actions=[610,165],native_item_effect_stock_path_unchanged=True,
        live_confirmation_pending=True)
    return plan
