"""Keep an accepted repeated cast in the common bank after common1003 movement.

Extend the existing exact-definition lookup only. The native selected queries,
pending request, item definition, cast schedule and resource checks still run.
Both pre-call and post-call checks prove the current owned movement record.
"""
from copy import deepcopy
import hashlib,json,struct
from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
from hinoenma_wind_weakness_dragon import LOOKUP_ASM,EXTRA_GUARD_ASM,EXTRA_GUARD_OFFSET

PARENT_SHA256='3c6f68faff37344a00635a229cc45e8ee918814556d0432b5fcedfc63603a7f9'
CARRIER='HE_LivingWeaponDigitNine'
GUARD_CARRIER='HE_MapVisualRestorePrivate'
GUARD_OFFSET=0x23A00
LOOKUP_OFFSET=0x66800
CHANGED=(CARRIER,GUARD_CARRIER)
MOVEMENT_SCHEDULE=bytes.fromhex('ffff0000ffff'*16)

def guard_asm():
    text='''item_recast_movement_guard:
push rcx
push r8
push r9
push r10
push r11
mov r10, qword ptr [rsp+0x1E8]
mov r11, {salt_hurt_first_return}
cmp r10, r11
je item_recast_caller
mov r11, {salt_hurt_next_return}
cmp r10, r11
je item_recast_caller
mov r11, {salt_hurt_qualification_return}
cmp r10, r11
jne item_recast_no
item_recast_caller:
cmp dword ptr [rdi+0x68], 2
jne item_recast_no
cmp dword ptr [rax], 1003
jne item_recast_no
cmp dword ptr [rdx+0x20], 20
jne item_recast_no
cmp dword ptr [rdx+0x34], -1
jne item_recast_no
cmp dword ptr [rax+0x80], 0x311709
jne item_recast_no
mov r10, qword ptr [rdi+0x80]
cmp qword ptr [rax+0x38], r10
jne item_recast_no
mov r11, qword ptr [r10+0x50]
test r11, r11
je item_recast_no
cmp qword ptr [rax+0x78], r11
jne item_recast_no
mov ecx, dword ptr [r10+0x130]
test ecx, ecx
je item_recast_no
cmp ecx, 4096
ja item_recast_no
mov r10, qword ptr [r10+0x128]
test r10, r10
je item_recast_no
xor r8d, r8d
item_recast_current_scan:
cmp qword ptr [r10], rax
jne item_recast_scan_next
inc r8d
item_recast_scan_next:
add r10, 8
dec ecx
jne item_recast_current_scan
cmp r8d, 1
jne item_recast_no
'''
    for off in range(0,96,8):
        value=struct.unpack_from('<Q',MOVEMENT_SCHEDULE,off)[0]
        text+=f'mov r10, {value}\ncmp qword ptr [rdx+{64+off}], r10\njne item_recast_no\n'
    return text+'''mov eax, 1
jmp item_recast_return
item_recast_no:
xor eax, eax
item_recast_return:
pop r11
pop r10
pop r9
pop r8
pop rcx
ret
'''

def apply_item_recast_lookup(previous):
    digest=hashlib.sha256(json.dumps(previous,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=PARENT_SHA256:raise ValueError('Exact tested item-hurt candidate required')
    plan=deepcopy(previous);hooks={h['name']:h for h in plan['hooks']}
    carrier,guard=hooks[CARRIER],hooks[GUARD_CARRIER]
    lookup=LOOKUP_ASM
    for anchor,label in (('arrow_sloth_lookup_existing_cast:', 'arrow_sloth_lookup_definition'),
                         ('arrow_sloth_lookup_post_cast:', 'arrow_sloth_lookup_post_bank')):
        if lookup.count(anchor)!=1:raise ValueError('Lookup phase anchor differs')
        extension=f'''cmp dword ptr [rax], 1003
jne {anchor[:-1]}_ordinary
call {{data}} + 0x14A00
test eax, eax
je arrow_sloth_lookup_restore
jmp {label}
{anchor[:-1]}_ordinary:
'''
        lookup=lookup.replace(anchor,anchor+'\n'+extension)
    if carrier['asm'].count(LOOKUP_ASM)!=1 or not carrier['asm'].endswith(EXTRA_GUARD_ASM):
        raise ValueError('Retained spell lookup/guard differs')
    prefix,tail=carrier['asm'].split(LOOKUP_ASM)
    padding=tail[:-len(EXTRA_GUARD_ASM)]
    if padding.replace('nop','').strip():raise ValueError('Lookup guard gap occupied')
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encoded(asm,h,offset):
        values={k:0x140000000+v for k,v in plan['targets'].items()}
        values.update(data=0x14400F000,**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(asm.format(**values),0x144000000+offset)[0])
    length=len(encoded(lookup,carrier,LOOKUP_OFFSET))
    if LOOKUP_OFFSET+length>EXTRA_GUARD_OFFSET:raise ValueError('Lookup guard gap too small')
    carrier['asm']=prefix+lookup+'\n'+'nop\n'*(EXTRA_GUARD_OFFSET-LOOKUP_OFFSET-length)+EXTRA_GUARD_ASM
    old_guard=encoded(guard['asm'],guard,guard['code_offset'])
    padding=GUARD_OFFSET-guard['code_offset']-len(old_guard)
    if padding<0:raise ValueError('Recast helper gap occupied')
    guard['asm']+='\n'+'nop\n'*padding+guard_asm()
    for h in (carrier,guard):
        raw=encoded(h['asm'],h,h['code_offset'])
        if len(raw)>h['code_capacity']:raise ValueError('Recast payload exceeds capacity')
    if not encoded(guard['asm'],guard,guard['code_offset']).startswith(old_guard):
        raise ValueError('Existing injury helper changed')
    plan['item_recast_lookup_candidate']=dict(revision=1,current_common_action=1003,current_motion=20,
        source_first=5897,source_count=49,exact_request_definition_checks_retained=True,
        native_input_mapping_unchanged=True,live_confirmation_pending=True)
    return plan
