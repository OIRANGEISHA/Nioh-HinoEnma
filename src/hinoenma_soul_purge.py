"""Soul Purge reads the player's equipped weapon, preserving native buffs/costs."""
from copy import deepcopy
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_general_jutsu import digest, definition_guard, GUARD_CARRIER
from hinoenma_general_jutsu_timing import CHAIN_ROWS, CHAIN_OFFSET
from hinoenma_special_item_actions import _once
import hinoenma_soul_release as soul

PARENT_SHA256 = '60cf6b4af3cc094d915a5e8d97d1d8c3472f840d1238adb35a7219e1ee92a9f6'
ITEM = 51944
DEFINITION = ((0,ITEM),(4,0xF02),(0x104,0x405),(0x10C,7),
              (0x110,12652),(0x114,31711),(0x118,0),(0x11C,0xC2626))

def definition_checks(reg, failure):
    return ''.join(f'cmp {"word" if off==4 else "dword"} ptr [{reg}+{off}], {value}\njne {failure}\n'
                   for off,value in DEFINITION)

def gate_source():
    text=soul.gate_source()
    text=_once(text,'cmp dword ptr [r14], 64629\njne soul_gate_native\n',
        'cmp dword ptr [r14], 64629\njne soul_purge_gate_definition\n')
    text=_once(text,'mov rcx, rbp\ncall {data} + 0x7400\n',
        'jmp soul_purge_gate_resolve\nsoul_purge_gate_definition:\n'+
        definition_checks('r14','soul_gate_native')+
        'soul_purge_gate_resolve:\nmov rcx, rbp\ncall {data} + 0x7400\n')
    text=_once(text,'mov qword ptr [rsp+0x50], rax\n', '''cmp dword ptr [r14], 51944
jne soul_purge_gate_accept
mov rdx, qword ptr [rbp+0x240]
cmp r8b, byte ptr [rdx+0x9CC]
jne soul_gate_native
soul_purge_gate_accept:
mov qword ptr [rsp+0x50], rax
''')
    return text

def effect_source(effect, kind):
    # Inside A83AD0 RSP is aligned. Eight saves + 20-byte shadow space preserve
    # alignment. Original [RSP+60] carries the source item ID. Resolver uses no
    # SIMD registers and no native calls; all original buff parameters survive.
    save=soul.SAVE.replace('sub rsp, 0x28','sub rsp, 0x20')
    restore=soul.RESTORE.replace('add rsp, 0x28','add rsp, 0x20')
    return 'add rcx, rax\n'+save+f'''cmp dword ptr [rsp+0xC0], 51944
jne soul_purge_effect_native
cmp rdi, r14
jne soul_purge_effect_native
cmp dword ptr [rsi], {effect}
jne soul_purge_effect_native
cmp dword ptr [rsi+4], {kind}
jne soul_purge_effect_native
mov rcx, rdi
call {{data}} + 0x7400
test rax, rax
je soul_purge_effect_native
mov rdx, qword ptr [rdi+0x240]
cmp r8b, byte ptr [rdx+0x9CC]
jne soul_purge_effect_native
mov qword ptr [rsp+0x48], rax
soul_purge_effect_native:
'''+restore+'''cmp dword ptr [rcx], -1
jmp {return}
'''

def apply_soul_purge(parent):
    if digest(parent)!=PARENT_SHA256:
        raise ValueError('Exact published Beta6.1.4 required')
    plan=deepcopy(parent); hs={h['name']:h for h in plan['hooks']}
    if hs['HE_SoulReleaseEligibility']['asm']!=soul.gate_source():
        raise ValueError('Exact existing familiarity gate required')
    hs['HE_SoulReleaseEligibility']['asm']=gate_source()
    # Admit only this additional kind-2 self-cast definition. Its instant-cast
    # path remains native; the existing common41 path covers normal casting.
    h=hs[GUARD_CARRIER]; marker='.byte '+','.join(map(str,CHAIN_ROWS))+'\n'
    head,tail=h['asm'].split(marker)
    head=head.rstrip()+'\n'
    while head.endswith('nop\n'):head=head[:-4]
    old=definition_guard()
    special='''general_jutsu_family_7:
cmp dword ptr [rax], 51944
jne soul_purge_family_existing
'''+''.join(f'cmp {"word" if off==4 else "dword"} ptr [rax+{off}], {value}\njne general_jutsu_definition_no\n'
             for off,value in DEFINITION if off not in (0,0x10C))+'''jmp general_jutsu_family_ok_7
soul_purge_family_existing:
'''
    head=_once(head,old,_once(old,'general_jutsu_family_7:\n',special))
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encode(h,text=None):
        v={k:0x140000000+r for k,r in plan['targets'].items()}
        v.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm((text or h['asm']).format(**v),0x144000000+h['code_offset'])[0])
    padding=CHAIN_OFFSET-h['code_offset']-len(encode(h,head))
    if padding<0:raise ValueError('Definition guard would move the chain table')
    h['asm']=head+'nop\n'*padding+marker+tail
    # Use verified zero padding after the existing post-defeat hook; its code
    # and every old entrypoint remain byte-identical.
    carrier=hs['HE_PostDefeatHealEvent']
    if len(encode(carrier))>0x400:raise ValueError('Reserved Soul Purge slots occupied')
    carrier['code_capacity']=0x400
    for name,rva,offset,effect,kind in (
        ('HE_SoulPurgeAttackFamiliarity',0xA8AEE0,0x17400,12652,229),
        ('HE_SoulPurgeLuckFamiliarity',0xA8AFEB,0x17800,31711,230)):
        plan['hooks'].append(dict(name=name,rva=rva,length=6,original='4803c88339ff',
            code_offset=offset,code_capacity=0x400,asm=effect_source(effect,kind),
            purpose='Local Soul Purge familiar weapon read; native multiplier and consumption retained'))
    for h in plan['hooks']:
        if len(encode(h))>h['code_capacity']:raise ValueError('Hook capacity exceeded: '+h['name'])
    plan['soul_purge_candidate']=dict(revision=1,item=ITEM,native_familiarity_minimum=300,
        exact_selected_weapon=True,native_buff_scaling=True,native_familiarity_consumption=True,
        actor_inventory_save_writes=False,live_confirmation_pending=True)
    return plan
