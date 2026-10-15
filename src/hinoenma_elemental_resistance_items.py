"""Five observed Seimei resistance requests through native common41.

Only exact kind3 item definitions are admitted. The existing common172 entry,
common41 schedule, native buffs, reuse rules and inventory ownership stay native.
The existing injury and common1003 repeat-cast resolvers remain in place.
"""
from copy import deepcopy
import hashlib, json
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
import hinoenma_wind_weakness_dragon as previous
from hinoenma_special_item_actions import _once

PARENT_SHA256='1ca87b85f836f695b69c0fc7befb8c09efd596bd351fc95a83ec4d4e8ede1e79'
CARRIER=previous.CARRIER_NAME
GUARD_OFFSET=0x68E00
CHANGED=(CARRIER,)
# Observed IDs in the user's fire, water, wind, lightning, earth order.
ITEM_SPECS=(
    (7785,3,0,7,7,(63190,0,0),0xC2626,41,110,192),
    (805,3,0,7,7,(62930,0,0),0xC2626,41,110,192),
    (64630,3,0,7,7,(45181,0,0),0xC2626,41,110,192),
    (35156,3,0,7,7,(51630,0,0),0xC2626,41,110,192),
    (10101,3,0,7,7,(21144,0,0),0xC2626,41,110,192),
)

def definition_guard():
    # RAX=already looked-up definition, RDI=owned controller. Leaf function;
    # no native calls or memory writes. Wrapped callers save volatile state.
    text='''elemental_resistance_definition_guard:
mov r11d, dword ptr [rdi+0x548]
cmp dword ptr [rax], r11d
jne elemental_resistance_no
cmp word ptr [rax+4], 3
jne elemental_resistance_no
cmp dword ptr [rax+0x104], 7
jne elemental_resistance_no
cmp dword ptr [rax+0x10C], 7
jne elemental_resistance_no
cmp dword ptr [rdi+0x54C], 7
jne elemental_resistance_no
cmp byte ptr [rdi+0x570], 0
jne elemental_resistance_no
cmp qword ptr [rax+0x114], 0
jne elemental_resistance_no
cmp dword ptr [rax+0x11C], 0xC2626
jne elemental_resistance_no
'''
    for ident,_,_,_,_,effects,*_ in ITEM_SPECS:
        text+=f'cmp r11d, {ident}\nje elemental_resistance_effect_{ident}\n'
    text+='jmp elemental_resistance_no\n'
    for ident,_,_,_,_,effects,*_ in ITEM_SPECS:
        text+=(f'elemental_resistance_effect_{ident}:\nmov r10d, {effects[0]}\n'
               'jmp elemental_resistance_effect\n')
    return text+'''elemental_resistance_effect:
cmp dword ptr [rax+0x110], r10d
jne elemental_resistance_no
mov eax, 1
ret
elemental_resistance_no:
xor eax, eax
ret
'''

GUARD_ASM=definition_guard()

def _extend_definition(text,last,prefix):
    anchor=f'je {prefix}_definition_{last}\njmp {prefix}_restore\n'
    return _once(text,anchor,f'''je {prefix}_definition_{last}
call {{data}} + 0x59E00
test al, al
je {prefix}_restore
mov dword ptr [rsp+0x94], 41
mov dword ptr [rsp+0x98], 110
jmp {prefix}_definition_done
''')

def apply_elemental_resistance_items(parent):
    fingerprint=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if fingerprint(parent)!=PARENT_SHA256:
        raise ValueError('Exact packaged Beta6.1.1 parent required')
    plan=deepcopy(parent)
    carrier=next(h for h in plan['hooks'] if h['name']==CARRIER)
    if carrier['asm'].count(previous.HELPER_ASM)!=1 or not carrier['asm'].endswith(previous.EXTRA_GUARD_ASM):
        raise ValueError('Expected retained fixed spell helper and auxiliary guard')
    prefix,tail=carrier['asm'].split(previous.HELPER_ASM)
    body,guard_end=tail.split(previous.EXTRA_GUARD_ASM)
    if guard_end:raise ValueError('Occupied resistance guard tail')
    first_padding,lookup_body=body.split('arrow_sloth_lookup_entry:\n')
    if first_padding.replace('nop','').strip():raise ValueError('Occupied helper gap')
    lookup='arrow_sloth_lookup_entry:\n'+lookup_body
    while lookup.endswith('nop\n'):lookup=lookup[:-4]
    lookup=lookup.rstrip()+'\n'
    helper=_extend_definition(previous.HELPER_ASM,previous.ALL_ITEM_SPECS[-1][0],'dung_fan')
    # All existing item IDs retain their path. Only the five new kind3 casts
    # re-enter the existing full record/schedule recheck after clip callbacks.
    helper=_once(helper,'je wind_weakness_dragon_post_44607\njmp wind_weakness_dragon_post_done\n',
        '''je wind_weakness_dragon_post_44607
cmp dword ptr [rsp+0x94], 41
jne wind_weakness_dragon_post_done
cmp dword ptr [rdi+0x548], 64367
je wind_weakness_dragon_post_done
mov rax, qword ptr [rsp+0xC8]
call {data} + 0x59E00
test al, al
je dung_fan_restore
jmp wind_weakness_dragon_post_resources
''')
    lookup=_extend_definition(lookup,previous.LOOKUP_ITEM_SPECS[-1][0],'arrow_sloth_lookup')
    lookup=_once(lookup,
        'je arrow_sloth_lookup_post_definition_44930\njmp arrow_sloth_lookup_restore\n',
        '''je arrow_sloth_lookup_post_definition_44930
call {data} + 0x59E00
test al, al
je arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_success
''')
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    values={k:0x140000000+r for k,r in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+carrier['rva']+carrier['length']})
    def encode(text,offset):return bytes(ks.asm(text.format(**values),0x144000000+offset)[0])
    old=encode(carrier['asm'],carrier['code_offset'])
    hsize=len(encode(helper,previous.HELPER_OFFSET))
    lsize=len(encode(lookup,previous.LOOKUP_OFFSET))
    esize=len(encode(previous.EXTRA_GUARD_ASM,previous.EXTRA_GUARD_OFFSET))
    if (hsize>previous.LOOKUP_OFFSET-previous.HELPER_OFFSET
        or lsize>previous.EXTRA_GUARD_OFFSET-previous.LOOKUP_OFFSET
        or previous.EXTRA_GUARD_OFFSET+esize>GUARD_OFFSET):
        raise ValueError('Fixed entry gap exhausted')
    carrier['asm']=(prefix+helper+'\n'+'nop\n'*(previous.LOOKUP_OFFSET-previous.HELPER_OFFSET-hsize)
        +lookup+'\n'+'nop\n'*(previous.EXTRA_GUARD_OFFSET-previous.LOOKUP_OFFSET-lsize)
        +previous.EXTRA_GUARD_ASM+'\n'+'nop\n'*(GUARD_OFFSET-previous.EXTRA_GUARD_OFFSET-esize)+GUARD_ASM)
    new=encode(carrier['asm'],carrier['code_offset'])
    if len(new)>carrier['code_capacity']:raise ValueError('Resistance guard exceeds owned capacity')
    start=previous.HELPER_OFFSET-carrier['code_offset']
    e0=previous.EXTRA_GUARD_OFFSET-carrier['code_offset']
    if new[:start]!=old[:start] or new[e0:e0+esize]!=old[e0:e0+esize]:
        raise ValueError('Existing item prefix or auxiliary guard changed')
    intervals=plan['abyss_assembly_code_intervals'][CARRIER]
    if intervals[-1]!=[0x4000,len(old)]:raise ValueError('Unexpected relocation interval')
    intervals[-1]=[0x4000,len(new)]
    plan['elemental_resistance_items_candidate']=dict(revision=1,item_ids=[r[0] for r in ITEM_SPECS],
        native_common_action=41,native_motion=110,kind=3,native_buff_and_stock_rules_unchanged=True,
        live_confirmation_pending=True)
    if fingerprint(parent)!=PARENT_SHA256:raise ValueError('Parent mutated')
    return plan
