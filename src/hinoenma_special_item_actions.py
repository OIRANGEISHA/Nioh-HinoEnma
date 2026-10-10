"""Finite native item-action entry, preserving original effects and consumption.

Queries100/191/275/276/286/384 select common172's original item families.
Event references are sixteen <hHH> entries at parameters40; duration zero
is legal. Native707BF0 owns object spawning, release and item commit. This
module only calls706070(172), and never dispatches an event or edits an item.
The new RX tail ends13000; dataF000..10000 and counters13000..14000 stay intact.
"""
from copy import deepcopy
import struct

from hinoenma_signpost import HELPER_ASM as _SIGNPOST_HELPER
from hinoenma_signpost import RESOURCE_ASM as _SINGLE_MOTION_RESOURCES

HOOK_INDICES = (6, 7, 11, 48)
CODE_OFFSETS = (0x1800, 0x1C00, 0x2C00, 0x11800)
CODE_CAPACITIES = (0x400, 0x400, 0x400, 0x1800)
HELPER_OFFSET = 0x11A00
EFFECT_HELPER_OFFSET = 0x12B00
RESOURCE_OFFSET = 0x12E00
EXPECTED_SLOTS = (
    (6, 'HE_InputA', 0x721044, 5, 0x1800, 0x400),
    (7, 'HE_InputB', 0x721099, 5, 0x1C00, 0x400),
    (11, 'HE_HimorogiFragment', 0x75185D, 5, 0x2C00, 0x400),
    (48, 'HE_SameTemplateUnloadResources', 0x8B1A10, 5, 0x11800, 0x800),
)
# ID, kind, subtype, category, flags104, effects110/114/118, object11C,
# final common action, main motion, native query. Kind2 jutsu is excluded.
ITEM_SPECS = (
    (12084, 1, 0, 22, 0x12005, (0, 0, 0), 0xC2626, 610, 111, 286),
    (50129, 1, 0, 14, 0x10005, (0, 0, 0), 0x75441, 602, 126, 276),
    (7739, 1, 0, 6, 0x10005, (0, 0, 0), 0xBA4A7, 982, 120, 191),
    (7696, 3, 0, 13, 7, (30590, 0, 0), 0x4A517, 601, 370, 275),
    (22295, 1, 0, 4, 0x10005, (0, 0, 0), 0x52B13, 165, 103, 100),
    (49379, 1, 0, 27, 0x10005, (0, 0, 0), 0xD89A5, 1185, 123, 384),
)
SCHEDULE_HEX = {
    165: '12000f00ffff1f002800ffff140002000f00ffff0000ffff11272300ffffa0000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    982: '11000f00ffff1f002300ffff140002000f00ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    601: '12001e00ffff13006400ffff1e002c01ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    602: '12001100ffff13004b00ffffffff0000ffff112700001e005a001e001e00ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
    610: '11001100ffff70006400ffff14000000320011273200280014005a000e0011276800ffff13006400ffff1e006b00ffff7a00320019008d006200ffff8f00000031008f004c00ffff8e000000ffff91006400ffff94006400ffffffff0000ffff',
    1185: '87000a00ffff88003300ffff89003300ffff13003300ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
}
# Distinct referenced descriptor: index, opcode17, template18, bone1C,
# commit3F, channel2A, signedWORD52. Values came from current VM_READ records;
# they are static schedules, not evidence that any event already executed.
EVENT_GUARDS = {
    165: ((18,6,-1,22,255,255,-1),(31,5,-1,-1,255,255,-1),
          (20,-1,-1,-1,255,18,-1),(10001,-1,-1,-1,255,0,-1),(160,-1,-1,-1,255,255,-1)),
    982: ((17,6,-1,21,255,255,-1),(31,5,-1,-1,255,255,-1),(20,-1,-1,-1,255,18,-1)),
    601: ((18,6,-1,22,255,255,-1),(19,-1,-1,-1,0,255,-1),(30,0,-1,-1,255,255,-1)),
    602: ((18,6,-1,22,255,255,-1),(19,-1,-1,-1,0,255,-1),
          (10001,-1,-1,-1,255,0,-1),(90,-1,-1,-1,255,7,-1)),
    610: ((17,6,-1,21,255,255,-1),(112,7,-1,0,255,255,1505),
          (20,-1,-1,-1,255,18,-1),(10001,-1,-1,-1,255,0,-1),
          (19,-1,-1,-1,0,255,-1),(30,0,-1,-1,255,255,-1),
          (122,-1,-1,-1,255,255,-1),(141,9,-1,-1,255,255,-1),
          (143,-1,-1,-1,255,255,-1),(142,-1,-1,-1,255,255,-1),
          (145,-1,-1,-1,255,255,-1),(148,-1,-1,-1,255,255,-1)),
    1185: ((135,14,408470,22,255,255,1523),(136,18,-1,-1,255,255,-1),
           (137,32,408470,0,255,255,1522),(19,-1,-1,-1,0,255,-1)),
}
NATIVE_SIGNATURE_SPANS = (
    ('special_item_setter',0x706070,0x4B),
    ('special_item_lookup_tail',0x73FA45,0xCC),
    ('special_item_motion_lookup',0x917500,0xBC),
    ('special_item_definition_lookup',0x7324E0,0x81),
    ('special_item_query4',0x738026,0x2F),
    ('special_item_query6',0x738084,0x2F),
    ('special_item_query13',0x7381CD,0x2F),
    ('special_item_query14',0x7381FC,0x2F),
    ('special_item_query22',0x738374,0x2F),
    ('special_item_query27',0x73845F,0x2F),
    ('special_item_query100_table',0x73AC90,4),
    ('special_item_query191_table',0x73ADFC,4),
    ('special_item_query275_table',0x73AF4C,4),
    ('special_item_query276_table',0x73AF50,4),
    ('special_item_query286_table',0x73AF78,4),
    ('special_item_query384_table',0x73B100,4),
    ('special_item_object6',0x708C3B,0x7B),
    ('special_item_event_commit',0x70A522,0x88),
    ('special_item_global_event_range',0x6DFED0,0x45),
)


def _once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Frozen Signpost shape differs: '+old.splitlines()[0])
    return text.replace(old,new,1)


def _definition_scope():
    text = '''mov rax, qword ptr [rdi+0x548]
mov qword ptr [rsp+0xC0], rax
mov rcx, {item_assets}
mov rcx, qword ptr [rcx]
test rcx, rcx
je special_item_restore
mov rcx, qword ptr [rcx+0x20]
test rcx, rcx
je special_item_restore
mov rcx, qword ptr [rcx+0x428]
test rcx, rcx
je special_item_restore
mov edx, dword ptr [rdi+0x548]
call {item_lookup}
test rax, rax
je special_item_restore
mov qword ptr [rsp+0xC8], rax
'''
    for ident,*_ in ITEM_SPECS:
        text += f'cmp dword ptr [rdi+0x548], {ident}\nje special_item_definition_{ident}\n'
    text += 'jmp special_item_restore\n'
    for ident,kind,sub,cat,flags,effects,spawn,action,motion,_ in ITEM_SPECS:
        text += f'special_item_definition_{ident}:\n'
        fields=((0,ident),(4,kind|(sub<<8)),(0x104,flags),(0x10C,cat),
                *((0x110+i*4,v) for i,v in enumerate(effects)),(0x11C,spawn))
        for off,value in fields:
            width='word' if off==4 else 'dword'
            text += f'cmp {width} ptr [rax+{off}], {value}\njne special_item_restore\n'
        text += (f'cmp dword ptr [rdi+0x54C], {cat}\njne special_item_restore\n'
                 f'mov dword ptr [rsp+0x94], {action}\nmov dword ptr [rsp+0x98], {motion}\n'
                 'jmp special_item_definition_done\n')
    return text+'special_item_definition_done:\n'


def _schedules():
    # Expected bytes live inside unreachable, fixed-width MOVABS immediates.
    # The complete payload remains instructions for the EXE relocation parser.
    text='special_item_schedule:\nsub rsp, 0x28\nmov qword ptr [rsp], rax\nmov qword ptr [rsp+8], r8\n'
    for action in SCHEDULE_HEX:
        text += f'cmp edx, {action}\nje special_item_schedule_{action}\n'
    text += 'jmp special_item_schedule_false\n'
    for action in SCHEDULE_HEX:
        text += f'special_item_schedule_{action}:\n'
        text += (f'lea r11, [rip+special_item_schedule_data_{action}]\n'
                 f'mov dword ptr [rsp+0x18], {len(EVENT_GUARDS[action])}\njmp special_item_schedule_compare\n')
    text+='''special_item_schedule_compare:
mov rax, qword ptr [rsp]
add rax, 0x40
mov ecx, 12
special_item_schedule_qword:
mov r10, qword ptr [r11+2]
cmp qword ptr [rax], r10
jne special_item_schedule_false
add r11, 10
add rax, 8
dec ecx
jne special_item_schedule_qword
mov r8, qword ptr [rsp+8]
mov r9, qword ptr [r8+0x80]
test r9, r9
je special_item_schedule_false
movzx ecx, word ptr [r8+0x88]
cmp ecx, 0x1000
ja special_item_schedule_false
special_item_schedule_descriptor:
movzx edx, word ptr [r11+2]
cmp edx, 10000
jae special_item_schedule_global
cmp ecx, edx
jbe special_item_schedule_false
mov r10, qword ptr [r9+rdx*8]
jmp special_item_schedule_fields
special_item_schedule_global:
mov r10, {item_assets}
sub r10, 0x1E0
mov r10, qword ptr [r10]
test r10, r10
je special_item_schedule_false
mov r10, qword ptr [r10]
test r10, r10
je special_item_schedule_false
mov rax, qword ptr [r10+0x470]
mov r10, qword ptr [r10+0x468]
test r10, r10
je special_item_schedule_false
cmp rax, r10
jbe special_item_schedule_false
sub rax, r10
test al, 0x7F
jne special_item_schedule_false
cmp rax, 0x80000
ja special_item_schedule_false
sub edx, 10000
shl rdx, 7
lea r8, [rdx+0x80]
cmp rax, r8
jb special_item_schedule_false
add r10, rdx
special_item_schedule_fields:
test r10, r10
je special_item_schedule_false
mov al, byte ptr [r11+4]
cmp byte ptr [r10+0x17], al
jne special_item_schedule_false
mov eax, dword ptr [r11+6]
cmp dword ptr [r10+0x18], eax
jne special_item_schedule_false
mov ax, word ptr [r11+12]
cmp word ptr [r10+0x1C], ax
jne special_item_schedule_false
mov al, byte ptr [r11+5]
cmp byte ptr [r10+0x3F], al
jne special_item_schedule_false
mov al, byte ptr [r11+14]
cmp byte ptr [r10+0x2A], al
jne special_item_schedule_false
mov ax, word ptr [r11+15]
cmp word ptr [r10+0x52], ax
jne special_item_schedule_false
add r11, 20
dec dword ptr [rsp+0x18]
jne special_item_schedule_descriptor
mov eax, 1
add rsp, 0x28
ret
special_item_schedule_false:
xor eax, eax
add rsp, 0x28
ret
'''
    for action,raw in SCHEDULE_HEX.items():
        data=bytes.fromhex(raw)
        if len(data)!=0x60:
            raise ValueError('Expected exactly sixteen six-byte event references')
        text+=f'special_item_schedule_data_{action}:\n'
        for off in range(0,0x60,8):
            text+=f'movabs rax, {struct.unpack_from("<Q",data,off)[0]}\n'
        for index,opcode,template,bone,commit,channel,word52 in EVENT_GUARDS[action]:
            first=struct.pack('<HBBi',index,opcode&255,commit,template)
            second=struct.pack('<hBh3x',bone,channel,word52)
            for value in (first,second):
                text+=f'movabs rax, {struct.unpack("<Q",value)[0]}\n'
    return text


# Win64 entry RSP%16==8; eight saved values plus E8 locals preserve flags,
# volatile integer/SSE0..5 state and MXCSR. Native callbacks remain aligned.
HELPER_ASM = (_SIGNPOST_HELPER.replace('signpost_','special_item_').replace('0xA8','0xE8')
              .replace('{special_item_action_lookup}','{signpost_action_lookup}'))
HELPER_ASM = _once(HELPER_ASM,'mov r11, {data}\n',
    'mov r11, {data}\nmov eax, dword ptr [r11+0x1C]\ntest eax, eax\n'
    'je special_item_restore\nmov dword ptr [rsp+0xA0], eax\n')
HELPER_ASM = _once(HELPER_ASM,'special_item_role:\n',
    'special_item_role:\nmov qword ptr [rsp+0xA8], rdx\n'
    'mov eax, dword ptr [rdx]\nmov dword ptr [rsp+0x9C], eax\n')
HELPER_ASM = _once(HELPER_ASM,'cmp dword ptr [rax], ecx\njne special_item_fail_a\n',
    'cmp dword ptr [rax], ecx\njne special_item_fail_a\n'
    'cmp dword ptr [r11+4], ecx\njne special_item_fail_a\n'
    'mov qword ptr [rsp+0xB0], rax\n')
HELPER_ASM = _once(HELPER_ASM,'cmp qword ptr [rax+0x20], 0\njle special_item_fail_a\n',
    'cmp qword ptr [rax+0x20], 0\njle special_item_fail_a\nmov qword ptr [rsp+0xB8], rax\n')
HELPER_ASM = _once(HELPER_ASM,
    'cmp dword ptr [rdi+0x548], 34765\njne special_item_fail_b\n'
    'cmp dword ptr [rdi+0x54C], 21\njne special_item_fail_b\n','')
HELPER_ASM = _once(HELPER_ASM,'mov rax, qword ptr [rdi+0x58]\n',
    'mov rax, qword ptr [rdi+0x58]\nmov qword ptr [rsp+0xD8], rax\n')
HELPER_ASM = _once(HELPER_ASM,'special_item_records:\n',
    'special_item_records:\n'+_definition_scope())
HELPER_ASM = _once(HELPER_ASM,
    'mov edx, 172\nxor r8d, r8d\ncall {signpost_action_lookup}\ntest rax, rax\nje special_item_restore\n',
    'mov edx, 172\nxor r8d, r8d\ncall {signpost_action_lookup}\ntest rax, rax\nje special_item_restore\n'
    'cmp dword ptr [rax], 172\njne special_item_restore\n')
HELPER_ASM = _once(HELPER_ASM,'mov edx, 609\n','mov edx, dword ptr [rsp+0x94]\n')
_final = HELPER_ASM.index('mov edx, dword ptr [rsp+0x94]\n')
_tail = HELPER_ASM.index('mov rax, {data}\n',_final)
HELPER_ASM = HELPER_ASM[:_final]+HELPER_ASM[_final:_tail].replace(
    'mov rcx, qword ptr [rsp+0x80]\n',
    'mov ecx, dword ptr [rsp+0x94]\ncmp dword ptr [rax], ecx\njne special_item_restore\n'
    'mov rcx, qword ptr [rsp+0x80]\n').replace(
    'cmp dword ptr [rax+0x20], 123\njne special_item_restore\n',
    'mov ecx, dword ptr [rsp+0x98]\ncmp dword ptr [rax+0x20], ecx\njne special_item_restore\n'
    'cmp dword ptr [rax+0x34], -1\njne special_item_restore\n'
    'mov qword ptr [rsp+0xD0], rax\nmov edx, dword ptr [rsp+0x94]\n'
    'mov r8, qword ptr [rsp+0x80]\ncall special_item_schedule\ntest al, al\nje special_item_restore\n')+HELPER_ASM[_tail:]
HELPER_ASM = _once(HELPER_ASM,'call {data} - 0xDB00\n',
    'mov qword ptr [rsp+0xE0], rcx\nmov edx, dword ptr [rsp+0x98]\ncall {data} + 0x3E00\n')
_POST = '''mov r11, {data}
mov eax, dword ptr [rsp+0xA0]
cmp dword ptr [r11+0x1C], eax
jne special_item_restore
mov rdx, qword ptr [rsp+0xA8]
cmp qword ptr [r11+0x10], rdx
jne special_item_restore
mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne special_item_restore
cmp dword ptr [rdx+4], 0x10000
jne special_item_restore
mov eax, dword ptr [rsp+0x9C]
cmp dword ptr [rdx], eax
jne special_item_restore
cmp dword ptr [rdx+0xEF0], 0
jne special_item_restore
mov rax, qword ptr [rsp+0xB0]
cmp qword ptr [rdx+0xE90], rax
jne special_item_restore
cmp dword ptr [rax+0x0C], 1
jne special_item_restore
mov ecx, dword ptr [rdx]
cmp dword ptr [rax], ecx
jne special_item_restore
cmp dword ptr [r11+4], ecx
jne special_item_restore
mov rax, qword ptr [rsp+0xB8]
cmp qword ptr [rdx+0x240], rax
jne special_item_restore
cmp qword ptr [rax], rdx
jne special_item_restore
cmp qword ptr [rax+0x108], rdx
jne special_item_restore
cmp qword ptr [rax+0x20], 0
jle special_item_restore
mov rax, qword ptr [rdx+0x230]
test rax, rax
je special_item_restore
cmp qword ptr [rax], rdx
jne special_item_restore
cmp qword ptr [rax+8], rdi
jne special_item_restore
cmp qword ptr [rdi+0x50], rdx
jne special_item_restore
mov rax, qword ptr [rsp+0xC0]
cmp qword ptr [rdi+0x548], rax
jne special_item_restore
cmp dword ptr [rdi+0x550], 1
jne special_item_restore
cmp dword ptr [rdi+0x554], 0x100
jne special_item_restore
cmp qword ptr [rdi+0x558], 0
jne special_item_restore
cmp qword ptr [rdi+0x728], 0
jne special_item_restore
mov rax, qword ptr [rdi+0x720]
test rax, rax
je special_item_restore
cmp qword ptr [rax], rax
jne special_item_restore
cmp qword ptr [rax+8], rax
jne special_item_restore
mov rax, qword ptr [rsp+0xD8]
cmp qword ptr [rdi+0x58], rax
jne special_item_restore
cmp dword ptr [rax], 0
jne special_item_restore
mov rcx, qword ptr [rdi+0x78]
test rcx, rcx
je special_item_restore
cmp qword ptr [rax+0x38], rcx
jne special_item_restore
mov rax, qword ptr [rax+0x20]
test rax, rax
je special_item_restore
test byte ptr [rax], 1
je special_item_restore
test byte ptr [rax+1], 8
jne special_item_restore
mov rax, qword ptr [rsp+0x80]
cmp qword ptr [rdi+0x80], rax
jne special_item_restore
mov rcx, qword ptr [rsp+0xE0]
cmp qword ptr [rdx+0x38], rcx
jne special_item_restore
cmp dword ptr [rcx+0x50], 1
ja special_item_restore
'''
HELPER_ASM = _once(HELPER_ASM,'mov rcx, rdi\nmov edx, 172\n',
    _POST+'mov rcx, rdi\nmov edx, 172\n')+_schedules()

RESOURCE_ASM = _SINGLE_MOTION_RESOURCES.replace('signpost_','special_item_')
RESOURCE_ASM = _once(RESOURCE_ASM,'mov qword ptr [rsp+0x20], rcx\n',
    'mov qword ptr [rsp+0x20], rcx\nmov dword ptr [rsp+0x30], edx\n')
RESOURCE_ASM = _once(RESOURCE_ASM,'mov edx, 123\n','mov edx, dword ptr [rsp+0x30]\n')


def _input_scope(suffix):
    text='push rcx\nmov ecx, 123\ncmp dword ptr [rdx], 609\nje special_item_input_found_'+suffix+'\n'
    for action,motion in dict((x[7],x[8]) for x in ITEM_SPECS).items():
        text+=f'mov ecx, {motion}\ncmp dword ptr [rdx], {action}\nje special_item_input_found_{suffix}\n'
    text+=f'pop rcx\njmp signpost_input_continue_{suffix}\nspecial_item_input_found_{suffix}:\n'
    text+='mov rdx, qword ptr [rdx+0x38]\ntest rdx, rdx\n'
    text+=f'je special_item_input_continue_{suffix}\ncmp qword ptr [rbx+0x80], rdx\njne special_item_input_continue_{suffix}\n'
    text+='mov rdx, qword ptr [rbx+0x58]\nmov rdx, qword ptr [rdx+0x20]\ntest rdx, rdx\n'
    text+=f'je special_item_input_continue_{suffix}\ncmp dword ptr [rdx+0x20], ecx\njne special_item_input_continue_{suffix}\n'
    text+=f'pop rcx\npop rdx\njmp input_{suffix}_done\nspecial_item_input_continue_{suffix}:\npop rcx\n'
    return text


def apply_special_item_actions(previous_profile, *, effect_helper='xor eax, eax\nret\n'):
    """Pure0.51->0.52: four payloads, no new sites or allocation."""
    if previous_profile.get('tool_version')!='0.51' or len(previous_profile['hooks'])!=49:
        raise ValueError('Special item actions require the complete frozen0.51 profile')
    if (previous_profile.get('allocation_size'),previous_profile.get('data_offset'))!=(0x14000,0xF000):
        raise ValueError('Unexpected existing allocation/data/counter layout')
    for index,*fields in EXPECTED_SLOTS:
        h=previous_profile['hooks'][index]
        if (h['name'],h['rva'],h['length'],h['code_offset'],h.get('code_capacity',0x400))!=tuple(fields):
            raise ValueError('Unexpected special item carrier/input layout')
    plan=deepcopy(previous_profile)
    fragment,carrier=plan['hooks'][11],plan['hooks'][48]
    fragment['asm']=_once(fragment['asm'],'call {data} - 0xC300\n',
                         'call {data} - 0xC300\ncall {data} + 0x2A00\n')
    for index,suffix in ((6,'a'),(7,'b')):
        h=plan['hooks'][index]
        first=f'cmp dword ptr [rdx], 609\njne signpost_input_continue_{suffix}\n'
        end=f'signpost_input_continue_{suffix}:\n'
        start=h['asm'].index(first)
        stop=h['asm'].index(end,start)
        h['asm']=h['asm'][:start]+_input_scope(suffix)+h['asm'][stop:]
    # Assemble only owned code to derive fixed-entry padding; never read a
    # process or write a profile. The frozen unload prefix must remain exact.
    from source_assembler import Ks,KS_ARCH_X86,KS_MODE_64
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    values={k:0x140000000+v for k,v in plan['targets'].items()}
    values.update(data=0x144000000+plan['data_offset'])
    values['return']=0x140000000+carrier['rva']+carrier['length']
    old,_=ks.asm(carrier['asm'].format(**values),addr=0x144000000+carrier['code_offset'])
    helper,_=ks.asm(HELPER_ASM.format(**values),addr=0x144000000+HELPER_OFFSET)
    effects,_=ks.asm(effect_helper.format(**values),addr=0x144000000+EFFECT_HELPER_OFFSET)
    resources,_=ks.asm(RESOURCE_ASM.format(**values),addr=0x144000000+RESOURCE_OFFSET)
    if (len(old)>HELPER_OFFSET-carrier['code_offset'] or len(helper)>EFFECT_HELPER_OFFSET-HELPER_OFFSET
            or len(effects)>RESOURCE_OFFSET-EFFECT_HELPER_OFFSET or len(resources)>0x200):
        raise ValueError('Special item helper exceeds its counter-safe fixed region')
    carrier['asm']+='\n'+'nop\n'*(HELPER_OFFSET-carrier['code_offset']-len(old))+HELPER_ASM
    carrier['asm']+='\n'+'nop\n'*(EFFECT_HELPER_OFFSET-HELPER_OFFSET-len(helper))+effect_helper
    carrier['asm']+='\n'+'nop\n'*(RESOURCE_OFFSET-EFFECT_HELPER_OFFSET-len(effects))+RESOURCE_ASM
    carrier['code_capacity']=0x1800
    carrier['purpose']+='; fixed tail carries exact six-item native common172 entry'
    spans=sorted((h['code_offset'],h['code_offset']+h.get('code_capacity',0x400)) for h in plan['hooks'])
    if any(a[1]>b[0] for a,b in zip(spans,spans[1:])) or spans[-1][1]!=0x13000:
        raise ValueError('Code slots overlap or reach the private counter page')
    plan.update(tool_version='0.52',stage='finite_native_special_item_actions',special_item_actions_revision=1,
        special_item_actions_changed_hook_indices=list(HOOK_INDICES),
        special_item_actions_item_ids=[x[0] for x in ITEM_SPECS],
        special_item_actions_common_actions=[172]+sorted(SCHEDULE_HEX),
        special_item_actions_helper_offsets=dict(entry=HELPER_OFFSET,effects=EFFECT_HELPER_OFFSET,resources=RESOURCE_OFFSET),
        special_item_actions_required_motion_slots=[2,6],
        special_item_actions_new_rx_page=[0x12000,0x13000],
        special_item_actions_counter_page_preserved=[0x13000,0x14000],
        special_item_actions_direct_item_effect_quantity_npc_save_writes=False,
        special_item_actions_resource_failure_fallback='previous_native_item_animation_gate',
        special_item_actions_gameplay_confirmation_pending=True)
    return plan
