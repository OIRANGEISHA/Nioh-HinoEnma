"""Two observed requests through native throw165 and spell42.

Exact definitions extend the existing scoped item entry and common-bank lookup.
Dispersal retains native event catch-up, injury and moving-recast behavior.
No inventory, effect, damage or target state is synthesized.
"""
from copy import deepcopy
import hashlib, json
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
import hinoenma_guardian_sludge_items as jars
import hinoenma_wind_weakness_dragon as spells
import hinoenma_elemental_resistance_items as resistance
import hinoenma_spell_event_catchup as catchup
from hinoenma_special_item_actions import _once

PARENT_SHA256='f76274c57b2d0e6abd44a738cd49fef7d6aabebdbf57c3cfc3346a0fbd9f9847'
GUARD_OFFSET=0x21A00
CHANGED=(spells.CARRIER_NAME,catchup.CARRIER,jars.GUARD_CARRIER)
ITEM_SPECS=(
    (57901,1,0,4,0x10005,(0,0,0),0x2299A,165,103,100),
    (22722,2,15,9,5,(0,0,0),0xF3C55,42,111,194),
)

def _fields(spec, failure):
    ident,kind,sub,category,flags,effects,spawn,*_=spec
    text=''
    for off,value in ((0,ident),(4,kind|sub<<8),(0x104,flags),(0x10C,category),
                      *((0x110+i*4,v) for i,v in enumerate(effects)),(0x11C,spawn)):
        text+=f'cmp {"word" if off==4 else "dword"} ptr [rax+{off}], {value}\njne {failure}\n'
    return text+f'cmp dword ptr [rdi+0x54C], {category}\njne {failure}\n'

# Leaf called only inside existing fully saved entry/lookup helpers.
DISPERSAL_GUARD_ASM=('dispersal_definition_guard:\n'
    'cmp dword ptr [rdi+0x548], 22722\njne dispersal_definition_no\n'
    +_fields(ITEM_SPECS[1],'dispersal_definition_no')+
    'cmp byte ptr [rdi+0x570], 0\njne dispersal_definition_no\n'
    'mov eax, 1\nret\ndispersal_definition_no:\nxor eax, eax\nret\n')

def _definition_extension(text,last,prefix):
    anchor=f'je {prefix}_definition_{last}\n'
    return _once(text,anchor,anchor+f'''cmp dword ptr [rdi+0x548], 22722
jne {prefix}_dispersal_existing
call {{data}} + 0x12A00
test al, al
je {prefix}_restore
mov dword ptr [rsp+0x94], 42
mov dword ptr [rsp+0x98], 111
jmp {prefix}_definition_done
{prefix}_dispersal_existing:
''')

def apply_sticky_dispersal_items(parent):
    fingerprint=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if fingerprint(parent)!=PARENT_SHA256:raise ValueError('Exact packaged Beta6.1.2 parent required')
    plan=deepcopy(parent);hooks={h['name']:h for h in plan['hooks']}
    carrier=hooks[spells.CARRIER_NAME];guard=hooks[jars.GUARD_CARRIER];event=hooks[catchup.CARRIER]
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encode(text,h,offset):
        values={k:0x140000000+r for k,r in plan['targets'].items()}
        values.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(text.format(**values),0x144000000+offset)[0])

    # The existing auxiliary jar guard already feeds native165; only add this ID.
    jar_guard=_once(jars.GUARD_ASM,'je guardian_sludge_definition_20527\n',
        'je guardian_sludge_definition_20527\n'
        'cmp dword ptr [rdi+0x548], 57901\nje guardian_sludge_definition_57901\n')
    jar_guard=_once(jar_guard,'guardian_sludge_match:\n',
        'guardian_sludge_definition_57901:\n'+_fields(ITEM_SPECS[0],'guardian_sludge_false')+
        'mov r10d, 165\nmov r11d, 103\njmp guardian_sludge_match\n'
        'guardian_sludge_match:\n')
    if not guard['asm'].endswith(jars.GUARD_ASM):raise ValueError('Jar guard tail differs')
    prefix=guard['asm'][:-len(jars.GUARD_ASM)]
    if len(encode(prefix,guard,guard['code_offset']))!=jars.GUARD_OFFSET-guard['code_offset']:
        raise ValueError('Jar guard fixed entry changed')
    size=len(encode(jar_guard,guard,jars.GUARD_OFFSET))
    if jars.GUARD_OFFSET+size>GUARD_OFFSET:raise ValueError('Jar guard exhausted owned padding')
    guard['asm']=prefix+jar_guard+'\n'+'nop\n'*(GUARD_OFFSET-jars.GUARD_OFFSET-size)+DISPERSAL_GUARD_ASM

    # Split fixed regions without moving the published helper/lookup entries.
    text=carrier['asm']
    if text.count('dung_fan_helper:')!=1 or not text.endswith(resistance.GUARD_ASM):
        raise ValueError('Expected resistance-release spell helper')
    prefix,body=text.split('dung_fan_helper:')
    helper,tail=('dung_fan_helper:'+body).split('arrow_sloth_lookup_entry:')
    lookup,tail=('arrow_sloth_lookup_entry:'+tail).split(spells.EXTRA_GUARD_ASM)
    for raw in (helper,lookup):
        if not raw.rstrip().endswith('nop'):raise ValueError('Expected fixed-entry padding')
    def strip_padding(raw):
        raw=raw.rstrip()+'\n'
        while raw.endswith('nop\n'):raw=raw[:-4]
        return raw.rstrip()+'\n'
    helper=strip_padding(helper);lookup=strip_padding(lookup)
    helper=_definition_extension(helper,spells.ALL_ITEM_SPECS[-1][0],'dung_fan')
    helper=_once(helper,'je wind_weakness_dragon_post_44607\n',
        '''je wind_weakness_dragon_post_44607
cmp dword ptr [rdi+0x548], 22722
jne dispersal_post_existing
mov rax, qword ptr [rsp+0xC8]
call {data} + 0x12A00
test al, al
je dung_fan_restore
jmp wind_weakness_dragon_post_resources
dispersal_post_existing:
''')
    lookup=_definition_extension(lookup,spells.LOOKUP_ITEM_SPECS[-1][0],'arrow_sloth_lookup')
    lookup=_once(lookup,'je arrow_sloth_lookup_post_definition_44930\n',
        '''je arrow_sloth_lookup_post_definition_44930
cmp dword ptr [rdi+0x548], 22722
jne dispersal_lookup_post_existing
call {data} + 0x12A00
test al, al
je arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_success
dispersal_lookup_post_existing:
''')
    hsize=len(encode(helper,carrier,spells.HELPER_OFFSET));lsize=len(encode(lookup,carrier,spells.LOOKUP_OFFSET))
    if (hsize>spells.LOOKUP_OFFSET-spells.HELPER_OFFSET or
            lsize>spells.EXTRA_GUARD_OFFSET-spells.LOOKUP_OFFSET):raise ValueError('Spell fixed gap exhausted')
    carrier['asm']=(prefix+helper+'\n'+'nop\n'*(spells.LOOKUP_OFFSET-spells.HELPER_OFFSET-hsize)
        +lookup+'\n'+'nop\n'*(spells.EXTRA_GUARD_OFFSET-spells.LOOKUP_OFFSET-lsize)+spells.EXTRA_GUARD_ASM+tail)

    # The exact same native42 startup can skip its early create event. Keep the
    # one-shot marker's full owner/schedule/epoch checks and add only this ID.
    event['asm']=_once(event['asm'],
        'cmp dword ptr [rcx+0x548], 44930\njne spell_gap_reject\n',
        '''cmp dword ptr [rcx+0x548], 44930
je dispersal_gap_category
cmp dword ptr [rcx+0x548], 22722
jne spell_gap_reject
dispersal_gap_category:
''')
    for name in CHANGED:
        h=hooks[name];old=next(x for x in parent['hooks'] if x['name']==name)
        raw=encode(h['asm'],h,h['code_offset']);prior=encode(old['asm'],old,old['code_offset'])
        if len(raw)>h['code_capacity']:raise ValueError('New item payload exceeds owned capacity')
        if name==spells.CARRIER_NAME:
            start=spells.HELPER_OFFSET-h['code_offset'];end=spells.EXTRA_GUARD_OFFSET-h['code_offset']
            if len(raw)!=len(prior) or raw[:start]!=prior[:start] or raw[end:]!=prior[end:]:
                raise ValueError('Fixed spell outer regions changed')
        if name==jars.GUARD_CARRIER and raw[:0x400]!=prior[:0x400]:raise ValueError('Map spawn prefix changed')
        if name==catchup.CARRIER and raw[:0x300]!=prior[:0x300]:raise ValueError('Projectile prefix changed')
    plan['sticky_dispersal_items_candidate']=dict(revision=1,item_ids=[57901,22722],
        native_common_actions=[165,42],native_effect_stock_rules_unchanged=True,
        existing_injury_and_recast_preserved=True,live_confirmation_pending=True)
    if fingerprint(parent)!=PARENT_SHA256:raise ValueError('Parent mutated')
    return plan
