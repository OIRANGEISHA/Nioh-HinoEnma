"""Uninstalled, scene-bound Living Weapon action/motion/event read views.

This module does not open a process.  It only transforms a copied public plan.
The installer must populate all 512 binding bytes from one checked live scene.
The original 82 native entries, old resource routes and cleanup prefix remain.
"""
from copy import deepcopy
import struct

from hinoenma_orochi_trial import SAVE, RESTORE

MAGIC = 0x534C5748
DATA_OFFSET, DATA_SIZE = 0x44200, 0x200
CORE_OFFSET = 0xF000
READY_OFFSET, COMMON_OFFSET = 0x51C00, 0x52D40
PREFILTER_OFFSET = 0x51B04
GATEWAY_OFFSET = 0x52F00
CODE_END = 0x53000
FIELDS = {
    'magic':0x00, 'epoch':0x04, 'actor':0x08, 'controller':0x10,
    'phase':0x18, 'package':0x20, 'bank_wrapper':0x28, 'bank':0x30,
    'main_motion':0x38, 'aux_motion':0x40, 'main_event_wrapper':0x48,
    'aux_event_wrapper':0x50, 'idle_record':0x58, 'dispatch_record':0x60,
    'long_record':0x68, 'short_record':0x70, 'long_id':0x78, 'short_id':0x7C,
    'motion_controller':0x80, 'stat_component':0x88, 'identity':0x90,
    'main_event_owner':0x98, 'aux_event_owner':0xA0,
    'main_motion_map':0xA8, 'aux_motion_map':0xB0,
    'main_event_header':0xB8, 'aux_event_header':0xC0,
    'main_event_map':0xC8, 'aux_event_map':0xD0,
    'main_event_count':0xD8, 'aux_event_count':0xDC,
    'main_motion_count':0xE0, 'aux_motion_count':0xE4,
    'main_vector':0xE8, 'main_vector_end':0xF0,
    'aux_vector':0xF8, 'aux_vector_end':0x100,
    'long_parameters':0x108, 'short_parameters':0x110,
    'dispatch_parameters':0x118, 'idle_parameters':0x120,
    'main_long_slot':0x128, 'main_short_slot':0x130,
    'aux_long_slot':0x138, 'aux_short_slot':0x140,
    'main_long_clip':0x148, 'main_short_clip':0x150,
    'aux_long_clip':0x158, 'aux_short_clip':0x160,
    'bank_table':0x168, 'bank_count':0x170,
    'long_table_slot':0x178, 'short_table_slot':0x180,
    'dispatch_table_slot':0x188, 'idle_bank':0x190, 'idle_table_slot':0x198,
    'event_manager':0x1A0, 'primary_event_state':0x1A8,
    'main_motion_map_table':0x1B0, 'aux_motion_map_table':0x1B8,
    'main_event_map_table':0x1C0, 'aux_event_map_table':0x1C8,
    'main_long_map_entry':0x1D0, 'main_short_map_entry':0x1D8,
    'aux_long_map_entry':0x1E0, 'aux_short_map_entry':0x1E8,
    'inventory_owner':0x1F0, 'selected_item':0x1F8, 'equipment_bits':0x1FC,
}
DWORD_FIELDS = {'magic','epoch','phase','long_id','short_id','main_event_count',
    'aux_event_count','main_motion_count','aux_motion_count','bank_count',
    'selected_item','equipment_bits'}
FIELD_WIDTHS = {k:4 if k in DWORD_FIELDS else 8 for k in FIELDS}


def encode_binding(values):
    """Encode every checked field; publish phase and magic last when installing."""
    if set(values) != set(FIELDS):
        raise ValueError('Exactly the exported binding fields are required')
    if values['magic'] != MAGIC or values['phase'] not in (0,1) or values['epoch'] <= 0:
        raise ValueError('A complete ready scene identity is required')
    raw=bytearray(DATA_SIZE)
    for key,offset in FIELDS.items():
        struct.pack_into('<I' if FIELD_WIDTHS[key]==4 else '<Q',raw,offset,values[key])
    return bytes(raw)


def _ptr(register, bad, scratch='rcx', alignment=8):
    s=f'''cmp {register}, 0x10000
jb {bad}
mov {scratch}, 0x800000000000
cmp {register}, {scratch}
jae {bad}
'''
    if alignment>1:
        s+=f'test {register}, {alignment-1}\njne {bad}\n'
    return s


def _load(key, register='rax', bad='lwsv_ready_bad', alignment=8):
    return f'mov {register}, qword ptr [r11+0x{FIELDS[key]:X}]\n'+_ptr(register,bad,alignment=alignment)


def ready_source():
    """RAX bool, R11 binding/R10 actor/R8 controller on success.

    Clobbers only Win64 volatile GPRs; preserves nonvolatile GPRs and all XMMs.
    Does not require E50 ownership or full charge. No native memory is written.
    """
    bad='lwsv_ready_bad'
    s=f'''lwsv_ready:
mov r11, {{data}}
add r11, 0x{DATA_OFFSET-CORE_OFFSET:X}
cmp dword ptr [r11], 0x{MAGIC:X}
jne {bad}
mov r9, {{data}}
mov eax, dword ptr [r9+0x1C]
test eax, eax
je {bad}
cmp eax, dword ptr [r11+4]
jne {bad}
'''+_load('actor','r10')+f'''cmp r10, qword ptr [r9+0x10]
jne {bad}
mov rax, {{player_slot}}
cmp qword ptr [rax], r10
jne {bad}
mov rax, qword ptr [r11+0x90]
cmp qword ptr [r10], rax
jne {bad}
cmp dword ptr [r10+4], 0x10000
jne {bad}
cmp dword ptr [r10+0xEF0], 0
jne {bad}
'''+_load('stat_component')+f'''cmp qword ptr [r10+0x240], rax
jne {bad}
cmp qword ptr [rax], r10
jne {bad}
cmp qword ptr [rax+0x108], r10
jne {bad}
cmp qword ptr [rax+0x18], 0
jle {bad}
cmp qword ptr [rax+0x20], 0
jle {bad}
mov r9d, dword ptr [r11+0x1FC]
mov ecx, r9d
shr ecx, 10
and ecx, 1
cmp byte ptr [rax+0x9CC], cl
jne {bad}
'''+_load('inventory_owner','rdx')+f'''mov rcx, {{mission_temp_owner}}
cmp qword ptr [rcx], rdx
jne {bad}
mov ecx, r9d
shr ecx, 11
and ecx, 1
and r9d, 0x3FF
cmp r9d, 700
jae {bad}
cmp dword ptr [rdx+rcx*4+0xB52B4], r9d
jne {bad}
imul r9, r9, 0xD0
mov ecx, dword ptr [r11+0x1F8]
cmp dword ptr [rdx+r9+0x210], ecx
jne {bad}
'''+_load('controller','r8')+f'''cmp qword ptr [r8+0x50], r10
jne {bad}
mov rax, qword ptr [r10+0x230]
'''+_ptr('rax',bad)+f'''cmp qword ptr [rax], r10
jne {bad}
cmp qword ptr [rax+8], r8
jne {bad}
'''+_load('motion_controller')+f'''cmp qword ptr [r10+0x38], rax
jne {bad}
'''+_load('event_manager')+f'''cmp qword ptr [r10+0x68], rax
jne {bad}
cmp qword ptr [rax+8], r10
jne {bad}
mov rdx, qword ptr [rax+0x40]
cmp rdx, qword ptr [r11+0x1A8]
jne {bad}
'''+_ptr('rdx',bad)+f'''cmp qword ptr [rdx+8], r10
jne {bad}
cmp dword ptr [rdx+0x18], 0
jne {bad}
'''+_load('package','r9')+f'''mov rax, {{weapon_package_vtable}}
cmp qword ptr [r9], rax
jne {bad}
'''+_load('bank_wrapper')+f'''cmp qword ptr [r9+0x1B8], rax
jne {bad}
mov rdx, qword ptr [rax+0x468]
cmp rdx, qword ptr [r11+0x30]
jne {bad}
'''+_ptr('rdx',bad)+f'''mov eax, dword ptr [rdx+0x130]
cmp eax, 1
jb {bad}
cmp eax, 4096
ja {bad}
cmp eax, dword ptr [r11+0x170]
jne {bad}
mov rcx, qword ptr [rdx+0x128]
cmp rcx, qword ptr [r11+0x168]
jne {bad}
mov rax, rcx
'''+_ptr('rax',bad)+f'''mov eax, dword ptr [r11+0x78]
cmp eax, dword ptr [r11+0x7C]
je {bad}
'''
    for key,id_key,motion,param,slot in (
        ('dispatch_record',None,-1,'dispatch_parameters','dispatch_table_slot'),
        ('long_record','long_id',9000,'long_parameters','long_table_slot'),
        ('short_record','short_id',9001,'short_parameters','short_table_slot')):
        s+=_load(key)+f'''cmp byte ptr [rax+0x40], 1
jne {bad}
cmp qword ptr [rax+0x38], rdx
jne {bad}
'''
        if id_key:
            s+=f'mov ecx, dword ptr [r11+0x{FIELDS[id_key]:X}]\ncmp dword ptr [rax], ecx\njne {bad}\n'
        else:
            s+=f'cmp dword ptr [rax], 169\njne {bad}\n'
        s+=f'''mov rcx, qword ptr [r11+0x{FIELDS[slot]:X}]
cmp rcx, qword ptr [r11+0x168]
jb {bad}
mov r9d, dword ptr [r11+0x170]
shl r9, 3
add r9, qword ptr [r11+0x168]
cmp rcx, r9
jae {bad}
test rcx, 7
jne {bad}
cmp qword ptr [rcx], rax
jne {bad}
mov rax, qword ptr [rax+0x20]
cmp rax, qword ptr [r11+0x{FIELDS[param]:X}]
jne {bad}
'''+_ptr('rax',bad,alignment=4)+f'''cmp dword ptr [rax+0x20], {motion}
jne {bad}
'''
    s+=_load('idle_record')+f'''cmp dword ptr [rax], 0
jne {bad}
cmp byte ptr [rax+0x40], 1
jne {bad}
mov rcx, qword ptr [r11+0x190]
cmp qword ptr [rax+0x38], rcx
jne {bad}
mov rcx, qword ptr [r11+0x198]
'''+_ptr('rcx',bad,'r9')+f'''cmp qword ptr [rcx], rax
jne {bad}
mov rax, qword ptr [rax+0x20]
cmp rax, qword ptr [r11+0x120]
jne {bad}
'''+_ptr('rax',bad,alignment=4)+f'''cmp dword ptr [rax+0x20], 0
jne {bad}
'''
    for side,pkg_off,motion_key,map_key,count_key,vec_key,end_key,map_table in (
        ('main',0x188,'main_motion','main_motion_map','main_motion_count','main_vector','main_vector_end','main_motion_map_table'),
        ('aux',0x190,'aux_motion','aux_motion_map','aux_motion_count','aux_vector','aux_vector_end','aux_motion_map_table')):
        s+=_load('package','r9')+_load(motion_key)+f'''cmp qword ptr [r9+0x{pkg_off:X}], rax
jne {bad}
mov rcx, {{motion_resource_vtable}}
cmp qword ptr [rax], rcx
jne {bad}
mov rcx, qword ptr [r11+0x{FIELDS[vec_key]:X}]
cmp qword ptr [rax+0x468], rcx
jne {bad}
mov rdx, qword ptr [r11+0x{FIELDS[end_key]:X}]
cmp qword ptr [rax+0x470], rdx
jne {bad}
cmp rdx, rcx
jbe {bad}
mov r9, rdx
sub r9, rcx
cmp r9, 0x80000
ja {bad}
test r9, 7
jne {bad}
mov rax, qword ptr [rax+0x480]
cmp rax, qword ptr [r11+0x{FIELDS[map_key]:X}]
jne {bad}
'''+_ptr('rax',bad,'r9')+f'''mov r9d, dword ptr [r11+0x{FIELDS[count_key]:X}]
cmp r9d, 1
jb {bad}
cmp r9d, 0x10000
ja {bad}
cmp dword ptr [rax+8], r9d
jne {bad}
mov r9, qword ptr [r11+0x{FIELDS[map_table]:X}]
cmp qword ptr [rax+0x10], r9
jne {bad}
mov rax, r9
'''+_ptr('rax',bad,'r9')
        for family in ('long','short'):
            s+=f'''mov rax, qword ptr [r11+0x{FIELDS[side+'_'+family+'_slot']:X}]
cmp rax, rcx
jb {bad}
cmp rax, rdx
jae {bad}
test rax, 7
jne {bad}
mov rax, qword ptr [rax]
cmp rax, qword ptr [r11+0x{FIELDS[side+'_'+family+'_clip']:X}]
jne {bad}
'''+_ptr('rax',bad,'r9')
            s+=f'''mov rax, qword ptr [r11+0x{FIELDS[side+'_'+family+'_map_entry']:X}]
mov r8, qword ptr [r11+0x{FIELDS[map_table]:X}]
cmp rax, r8
jb {bad}
mov r8d, dword ptr [r11+0x{FIELDS[count_key]:X}]
shl r8, 3
add r8, qword ptr [r11+0x{FIELDS[map_table]:X}]
cmp rax, r8
jae {bad}
test rax, 7
jne {bad}
cmp dword ptr [rax], {9000 if family=='long' else 9001}
jne {bad}
mov r8, qword ptr [r11+0x{FIELDS[side+'_'+family+'_slot']:X}]
sub r8, rcx
shr r8, 3
cmp dword ptr [rax+4], r8d
jne {bad}
'''
    for pkg_off,wrapper,owner,header,map_key,count_key,table_key in (
        (0x198,'main_event_wrapper','main_event_owner','main_event_header','main_event_map','main_event_count','main_event_map_table'),
        (0x1A0,'aux_event_wrapper','aux_event_owner','aux_event_header','aux_event_map','aux_event_count','aux_event_map_table')):
        s+=_load('package','r9')+_load(wrapper)+f'''cmp qword ptr [r9+0x{pkg_off:X}], rax
jne {bad}
mov rcx, {{weapon_event_vtable}}
cmp qword ptr [rax], rcx
jne {bad}
mov rax, qword ptr [rax+0x468]
cmp rax, qword ptr [r11+0x{FIELDS[owner]:X}]
jne {bad}
'''+_ptr('rax',bad)+f'''mov rdx, qword ptr [rax]
cmp rdx, qword ptr [r11+0x{FIELDS[header]:X}]
jne {bad}
'''+_ptr('rdx',bad)+f'''mov rcx, 0x4B4341505F474D54
cmp qword ptr [rdx], rcx
jne {bad}
mov rax, qword ptr [rax+8]
cmp rax, qword ptr [r11+0x{FIELDS[map_key]:X}]
jne {bad}
'''+_ptr('rax',bad)+f'''mov ecx, dword ptr [r11+0x{FIELDS[count_key]:X}]
cmp ecx, 1
jb {bad}
cmp ecx, 0x10000
ja {bad}
cmp dword ptr [rax+8], ecx
jne {bad}
mov rdx, qword ptr [r11+0x{FIELDS[table_key]:X}]
cmp qword ptr [rax+0x10], rdx
jne {bad}
'''+_ptr('rdx',bad)
    return s+'''mov r8, qword ptr [r11+0x10]
mov eax, 1
ret
lwsv_ready_bad:
xor eax, eax
ret
'''


def _owned(bad):
    return f'''cmp dword ptr [r11+0x18], 1
jne {bad}
mov rax, {{data}}
mov eax, dword ptr [rax+0xE50]
sub eax, 1
cmp eax, 1
ja {bad}
'''


def _prefilter(bad):
    """Reject dormant/foreign queries before reading any borrowed resources."""
    return f'''mov r9, {{data}}
mov eax, dword ptr [r9+0xE50]
sub eax, 1
cmp eax, 1
ja {bad}
mov r11, {{data}}
add r11, 0x{DATA_OFFSET-CORE_OFFSET:X}
cmp dword ptr [r11], 0x{MAGIC:X}
jne {bad}
cmp dword ptr [r11+0x18], 1
jne {bad}
mov eax, dword ptr [r9+0x1C]
cmp eax, dword ptr [r11+4]
jne {bad}
mov r10, qword ptr [r11+8]
cmp r10, qword ptr [r9+0x10]
jne {bad}
mov rax, {{player_slot}}
cmp qword ptr [rax], r10
jne {bad}
'''+_ptr('r10',bad)+_load('controller','r8',bad)+f'''cmp qword ptr [r8+0x50], r10
jne {bad}
mov rax, qword ptr [r10+0x230]
'''+_ptr('rax',bad)+f'''cmp qword ptr [rax], r10
jne {bad}
cmp qword ptr [rax+8], r8
jne {bad}
'''


def prefilter_source():
    """Share scope checks in the cleanup alignment gap to fit every view slot."""
    return 'lwsv_prefilter:\n'+_prefilter('lwsv_prefilter_bad')+'''mov eax, 1
ret
lwsv_prefilter_bad:
xor eax, eax
ret
'''


def _family_context(prefix):
    bad=prefix+'_fallback'
    return f'''mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x60]
je {prefix}_context
cmp rax, qword ptr [r11+0x68]
je {prefix}_context
cmp rax, qword ptr [r11+0x70]
je {prefix}_context
cmp rax, qword ptr [r11+0x58]
jne {bad}
mov rcx, {{data}}
cmp dword ptr [rcx+0xE50], 2
jne {bad}
{prefix}_context:
'''


def _startup_record(prefix, request='dword ptr [rsp+0xB8]'):
    bad=prefix+'_fallback'
    return f'''mov eax, {request}
cmp eax, 9000
je {prefix}_long
cmp eax, 9001
jne {bad}
mov rax, qword ptr [r11+0x70]
jmp {prefix}_record
{prefix}_long:
mov rax, qword ptr [r11+0x68]
{prefix}_record:
cmp qword ptr [r8+0x58], rax
je {prefix}_scope
cmp qword ptr [r8+0x60], rax
jne {bad}
{prefix}_scope:
'''


def _select_motion(prefix, selector='qword ptr [rsp+0xC0]'):
    return f'''cmp {selector}, 7
ja {prefix}_fallback
cmp {selector}, 4
jb {prefix}_main
mov rax, qword ptr [r11+0x40]
jmp {prefix}_selected
{prefix}_main:
mov rax, qword ptr [r11+0x38]
{prefix}_selected:
'''


def route_source(index):
    p=f'lwsv_view{index}'; bad=p+'_fallback'
    call=f'sub rsp, 8\ncall {{data}} + 0x{READY_OFFSET-CORE_OFFSET:X}\nadd rsp, 8\ntest eax, eax\nje {bad}\n'
    s=SAVE+f'sub rsp, 8\ncall {{data}} + 0x{PREFILTER_OFFSET-CORE_OFFSET:X}\nadd rsp, 8\ntest eax, eax\nje {bad}\n'
    if index==72:
        s+=_family_context(p)+f'''lea rax, [r8+0x70]
cmp rsi, rax
jne {bad}
test ebx, ebx
jne {bad}
'''+call+f'''
cmp dword ptr [rsp+0xA0], 3000
je {p}_terminal
mov eax, dword ptr [rsp+0xA0]
cmp eax, 169
je {p}_bank
cmp eax, dword ptr [r11+0x78]
je {p}_bank
cmp eax, dword ptr [r11+0x7C]
jne {bad}
{p}_bank:
mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x60]
je {p}_borrow
cmp rax, qword ptr [r11+0x68]
je {p}_borrow
cmp rax, qword ptr [r11+0x70]
je {p}_borrow
cmp rax, qword ptr [r11+0x58]
jne {bad}
mov rcx, {{data}}
cmp dword ptr [rcx+0xE50], 2
jne {bad}
{p}_borrow:
mov rax, qword ptr [r11+0x30]
mov qword ptr [rsp+0xC0], rax
'''+RESTORE+'''test rcx, rcx
jmp {return}
'''+f'''{p}_terminal:
mov rax, qword ptr [r8+0x58]
cmp rax, qword ptr [r11+0x68]
je {p}_finish
cmp rax, qword ptr [r11+0x70]
jne {bad}
{p}_finish:
mov qword ptr [rsp+0xA0], 0
'''+RESTORE+'''mov rcx, qword ptr [rsi+rax*8]
test rcx, rcx
jmp {return}
'''
    else:
        request='esi' if index in (76,77) else 'dword ptr [rsp+0xB8]'
        s+=_startup_record(p,request)+call
        if index==75:
            s+=f'''cmp r14, qword ptr [r11+0x1A0]
jne {bad}
cmp qword ptr [rsp+0xC0], 7
ja {bad}
cmp qword ptr [rsp+0xC0], 4
jb {p}_main
mov rax, qword ptr [r11+0xA0]
jmp {p}_selected
{p}_main:
mov rax, qword ptr [r11+0x98]
{p}_selected:
mov qword ptr [rsp+0xC0], rax
'''+RESTORE+'jmp {return}\n'
        else:
            arr='rdi' if index!=74 else 'qword ptr [rsp+0xC0]'
            s+=f'''mov rax, qword ptr [r11+0x80]
cmp {arr}, rax
jne {bad}
'''+_select_motion(p,'qword ptr [rsp+0xA8]' if index==74 else 'qword ptr [rsp+0xC0]')
            if index in (74,76):
                s+=('cmp rax, r14\n' if index==76 else 'cmp rax, 0\n')+'''pushfq
pop rax
mov qword ptr [rsp+0xD0], rax
'''
            else:
                s+='mov qword ptr [rsp+0x90], rax\n'
            s+=RESTORE+'jmp {return}\n'
    return s+bad+':\n'+RESTORE


def common_source():
    p='lwsv_common'; bad=p+'_fallback'
    s=p+':\n'+SAVE+f'call {{data}} + 0x{PREFILTER_OFFSET-CORE_OFFSET:X}\ntest eax, eax\nje {bad}\n'+_family_context(p)+f'''lea rax, [r8+0x70]
cmp qword ptr [rsp+0xC0], rax
jne {bad}
'''+f'call {{data}} + 0x{READY_OFFSET-CORE_OFFSET:X}\ntest eax, eax\nje {bad}\n'+f'''
cmp dword ptr [rsp+0xB8], 169
je {p}_dispatch
mov eax, dword ptr [rsp+0xB8]
cmp eax, dword ptr [r11+0x78]
je {p}_long
cmp eax, dword ptr [r11+0x7C]
jne {bad}
mov rax, qword ptr [r11+0x70]
jmp {p}_found
{p}_long:
mov rax, qword ptr [r11+0x68]
jmp {p}_found
{p}_dispatch:
mov rax, qword ptr [r11+0x60]
{p}_found:
mov rcx, qword ptr [rsp+0xB0]
test rcx, rcx
je {p}_output
'''+_ptr('rcx',bad,'rdx',alignment=4)+f'''mov dword ptr [rcx], 0
{p}_output:
mov qword ptr [rsp+0xC8], rax
'''+RESTORE+'''ret
'''+bad+':\nmov qword ptr [rsp+0xC8], 0\n'+RESTORE+'ret\n'
    return s


def common_thin_source():
    return f'''pushfq
push rax
sub rsp, 0x28
call {{data}} + 0x{COMMON_OFFSET-CORE_OFFSET:X}
test rax, rax
jne lwsv_common_thin_success
add rsp, 0x28
pop rax
popfq
jmp lwsv_common_thin_fallback
lwsv_common_thin_success:
add rsp, 0x28
lea rsp, [rsp+8]
popfq
ret
lwsv_common_thin_fallback:
'''


def gateway_source():
    return common_thin_source()+'jmp {data} + 0x20080\n'


def _assemble_one(plan, source, offset):
    from build_profile import assemble
    p=deepcopy(plan); h=deepcopy(p['hooks'][81]); h['asm']=source; h['code_offset']=offset
    p['hooks']=[h]
    return assemble(p,0x140000000,0x144000000)[0]['payload']


def apply_views(plan):
    """Return a pure 82-hook candidate; never installs or populates its binding."""
    if len(plan['hooks'])!=82 or plan['data_offset']!=CORE_OFFSET or plan['allocation_size']!=0x55000:
        raise ValueError('The exact 82-hook Beta5.6 layout is required')
    if plan.get('living_weapon_start_views_revision'):
        raise ValueError('Living Weapon views are already applied')
    expected={39:('HE_LadderCommonLookup',0x73FA40,0xE800,0x800),
        72:('HE_OrochiWeaponBankRead',0x73FA92,0x4A000,0x1000),
        73:('HE_OrochiWeaponMotionRead',0x954F0B,0x4B000,0x1000),
        74:('HE_OrochiWeaponMotionPresence',0x954EBC,0x4C000,0x1000),
        75:('HE_OrochiWeaponEventRead',0x968B77,0x4D000,0x1000),
        76:('HE_OrochiWeaponBlendPresence',0x9550A6,0x4E000,0x1000),
        77:('HE_OrochiWeaponBlendRead',0x9550EC,0x4F000,0x1000),
        81:('HE_PlayerResourceLifetimeCleanup',0x753616,0x51000,0x2000)}
    for i,shape in expected.items():
        h=plan['hooks'][i]
        if (h['name'],h['rva'],h['code_offset'],h['code_capacity'])!=shape:
            raise ValueError('An existing resource/cleanup entry differs')
    p=deepcopy(plan)
    if not p['hooks'][39]['asm'].startswith('jmp {data} + 0x20080\nnop\n'):
        raise ValueError('The shared Abyss common lookup entry differs')
    # Other existing hooks call internal ladder helpers at fixed offsets within
    # this body. Retain every original offset; redirect only the first near JMP.
    p['hooks'][39]['asm']=p['hooks'][39]['asm'].replace(
        'jmp {data} + 0x20080\nnop\n',
        f'jmp {{data}} + 0x{GATEWAY_OFFSET-CORE_OFFSET:X}\nnop\n',1)
    for i in range(72,78):
        p['hooks'][i]['asm']=route_source(i)+p['hooks'][i]['asm']
        p['hooks'][i]['purpose']+='; independently owned exact LW startup resource register view'
    h=p['hooks'][81]; old=_assemble_one(p,h['asm'],h['code_offset'])
    prefilter=prefilter_source(); prefilter_bytes=_assemble_one(p,prefilter,PREFILTER_OFFSET)
    ready=ready_source(); ready_bytes=_assemble_one(p,ready,READY_OFFSET)
    common=common_source(); common_bytes=_assemble_one(p,common,COMMON_OFFSET)
    gateway=gateway_source(); gateway_bytes=_assemble_one(p,gateway,GATEWAY_OFFSET)
    if (h['code_offset']+len(old)>PREFILTER_OFFSET or PREFILTER_OFFSET+len(prefilter_bytes)>READY_OFFSET
            or READY_OFFSET+len(ready_bytes)>COMMON_OFFSET or COMMON_OFFSET+len(common_bytes)>GATEWAY_OFFSET
            or GATEWAY_OFFSET+len(gateway_bytes)>CODE_END):
        raise ValueError('Living Weapon helper code overlaps existing cleanup or data')
    h['asm'] += ('\n'+'.byte 0\n'*(PREFILTER_OFFSET-h['code_offset']-len(old))+prefilter+
        '.byte 0\n'*(READY_OFFSET-PREFILTER_OFFSET-len(prefilter_bytes))+ready+
        '.byte 0\n'*(COMMON_OFFSET-READY_OFFSET-len(ready_bytes))+common+
        '.byte 0\n'*(GATEWAY_OFFSET-COMMON_OFFSET-len(common_bytes))+gateway)
    p['living_weapon_start_views_revision']=3
    p['living_weapon_start_binding_offset']=DATA_OFFSET
    p['living_weapon_start_binding_size']=DATA_SIZE
    p['living_weapon_start_ready_offset']=READY_OFFSET
    p['living_weapon_start_prefilter_offset']=PREFILTER_OFFSET
    p['living_weapon_start_common_offset']=COMMON_OFFSET
    p['living_weapon_start_gateway_offset']=GATEWAY_OFFSET
    p['living_weapon_start_views_gameplay_validated']=False
    p['abyss_assembly_code_intervals'][h['name']] += [
        [PREFILTER_OFFSET-h['code_offset'],PREFILTER_OFFSET-h['code_offset']+len(prefilter_bytes)],
        [READY_OFFSET-h['code_offset'],READY_OFFSET-h['code_offset']+len(ready_bytes)],
        [COMMON_OFFSET-h['code_offset'],COMMON_OFFSET-h['code_offset']+len(common_bytes)],
        [GATEWAY_OFFSET-h['code_offset'],GATEWAY_OFFSET-h['code_offset']+len(gateway_bytes)]]
    from build_profile import assemble
    before=assemble(plan,0x140000000,0x144000000); after=assemble(p,0x140000000,0x144000000)
    for i,(a,b) in enumerate(zip(before,after)):
        if a['patched']!=b['patched'] or a['original']!=b['original']:
            raise ValueError('Native entry patches must remain exact')
        if i not in expected and a['payload']!=b['payload']:
            raise ValueError('An unrelated payload changed')
        if i in range(72,78) and not b['payload'].endswith(a['payload']):
            # Relocations within old bodies shift after the prepended code;
            # source is the immutable fallback identity, not byte suffix identity.
            if not p['hooks'][i]['asm'].endswith(plan['hooks'][i]['asm']):
                raise ValueError('An original fallback body changed')
    p['living_weapon_start_views_sizes']={str(i):len(after[i]['payload']) for i in expected}
    p['living_weapon_start_helper_sizes']={'prefilter':len(prefilter_bytes),'ready':len(ready_bytes),'common':len(common_bytes)}
    p['living_weapon_start_helper_sizes']['gateway']=len(gateway_bytes)
    if after[39]['payload'][5:] != before[39]['payload'][5:]:
        raise ValueError('Fixed cross-hook ladder helper offsets changed')
    return p
