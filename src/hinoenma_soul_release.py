"""Soul Release: owned saved weapon views and the proven common42 cast.

The native projectile still computes familiarity damage, consumes the selected
weapon's familiarity, recalculates attributes, and consumes the prepared use.
No inventory, real Boss equipment, animation bank or event table is rewritten.
"""
from copy import deepcopy
import hashlib, json
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_special_item_actions import _once
import hinoenma_nine_talismans as nine
import hinoenma_wind_weakness_dragon as spells

ITEM = 64629
TEMPLATE = 0x5B260
PARENT_SHA256 = '17db69f17077579017935078108d0b6598de0f8f84a5f9dae32889af516d952b'
RESOLVER_OFFSET = 0x16400
GATE_OFFSET = 0x16C00
DAMAGE_OFFSET = 0x17C00
SAVE = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0x28
'''
RESTORE = '''add rsp, 0x28
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''
# With SAVE: saved R11/10/9/8/DX/CX/AX at 28/30/38/40/48/50/58.


def resolver_source():
    """RCX actor -> RAX saved gear, R8d native selector; volatile GPRs only."""
    return '''soul_owned_weapon:
mov r11, {data}
cmp rcx, qword ptr [r11+0x10]
jne soul_owned_weapon_no
test rcx, rcx
je soul_owned_weapon_no
mov rax, {player_slot}
cmp rcx, qword ptr [rax]
jne soul_owned_weapon_no
cmp dword ptr [rcx+4], 0x10000
jne soul_owned_weapon_no
cmp dword ptr [rcx+0xEF0], 0
jne soul_owned_weapon_no
mov eax, dword ptr [rcx]
cmp eax, 0x58E5E
je soul_owned_weapon_template
cmp eax, 0x51BE1
jne soul_owned_weapon_no
soul_owned_weapon_template:
cmp dword ptr [r11+4], eax
jne soul_owned_weapon_no
cmp dword ptr [r11+0x1C], 0
je soul_owned_weapon_no
mov rdx, qword ptr [rcx+0xE90]
test rdx, rdx
je soul_owned_weapon_no
cmp dword ptr [rdx], eax
jne soul_owned_weapon_no
cmp dword ptr [rdx+0xC], 1
jne soul_owned_weapon_no
mov rdx, qword ptr [rcx+0x240]
test rdx, rdx
je soul_owned_weapon_no
cmp qword ptr [rdx], rcx
jne soul_owned_weapon_no
cmp qword ptr [rdx+0x108], rcx
jne soul_owned_weapon_no
cmp qword ptr [rdx+0x20], 0
jle soul_owned_weapon_no
movzx r8d, byte ptr [rdx+0x9CC]
cmp r8d, 1
ja soul_owned_weapon_no
mov rax, {mission_temp_owner}
mov r10, qword ptr [rax]
cmp r10, 0x10000
jb soul_owned_weapon_no
mov rax, r10
shr rax, 47
jne soul_owned_weapon_no
test r10b, 7
jne soul_owned_weapon_no
mov r9d, r8d
xor r9d, 1
mov eax, dword ptr [r10+r9*4+0xB52B4]
cmp eax, 700
ja soul_owned_weapon_no
jb soul_owned_weapon_row
xor r9d, 1
mov eax, dword ptr [r10+r9*4+0xB52B4]
cmp eax, 700
jae soul_owned_weapon_no
xor r8d, 1
soul_owned_weapon_row:
imul rax, rax, 0xD0
lea rax, [r10+rax+0x210]
cmp dword ptr [rax], 0
jl soul_owned_weapon_no
cmp dword ptr [rax], 65535
ja soul_owned_weapon_no
cmp qword ptr [rax+0x30], 0
je soul_owned_weapon_no
ret
soul_owned_weapon_no:
xor eax, eax
ret
'''


def gate_source():
    # Original registers at 766455 are RCX gear offset, RAX component.
    return '''add rcx, rax
'''+SAVE+'''cmp dword ptr [r14], 64629
jne soul_gate_native
cmp word ptr [r14+4], 0xF02
jne soul_gate_native
cmp dword ptr [r14+0x104], 0x405
jne soul_gate_native
cmp dword ptr [r14+0x10C], 17
jne soul_gate_native
cmp qword ptr [r14+0x110], 0
jne soul_gate_native
cmp dword ptr [r14+0x118], 0
jne soul_gate_native
cmp dword ptr [r14+0x11C], 0x5B260
jne soul_gate_native
mov rcx, rbp
call {data} + 0x7400
test rax, rax
je soul_gate_native
mov qword ptr [rsp+0x50], rax
soul_gate_native:
'''+RESTORE+'''cmp dword ptr [rcx], -1
jmp {return}
'''


def damage_source():
    # R15 is the native projectile, RBX its resolved actor owner. This replaces
    # only the gear read; native 7E2932/A8E410 and 7C7EB0 remain unchanged.
    return SAVE+'''test r15, r15
je soul_damage_native
cmp dword ptr [r15], 0x5B260
jne soul_damage_native
cmp word ptr [r15+4], 4
jne soul_damage_native
cmp qword ptr [r15+0x200], rbx
jne soul_damage_native
cmp r15, qword ptr [rdi+0x28]
jne soul_damage_native
cmp r12, qword ptr [rdi]
jne soul_damage_native
mov rcx, rbx
call {data} + 0x7400
test rax, rax
je soul_damage_native
sub rax, qword ptr [rsp+0x58]
mov qword ptr [rsp+0x50], rax
mov qword ptr [rsp+0x40], r8
soul_damage_native:
'''+RESTORE+'''cmp dword ptr [rax+rcx], -1
je {soul_damage_skip}
jmp {return}
'''


SOUL_DEFINITION = '''soul_release_definition:
cmp dword ptr [rax], 64629
jne nine_talismans_definition_no
cmp word ptr [rax+4], 0xF02
jne nine_talismans_definition_no
cmp dword ptr [rax+0x104], 0x405
jne nine_talismans_definition_no
cmp dword ptr [rax+0x10C], 17
jne nine_talismans_definition_no
cmp dword ptr [rdi+0x54C], 17
jne nine_talismans_definition_no
cmp qword ptr [rax+0x110], 0
jne nine_talismans_definition_no
cmp dword ptr [rax+0x118], 0
jne nine_talismans_definition_no
cmp dword ptr [rax+0x11C], 0x5B260
jne nine_talismans_definition_no
cmp byte ptr [rdi+0x570], 0
jne nine_talismans_definition_no
mov r10d, 42
mov r11d, 111
ret
'''


def apply_soul_release(parent):
    if len(parent['hooks']) != 82 or parent.get('nine_talismans_candidate',{}).get('revision') != 1:
        raise ValueError('Verified nine-talismans parent required')
    fingerprint=lambda p:hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    original=fingerprint(parent)
    if original != PARENT_SHA256:raise ValueError('Exact nine-talismans parent required')
    p=deepcopy(parent);hs={h['name']:h for h in p['hooks']};ks=Ks(KS_ARCH_X86,KS_MODE_64)
    p['targets'].update(soul_damage_skip=0x7E2943,soul_familiarity_min=0x12358A8)
    def encode(s,h,off):
        values={k:0x140000000+r for k,r in p['targets'].items()}
        values.update(data=0x144000000+p['data_offset'],**{'return':0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(s.format(**values),0x144000000+off)[0])
    def append(name,offset,text):
        h=hs[name];n=len(encode(h['asm'],h,h['code_offset']))
        if h['code_offset']+n>offset:raise ValueError('Owned padding occupied')
        h['asm']+='\n'+'nop\n'*(offset-h['code_offset']-n)+text

    # Rebuild the tail in place so its helper address can grow without moving
    # any of the preceding menu-idle code or fixed spell helper entrypoints.
    guard=hs[nine.GUARD_CARRIER]
    before,oldtail=guard['asm'].split('nine_talismans_definition:',1)
    if ('nine_talismans_definition:'+oldtail).strip()!=(nine.definition_guard()+nine.gap_guard()).strip():
        raise ValueError('Exact definition/catchup helper required')
    definition=_once(nine.definition_guard(),'xor r11d, r11d\n',
        'xor r11d, r11d\ncmp dword ptr [rdi+0x548], 64629\nje soul_release_definition\n')+SOUL_DEFINITION
    gap=nine.gap_guard()
    gap=_once(gap,'nine_talismans_gap_42:\n', '''nine_talismans_gap_42:
cmp dword ptr [rcx+0x548], 64629
jne soul_release_gap_existing
cmp dword ptr [rcx+0x54C], 17
jne nine_talismans_gap_no
jmp soul_release_gap_motion
soul_release_gap_existing:
''')
    gap=_once(gap,'nine_talismans_gap_match_42:\ncmp dword ptr [rcx+0x54C], 9\njne nine_talismans_gap_no\n',
        'nine_talismans_gap_match_42:\ncmp dword ptr [rcx+0x54C], 9\njne nine_talismans_gap_no\nsoul_release_gap_motion:\n')
    gapoffset=nine.GUARD_OFFSET+len(encode(definition,guard,nine.GUARD_OFFSET))
    guard['asm']=before+definition+gap
    event=hs['HE_ProjectileElementInheritance']
    previous=parent['nine_talismans_candidate']['gap_guard_offset']
    event['asm']=_once(event['asm'],f'call {{data}} + {previous-0xF000}\n',f'call {{data}} + {gapoffset-0xF000}\n')

    carrier=hs[spells.CARRIER_NAME]
    prefix,rest=carrier['asm'].split('dung_fan_helper:')
    helper,rest=('dung_fan_helper:'+rest).split('arrow_sloth_lookup_entry:')
    lookup,tail=('arrow_sloth_lookup_entry:'+rest).split(spells.EXTRA_GUARD_ASM)
    def unpad(s):
        s=s.rstrip()+'\n'
        while s.endswith('nop\n'):s=s[:-4]
        return s.rstrip()+'\n'
    helper=unpad(helper);lookup=unpad(lookup)
    helper=_once(helper,'mov rcx, rdi\nmov edx, 172\ncall {native_ladder_set_action}\n', '''cmp dword ptr [rdi+0x548], 64629
jne soul_release_dispatch_existing
mov rcx, qword ptr [rsp+0xA8]
call {data} + 0x7400
test rax, rax
je dung_fan_restore
mov rcx, {soul_familiarity_min}
imul ecx, dword ptr [rcx], 100
cmp dword ptr [rax+0x14], ecx
jb dung_fan_restore
mov rcx, rdi
mov edx, 42
call {native_ladder_set_action}
jmp dung_fan_restore
soul_release_dispatch_existing:
mov rcx, rdi
mov edx, 172
call {native_ladder_set_action}
''')
    # Native common172 can still request its weapon-specific3025 during a
    # shortcut/continuation. Resolve that request to the same owned common42.
    lookup=_once(lookup,'cmp edx, 41\nje arrow_sloth_lookup_role\n',
        'cmp edx, 3025\nje arrow_sloth_lookup_role\ncmp edx, 41\nje arrow_sloth_lookup_role\n')
    anchor='mov ecx, dword ptr [rsp+0x198]\ncmp dword ptr [rax], ecx\n'
    lookup=_once(lookup,anchor,'''mov ecx, dword ptr [rsp+0x198]
cmp ecx, 3025
jne soul_release_existing_cast
cmp dword ptr [rdi+0x548], 64629
jne arrow_sloth_lookup_restore
mov ecx, 42
soul_release_existing_cast:
cmp dword ptr [rax], ecx
''')
    lookup=_once(lookup,'mov eax, dword ptr [rsp+0x94]\ncmp dword ptr [rsp+0x198], eax\njne arrow_sloth_lookup_restore\n', '''mov eax, dword ptr [rsp+0x94]
cmp dword ptr [rsp+0x198], 3025
jne soul_release_lookup_ordinary
cmp dword ptr [rdi+0x548], 64629
jne arrow_sloth_lookup_restore
cmp eax, 42
jne arrow_sloth_lookup_restore
jmp soul_release_lookup_request_ok
soul_release_lookup_ordinary:
cmp dword ptr [rsp+0x198], eax
jne arrow_sloth_lookup_restore
soul_release_lookup_request_ok:
''')
    hlen=len(encode(helper,carrier,spells.HELPER_OFFSET));llen=len(encode(lookup,carrier,spells.LOOKUP_OFFSET))
    if hlen>0x1800 or llen>0x1400:raise ValueError('Fixed item helper capacity exceeded')
    carrier['asm']=prefix+helper+'nop\n'*(0x1800-hlen)+lookup+'nop\n'*(0x1400-llen)+spells.EXTRA_GUARD_ASM+tail

    append('HE_PostDefeatRestore',RESOLVER_OFFSET,resolver_source())
    for name in ('HE_PostDefeatRestore','HE_PostDefeatHealEvent'):
        hs[name]['code_capacity']=0xC00
    specs=(('HE_SoulReleaseEligibility',0x766455,6,'4803c88339ff',GATE_OFFSET,gate_source()),
           ('HE_SoulReleaseFamiliarity',0x7E28A9,10,'833c08ff0f8490000000',DAMAGE_OFFSET,damage_source()))
    for name,rva,length,original_hex,off,source in specs:
        h=dict(name=name,rva=rva,length=length,original=original_hex,code_offset=off,code_capacity=0x400,
               asm=source,purpose='Exact local Hino Soul Release saved-equipment read view; native effect/consumption retained')
        p['hooks'].append(h)
    for h in p['hooks']:
        if len(encode(h['asm'],h,h['code_offset']))>h['code_capacity']:
            raise ValueError('Payload exceeds capacity: '+h['name'])
    p['soul_release_candidate']=dict(revision=1,parent_fingerprint=original,item_id=ITEM,projectile=TEMPLATE,
        native_action=3025,compatible_action=42,native_motion=1041,compatible_motion=111,
        resolver_offset=RESOLVER_OFFSET,gap_guard_offset=gapoffset,native_familiarity_minimum=300,
        native_effect_and_consumption=True,inventory_writes=False,real_equipment_writes=False,
        live_confirmation_pending=True)
    if fingerprint(parent)!=original:raise ValueError('Parent mutated')
    return p
