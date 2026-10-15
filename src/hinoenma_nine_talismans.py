"""Exact observed Onmyo requests through native common42, 611 and 1165.

Item commit, projectile generation, healing and debuffs remain native. Soul
Release is intentionally separate: its equipment gate and weapon-specific
action have not yet been verified for the Boss player.
"""
from copy import deepcopy
import hashlib, json, struct
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
import hinoenma_wind_weakness_dragon as spells
import hinoenma_spell_event_catchup as gap
import hinoenma_item_hurt_lookup as hurt
from hinoenma_special_item_actions import _once, _schedules

PARENT_SHA256='767acedbc7bfcdac26d5ccb618e23e1978a05c689483f2483e3399a8eb586b37'
GUARD_CARRIER='HE_MapNativeIdlePrivate'
GUARD_OFFSET=0x26400
SCHEDULE_CARRIER='HE_PostDefeatDamage'
SCHEDULE_OFFSET=0x15400
ITEM_SPECS=(
    (52306,2,15,9,5,(0,0,0),0xE4DDB,42,111,194),
    (40718,2,15,23,5,(0,0,0),0xD9E7,611,110,287),
    (19803,2,15,9,5,(0,0,0),0x4BF8D,42,111,194),
    (31267,2,15,25,5,(0,0,0),0xB569D,1165,111,359),
    (3735,2,15,25,5,(0,0,0),0x90B5F,1165,111,359),
    (52147,2,15,25,5,(0,0,0),0xD84C8,1165,111,359),
    (3944,2,15,25,5,(0,0,0),0xBE1B6,1165,111,359),
    (24932,2,15,25,5,(0,0,0),0xDFE76,1165,111,359),
    (35389,2,15,23,5,(0,0,0),0xC0FE6,611,110,287),
)
AREA_SCHEDULE='11001800ffff1f006400ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff7a00320019008f00000031008f004c00ffff8e000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff'
SCHEDULE_HEX={**spells.SCHEDULE_HEX,611:AREA_SCHEDULE}
EVENT_GUARDS={**spells.EVENT_GUARDS,611:(
    (17,6,-1,21,255,255,-1),(31,5,-1,-1,255,255,-1),
    (122,-1,-1,-1,255,255,-1),(142,-1,-1,-1,255,255,-1),
    (143,-1,-1,-1,255,255,-1))}

def definition_guard():
    # RAX=definition, RDI=controller; preserve both. R10/R11 output action/motion.
    s='nine_talismans_definition:\nxor r10d, r10d\nxor r11d, r11d\n'
    for ident,*_ in ITEM_SPECS:
        s+=f'cmp dword ptr [rdi+0x548], {ident}\nje nine_talismans_definition_{ident}\n'
    s+='ret\n'
    for ident,kind,sub,cat,flags,effects,spawn,action,motion,_ in ITEM_SPECS:
        s+=f'''nine_talismans_definition_{ident}:
cmp dword ptr [rax], {ident}
jne nine_talismans_definition_no
cmp dword ptr [rax+0x11C], {spawn}
jne nine_talismans_definition_no
mov ecx, {cat}
mov r10d, {action}
mov r11d, {motion}
jmp nine_talismans_definition_common
'''
    s+='''nine_talismans_definition_common:
cmp word ptr [rax+4], 0xF02
jne nine_talismans_definition_no
cmp dword ptr [rax+0x104], 5
jne nine_talismans_definition_no
cmp dword ptr [rax+0x10C], ecx
jne nine_talismans_definition_no
cmp dword ptr [rdi+0x54C], ecx
jne nine_talismans_definition_no
cmp qword ptr [rax+0x110], 0
jne nine_talismans_definition_no
cmp dword ptr [rax+0x118], 0
jne nine_talismans_definition_no
cmp byte ptr [rdi+0x570], 0
jne nine_talismans_definition_no
ret
nine_talismans_definition_no:
xor r10d, r10d
mov r11d, -1
ret
'''
    return s

def gap_guard():
    # Outer event hook saves RAX/R10/R11 and flags; RCX/RDX/R8 remain untouched.
    s='nine_talismans_gap:\n'
    for action in (42,611,1165):
        s+=f'cmp dword ptr [rdx], {action}\nje nine_talismans_gap_{action}\n'
    s+='jmp nine_talismans_gap_no\n'
    for action,cat,motion,alternate in ((42,9,111,-1),(611,23,110,-1),(1165,25,111,90111)):
        s+=f'nine_talismans_gap_{action}:\n'
        ids=[r[0] for r in ITEM_SPECS if r[7]==action]
        if action==42:ids+=[44930,22722]
        if action==1165:ids+=[26116]
        for ident in ids:s+=f'cmp dword ptr [rcx+0x548], {ident}\nje nine_talismans_gap_match_{action}\n'
        s+=f'''jmp nine_talismans_gap_no
nine_talismans_gap_match_{action}:
cmp dword ptr [rcx+0x54C], {cat}
jne nine_talismans_gap_no
mov r10, qword ptr [rdx+0x20]
test r10, r10
je nine_talismans_gap_no
cmp dword ptr [r10+0x20], {motion}
jne nine_talismans_gap_no
cmp dword ptr [r10+0x34], {alternate}
jne nine_talismans_gap_no
'''
        s+=gap.checks(SCHEDULE_HEX[action],'r10',0x40).replace('spell_gap_reject','nine_talismans_gap_no')
        s+='mov eax, 1\nret\n'
    return s+'nine_talismans_gap_no:\nxor eax, eax\nret\n'

def apply_nine_talismans(parent):
    fingerprint=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if fingerprint(parent)!=PARENT_SHA256:raise ValueError('Exact tested Dispersal revision2 parent required')
    plan=deepcopy(parent);hooks={h['name']:h for h in plan['hooks']};ks=Ks(KS_ARCH_X86,KS_MODE_64)
    def encode(text,h,offset):
        v={k:0x140000000+r for k,r in plan['targets'].items()}
        v.update(data=0x144000000+plan['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(text.format(**v),0x144000000+offset)[0])
    def append(name,offset,text):
        h=hooks[name];n=len(encode(h['asm'],h,h['code_offset']))
        if h['code_offset']+n>offset:raise ValueError('Owned padding occupied: '+name)
        h['asm']+='\n'+'nop\n'*(offset-h['code_offset']-n)+text
    definition=definition_guard();guard=hooks[GUARD_CARRIER]
    gap_offset=GUARD_OFFSET+len(encode(definition,guard,GUARD_OFFSET))
    append(GUARD_CARRIER,GUARD_OFFSET,definition+gap_guard())
    schedule=_schedules(SCHEDULE_HEX,EVENT_GUARDS).replace('special_item_','dung_fan_')
    append(SCHEDULE_CARRIER,SCHEDULE_OFFSET,schedule)

    carrier=hooks[spells.CARRIER_NAME]
    prefix,rest=carrier['asm'].split('dung_fan_helper:')
    helper,rest=('dung_fan_helper:'+rest).split('arrow_sloth_lookup_entry:')
    lookup,tail=('arrow_sloth_lookup_entry:'+rest).split(spells.EXTRA_GUARD_ASM)
    def unpad(text):
        text=text.rstrip()+'\n'
        while text.endswith('nop\n'):text=text[:-4]
        return text.rstrip()+'\n'
    helper=unpad(helper);lookup=unpad(lookup)
    # Move the unchanged schedule validator plus new611 into owned spare code.
    helper=helper.split('dung_fan_schedule:')[0]+f'dung_fan_schedule:\njmp {{data}} + {SCHEDULE_OFFSET-0xF000}\n'
    def extend(text,prefix,last):
        anchor=f'je {prefix}_definition_{last}\n'
        return _once(text,anchor,anchor+f'''call {{data}} + {GUARD_OFFSET-0xF000}
cmp r11d, -1
je {prefix}_restore
test r10d, r10d
je {prefix}_nine_existing
mov dword ptr [rsp+0x94], r10d
mov dword ptr [rsp+0x98], r11d
jmp {prefix}_definition_done
{prefix}_nine_existing:
''')
    helper=extend(helper,'dung_fan',44607)
    lookup=extend(lookup,'arrow_sloth_lookup',44930)
    helper=_once(helper,'je wind_weakness_dragon_post_44607\n',f'''je wind_weakness_dragon_post_44607
mov rax, qword ptr [rsp+0xC8]
call {{data}} + {GUARD_OFFSET-0xF000}
cmp r11d, -1
je dung_fan_restore
test r10d, r10d
je nine_talismans_post_existing
cmp dword ptr [rsp+0x94], r10d
jne dung_fan_restore
cmp dword ptr [rsp+0x98], r11d
jne dung_fan_restore
jmp wind_weakness_dragon_post_resources
nine_talismans_post_existing:
''')
    lookup=_once(lookup,'je arrow_sloth_lookup_post_definition_44930\n',f'''je arrow_sloth_lookup_post_definition_44930
call {{data}} + {GUARD_OFFSET-0xF000}
cmp r11d, -1
je arrow_sloth_lookup_restore
test r10d, r10d
je nine_talismans_lookup_post_existing
cmp dword ptr [rsp+0x94], r10d
jne arrow_sloth_lookup_restore
cmp dword ptr [rsp+0x98], r11d
jne arrow_sloth_lookup_restore
jmp arrow_sloth_lookup_success
nine_talismans_lookup_post_existing:
''')
    hs=len(encode(helper,carrier,spells.HELPER_OFFSET));ls=len(encode(lookup,carrier,spells.LOOKUP_OFFSET))
    if hs>0x1800 or ls>0x1400:raise ValueError('Fixed helper capacity exhausted')
    carrier['asm']=prefix+helper+'\n'+'nop\n'*(0x1800-hs)+lookup+'\n'+'nop\n'*(0x1400-ls)+spells.EXTRA_GUARD_ASM+tail

    event=hooks[gap.CARRIER]
    start=event['asm'].index('cmp dword ptr [rdx], 1165\n')
    end=event['asm'].index('mov r10, qword ptr [rcx+0x80]\ncmp word ptr [r10+0x88], 32\n',start)
    event['asm']=event['asm'][:start]+f'call {{data}} + {gap_offset-0xF000}\ntest al, al\nje spell_gap_reject\n'+event['asm'][end:]
    event['asm']=_once(event['asm'],'movd eax, xmm2\ncmp eax, 0x41880000\n', '''movd eax, xmm2
cmp dword ptr [rdx], 611
jne nine_talismans_gap_ordinary_window
cmp eax, 0x41C00000
jbe spell_gap_restore
cmp eax, 0x42C80000
jae spell_gap_restore
jmp nine_talismans_gap_window_ok
nine_talismans_gap_ordinary_window:
cmp eax, 0x41880000
''')
    event['asm']=_once(event['asm'],'cmp eax, 0x42D00000\njae spell_gap_restore\nmov byte ptr [rsp], 1\n',
        'cmp eax, 0x42D00000\njae spell_gap_restore\nnine_talismans_gap_window_ok:\nmov byte ptr [rsp], 1\n')

    for name,suffix in (('HE_InputA','a'),('HE_InputB','b')):
        h=hooks[name];anchor=f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        h['asm']=_once(h['asm'],anchor,f'mov ecx, 110\ncmp dword ptr [rdx], 611\nje special_item_input_found_{suffix}\n'+anchor)
    table=hooks[hurt.DATA_CARRIER];old='.byte '+','.join(map(str,hurt.TABLE_BYTES))+'\n'
    new=hurt.TABLE_BYTES+struct.pack('<2i96s',611,110,bytes.fromhex(AREA_SCHEDULE))
    table['asm']=_once(table['asm'],old,'.byte '+','.join(map(str,new))+'\n')
    code=hooks[hurt.CODE_CARRIER]
    code['asm']=_once(code['asm'],f'mov ecx, {len(hurt.CAST_ROWS)}\nitem_hurt_cast_scan:\n',f'mov ecx, {len(hurt.CAST_ROWS)+1}\nitem_hurt_cast_scan:\n')

    changed=[]
    for h,old in zip(plan['hooks'],parent['hooks']):
        if h['asm']==old['asm']:continue
        changed.append(h['name']);raw=encode(h['asm'],h,h['code_offset'])
        if len(raw)>h['code_capacity']:raise ValueError('Payload capacity exceeded: '+h['name'])
        before=encode(old['asm'],old,old['code_offset'])
        if h['name'] in (SCHEDULE_CARRIER,GUARD_CARRIER) and not raw.startswith(before):raise ValueError('Original carrier prefix changed')
    plan['nine_talismans_candidate']=dict(revision=1,item_ids=[r[0] for r in ITEM_SPECS],
        changed_hooks=changed,guard_offset=GUARD_OFFSET,gap_guard_offset=gap_offset,
        schedule_offset=SCHEDULE_OFFSET,native_effects_and_stock_unchanged=True,
        native_injury_and_input_protection=True,live_confirmation_pending=True)
    if fingerprint(parent)!=PARENT_SHA256:raise ValueError('Parent mutated')
    return plan
