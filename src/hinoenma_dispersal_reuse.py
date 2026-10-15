"""Admit released, player-owned Dispersal projectiles during another cast.

The old empty-object-list condition unnecessarily delayed this item after its
animation ended. This leaf validates the bounded native list without modifying
it. Held objects, different items, broken links and other owners still reject.
"""
from copy import deepcopy
import hashlib,json
from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
import hinoenma_sticky_dispersal_items as items
import hinoenma_wind_weakness_dragon as spells
import hinoenma_elemental_resistance_items as resistance
import hinoenma_spell_event_catchup as catchup
import hinoenma_guardian_sludge_items as jars
from hinoenma_special_item_actions import _once

PARENT_SHA256='ed3765613e7b17c6f3a0862bd1a423aa09fcc78c40cc9f4cedd3f7fd68bbe4a1'
GUARD_OFFSET=0x21C00
CHANGED=items.CHANGED
MAX_RELEASED=16

def guard_asm():
    # RCX=ctl, EAX=bool. Preserve every other GP register and all SIMD state.
    # Object +4 is the 16-bit type; +6 is an independent native instance number.
    text='''dispersal_released_objects:
push rdx
push rbx
push rsi
push r8
push r9
push r10
push r11
mov r8, qword ptr [rcx+0x720]
test r8, r8
je dispersal_objects_no
mov r9, qword ptr [rcx+0x728]
test r9, r9
jne dispersal_objects_scoped
cmp qword ptr [r8], r8
jne dispersal_objects_no
cmp qword ptr [r8+8], r8
jne dispersal_objects_no
jmp dispersal_objects_yes
dispersal_objects_scoped:
cmp r9, 16
ja dispersal_objects_no
cmp dword ptr [rcx+0x548], 22722
jne dispersal_objects_no
cmp dword ptr [rcx+0x54C], 9
jne dispersal_objects_no
cmp qword ptr [rcx+0x558], 0
jne dispersal_objects_no
mov rdx, qword ptr [rcx+0x50]
test rdx, rdx
je dispersal_objects_no
mov rax, {data}
cmp qword ptr [rax+0x10], rdx
jne dispersal_objects_no
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne dispersal_objects_no
cmp dword ptr [rdx+4], 0x10000
jne dispersal_objects_no
mov r10, qword ptr [r8]
mov r11, r8
dispersal_objects_next:
cmp r10, r8
je dispersal_objects_no
cmp r10, 0x10000
jb dispersal_objects_no
mov rax, r10
shr rax, 47
jne dispersal_objects_no
cmp qword ptr [r10+8], r11
jne dispersal_objects_no
mov rbx, qword ptr [r10+0x10]
cmp rbx, 0x10000
jb dispersal_objects_no
mov rax, rbx
shr rax, 47
jne dispersal_objects_no
cmp qword ptr [rbx+8], rdx
jne dispersal_objects_no
cmp qword ptr [rbx+0x38], 0
jne dispersal_objects_no
cmp qword ptr [rbx+0x40], 0
jne dispersal_objects_no
cmp dword ptr [rbx+0x48], 1
jne dispersal_objects_no
cmp byte ptr [rbx+0x4C], 0
jne dispersal_objects_no
mov rsi, qword ptr [rbx+0x20]
cmp rsi, 0x10000
jb dispersal_objects_no
mov rax, rsi
shr rax, 47
jne dispersal_objects_no
cmp dword ptr [rsi], 0xF3C55
jne dispersal_objects_no
cmp word ptr [rsi+4], 4
jne dispersal_objects_no
cmp qword ptr [rsi+0x200], rdx
jne dispersal_objects_no
cmp dword ptr [rsi+0x400], 22722
jne dispersal_objects_no
cmp byte ptr [rsi+0x1AD], 1
jne dispersal_objects_no
mov r11, r10
mov r10, qword ptr [r10]
dec r9
jne dispersal_objects_next
cmp r10, r8
jne dispersal_objects_no
cmp qword ptr [r8+8], r11
jne dispersal_objects_no
dispersal_objects_yes:
mov eax, 1
jmp dispersal_objects_return
dispersal_objects_no:
xor eax, eax
dispersal_objects_return:
pop r11
pop r10
pop r9
pop r8
pop rsi
pop rbx
pop rdx
ret
'''
    return text

GUARD_ASM=guard_asm()

def _empty_check(register,failure):
    return f'''cmp qword ptr [{register}+0x728], 0
jne {failure}
mov rax, qword ptr [{register}+0x720]
test rax, rax
je {failure}
cmp qword ptr [rax], rax
jne {failure}
cmp qword ptr [rax+8], rax
jne {failure}
'''

def _replace_check(text,register,failure,count):
    original=_empty_check(register,failure)
    if text.count(original)!=count:raise ValueError('Exact empty-list checks required')
    wrapper='' if register=='rcx' else 'push rcx\nmov rcx, rdi\n'
    wrapper+='call {data} + 0x12C00\n'
    if register!='rcx':wrapper+='pop rcx\n'
    return text.replace(original,wrapper+f'test al, al\nje {failure}\n')

def apply_dispersal_reuse(parent):
    digest=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest(parent)!=PARENT_SHA256:raise ValueError('Exact tested sticky/dispersal candidate required')
    plan=deepcopy(parent);hooks={h['name']:h for h in plan['hooks']}
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encoded(text,h,offset):
        values={k:0x140000000+r for k,r in plan['targets'].items()}
        values.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(text.format(**values),0x144000000+offset)[0])
    guard=hooks[jars.GUARD_CARRIER]
    old=encoded(guard['asm'],guard,guard['code_offset'])
    padding=GUARD_OFFSET-guard['code_offset']-len(old)
    if padding<0:raise ValueError('Released-object guard padding occupied')
    guard['asm']+='\n'+'nop\n'*padding+GUARD_ASM
    carrier=hooks[spells.CARRIER_NAME]
    if not carrier['asm'].endswith(resistance.GUARD_ASM):raise ValueError('Resistance tail differs')
    prefix,body=carrier['asm'].split('dung_fan_helper:')
    helper,tail=('dung_fan_helper:'+body).split('arrow_sloth_lookup_entry:')
    lookup,tail=('arrow_sloth_lookup_entry:'+tail).split(spells.EXTRA_GUARD_ASM)
    def unpad(raw):
        raw=raw.rstrip()+'\n'
        while raw.endswith('nop\n'):raw=raw[:-4]
        return raw.rstrip()+'\n'
    helper=_replace_check(unpad(helper),'rdi','dung_fan_fail_b',1)
    helper=_replace_check(helper,'rdi','dung_fan_restore',1)
    lookup=_replace_check(unpad(lookup),'rdi','arrow_sloth_lookup_restore',2)
    hsize=len(encoded(helper,carrier,spells.HELPER_OFFSET));lsize=len(encoded(lookup,carrier,spells.LOOKUP_OFFSET))
    if hsize>0x1800 or lsize>0x1400:raise ValueError('Fixed helper gap exhausted')
    carrier['asm']=(prefix+helper+'\n'+'nop\n'*(0x1800-hsize)+lookup+'\n'+'nop\n'*(0x1400-lsize)+spells.EXTRA_GUARD_ASM+tail)
    event=hooks[catchup.CARRIER]
    event['asm']=_replace_check(event['asm'],'rcx','spell_gap_reject',1)
    for name in CHANGED:
        h=hooks[name];prior=next(x for x in parent['hooks'] if x['name']==name)
        before=encoded(prior['asm'],prior,prior['code_offset']);after=encoded(h['asm'],h,h['code_offset'])
        if len(after)>h['code_capacity']:raise ValueError('Reuse guard exceeds owned code')
        if name==spells.CARRIER_NAME and (len(after)!=len(before) or after[:0x4000]!=before[:0x4000] or after[0x6C00:]!=before[0x6C00:]):
            raise ValueError('Fixed spell surrounding entries changed')
        if name==jars.GUARD_CARRIER and not after.startswith(before):raise ValueError('Existing map/definition guards changed')
        if name==catchup.CARRIER and before[:0x300]!=after[:0x300]:raise ValueError('Projectile prefix changed')
    plan['dispersal_reuse_candidate']=dict(revision=2,item_id=22722,released_template=0xF3C55,
        max_released_objects=MAX_RELEASED,native_list_not_modified=True,
        spawned_object_type_width=16,independent_spawn_instance_number_allowed=True,
        native_cast_timing_and_effect_lifetime_unchanged=True,live_confirmation_pending=True)
    if digest(parent)!=PARENT_SHA256:raise ValueError('Parent mutated')
    return plan
