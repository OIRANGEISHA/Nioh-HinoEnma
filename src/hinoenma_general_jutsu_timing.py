"""Recover a skipped early projectile event without replaying frame-zero events.

The observed Kunai entry advanced from frame zero to frame six while its
projectile creation is at frame two. Arm on the native zero-frame call, then
schedule exactly the missing creation frame once, before the ordinary call.
The native scheduler owns projectile creation, release and item consumption.
"""
from copy import deepcopy
import struct
from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_general_jutsu import digest, SCHEDULE_OFFSET
from hinoenma_special_item_actions import _once
import hinoenma_item_hurt_lookup as hurt
from hinoenma_spell_event_catchup import prefix as original_gap_prefix

PARENT_SHA256 = 'eaf6c5312e627df7714e47f68e583d6cae8f5c40236a538be8a4fcbaa273c7bc'
CARRIER = 'HE_PostDefeatHealScript'
OFFSET = 0x18400
ENTRY = 'HE_SaltEventCatchup'
# action: native category, body motion, first creation frame, release frame
RULES = {165:(4,103,15,40),166:(5,106,10,36),982:(6,120,15,35),
         986:(11,104,2,24),605:(16,125,19,64),607:(19,124,10,95),608:(20,123,10,50),
         612:(11,107,2,21),613:(5,108,2,33)}
CHAIN_CARRIER = 'HE_MapPreviewCameraHeightPrivate'
CHAIN_OFFSET = 0x2BA00
CHAIN_SCHEDULES = {
    612:'12000200ffff1f001500ffff140000000f00'+'ffff0000ffff'*13,
    613:'12000200ffff1f002100ffff140000000f00'+'ffff0000ffff'*13,
}
CHAIN_ROWS = b''.join(struct.pack('<2i96s',a,RULES[a][1],bytes.fromhex(raw))
                      for a,raw in CHAIN_SCHEDULES.items())
CREATE = bytes.fromhex('0000ffff000000000000ffffffffffff00000000ffffff06ffffffff1600000000000000000000000000ffffff00ffffffffffff00000000000000000000ffffffff6464646464646464ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff')
RELEASE = bytes.fromhex('0000ffff000000000000ffffffffffff00000000ffffff05ffffffffffff000000000000000000000000ffffff00ffffffffffff00000000000000000000ffffffff6464646464646464ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff')


def float_bits(value):
    return struct.unpack('<I',struct.pack('<f',value))[0]


def exact_descriptor(raw):
    return ''.join(f'movabs rax, {struct.unpack_from("<Q",raw,n)[0]}\ncmp qword ptr [r11+{n}], rax\njne jutsu_early_reject\n' for n in range(0,128,8))


def assembly():
    # This trampoline replaces a CALL site: incoming RSP is 16-byte aligned.
    # Eight pushes and A0 locals retain alignment and reserve native shadow space.
    s='''jutsu_early_entry:
pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xA0
'''
    for n in range(6):
        s+=f'movdqu xmmword ptr [rsp+{0x20+n*16}], xmm{n}\n'
    s+='''stmxcsr dword ptr [rsp+0x80]
mov qword ptr [rsp+0x88], rcx
mov qword ptr [rsp+0x90], rdx
test rcx, rcx
je jutsu_early_reject
test rdx, rdx
je jutsu_early_reject
cmp qword ptr [rcx+0x58], rdx
jne jutsu_early_reject
cmp byte ptr [rdx+0x40], 1
jne jutsu_early_reject
cmp dword ptr [rcx+0x68], 2
jne jutsu_early_reject
mov r8, qword ptr [rcx+0x80]
test r8, r8
je jutsu_early_reject
cmp qword ptr [rdx+0x38], r8
jne jutsu_early_reject
cmp dword ptr [rcx+0x548], 0
jl jutsu_early_reject
mov rax, qword ptr [rdx+0x20]
test rax, rax
je jutsu_early_reject
cmp dword ptr [rax+0x34], -1
jne jutsu_early_reject
'''
    for action in RULES:
        s+=f'cmp dword ptr [rdx], {action}\nje jutsu_early_action_{action}\n'
    s+='jmp jutsu_early_reject\n'
    for action,(cat,motion,first,last) in RULES.items():
        s+=f'''jutsu_early_action_{action}:
cmp dword ptr [rcx+0x54C], {cat}
jne jutsu_early_reject
cmp dword ptr [rax+0x20], {motion}
jne jutsu_early_reject
mov dword ptr [rsp+0x98], {float_bits(first)}
mov dword ptr [rsp+0x9C], {float_bits(last)}
'''
        if action==982:
            s+='cmp dword ptr [rcx+0x548], 7739\nje jutsu_early_restore\n'
        if action in CHAIN_SCHEDULES:
            offset=CHAIN_OFFSET-0xF000+list(CHAIN_SCHEDULES).index(action)*104+8
            s+=f'mov r10, {{data}}\nadd r10, {offset}\njmp jutsu_early_chain_schedule\n'
        else:
            s+=f'mov edx, {action}\njmp jutsu_early_schedule\n'
    s+=f'''jutsu_early_schedule:
call {{data}} + {SCHEDULE_OFFSET-0xF000}
mov rcx, qword ptr [rsp+0x88]
mov rdx, qword ptr [rsp+0x90]
test al, al
je jutsu_early_reject
jmp jutsu_early_schedule_done
jutsu_early_chain_schedule:
lea r11, [rax+0x40]
mov ecx, 12
jutsu_early_chain_schedule_loop:
mov r9, qword ptr [r10]
cmp qword ptr [r11], r9
jne jutsu_early_reject
add r10, 8
add r11, 8
dec ecx
jne jutsu_early_chain_schedule_loop
mov rcx, qword ptr [rsp+0x88]
mov rdx, qword ptr [rsp+0x90]
jutsu_early_schedule_done:
mov r10, qword ptr [rcx+0x80]
cmp word ptr [r10+0x88], 32
jb jutsu_early_reject
cmp word ptr [r10+0x88], 4096
ja jutsu_early_reject
mov r10, qword ptr [r10+0x80]
test r10, r10
je jutsu_early_reject
cmp dword ptr [rdx], 982
je jutsu_early_descriptor17
mov r11, qword ptr [r10+18*8]
test r11, r11
je jutsu_early_reject
'''
    s+=exact_descriptor(CREATE)
    s+='jmp jutsu_early_descriptor31\njutsu_early_descriptor17:\nmov r11, qword ptr [r10+17*8]\ntest r11, r11\nje jutsu_early_reject\n'
    create17=bytearray(CREATE);struct.pack_into('<h',create17,0x1C,21)
    s+=exact_descriptor(create17)
    s+='jutsu_early_descriptor31:\nmov r11, qword ptr [r10+31*8]\ntest r11, r11\nje jutsu_early_reject\n'
    s+=exact_descriptor(RELEASE)
    s+='''cmp dword ptr [rcx+0x24], 0x3F800000
jne jutsu_early_reject
cmp dword ptr [rcx+0x550], 1
jne jutsu_early_reject
cmp dword ptr [rcx+0x554], 0
jne jutsu_early_reject
cmp qword ptr [rcx+0x558], 0
jne jutsu_early_reject
cmp byte ptr [rcx+0x570], 0
jne jutsu_early_reject
cmp qword ptr [rcx+0x728], 0
jne jutsu_early_reject
mov rax, qword ptr [rcx+0x720]
test rax, rax
je jutsu_early_reject
cmp qword ptr [rax], rax
jne jutsu_early_reject
cmp qword ptr [rax+8], rax
jne jutsu_early_reject
'''
    role=original_gap_prefix().split('mov r10, qword ptr [rcx+0x50]\n',1)[1].split('cmp r9b, 1\n',1)[0]
    s+=('mov r10, qword ptr [rcx+0x50]\n'+role).replace('spell_gap_','jutsu_early_')
    s+='''cmp byte ptr [rsp+0xB0], 1
je jutsu_early_arm
cmp byte ptr [rsp+0xB0], 0
jne jutsu_early_reject
cmp dword ptr [r11+0x4E80], 3
jne jutsu_early_restore
mov eax, dword ptr [r11+0x1C]
cmp dword ptr [r11+0x4E84], eax
jne jutsu_early_reject
cmp qword ptr [r11+0x4E88], r10
jne jutsu_early_reject
cmp qword ptr [r11+0x4E90], rcx
jne jutsu_early_reject
cmp qword ptr [r11+0x4E98], rdx
jne jutsu_early_reject
mov eax, dword ptr [rcx+0x548]
cmp dword ptr [r11+0x4EA0], eax
jne jutsu_early_reject
mov eax, 3
xor r10d, r10d
lock cmpxchg dword ptr [r11+0x4E80], r10d
jne jutsu_early_restore
mov eax, dword ptr [rsp+0x40]
cmp eax, dword ptr [rsp+0x98]
jbe jutsu_early_restore
cmp eax, dword ptr [rsp+0x9C]
jae jutsu_early_restore
mov eax, dword ptr [rsp+0x98]
movd xmm2, eax
xor r9d, r9d
mov r8, qword ptr [rsp+0xB8]
call {salt_catchup_native_schedule}
jmp jutsu_early_restore
jutsu_early_arm:
cmp dword ptr [rsp+0x40], 0
jne jutsu_early_reject
mov dword ptr [r11+0x4E80], 0
mov eax, dword ptr [r11+0x1C]
mov dword ptr [r11+0x4E84], eax
mov qword ptr [r11+0x4E88], r10
mov qword ptr [r11+0x4E90], rcx
mov qword ptr [r11+0x4E98], rdx
mov eax, dword ptr [rcx+0x548]
mov dword ptr [r11+0x4EA0], eax
mov dword ptr [r11+0x4E80], 3
jmp jutsu_early_restore
jutsu_early_reject:
mov rcx, qword ptr [rsp+0x88]
mov r11, {data}
cmp dword ptr [r11+0x4E80], 3
jne jutsu_early_restore
cmp qword ptr [r11+0x4E90], rcx
jne jutsu_early_restore
mov dword ptr [r11+0x4E80], 0
jutsu_early_restore:
ldmxcsr dword ptr [rsp+0x80]
'''
    for n in range(6):
        s+=f'movdqu xmm{n}, xmmword ptr [rsp+{0x20+n*16}]\n'
    s+='''add rsp, 0xA0
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {data} + 0xD300
'''
    return s


def apply_general_jutsu_timing(parent):
    if digest(parent)!=PARENT_SHA256:
        raise ValueError('Exact generic-family revision 1 required')
    plan=deepcopy(parent)
    hooks={h['name']:h for h in plan['hooks']}
    carrier=hooks[CARRIER]
    ks=Ks(KS_ARCH_X86,KS_MODE_64)
    values={k:0x140000000+r for k,r in plan['targets'].items()}
    values.update(data=0x14400F000,**{'return':0x140000000+carrier['rva']+carrier['length']})
    old=bytes(ks.asm(carrier['asm'].format(**values),0x144000000+carrier['code_offset'])[0])
    pad=OFFSET-carrier['code_offset']-len(old)
    if pad<0:
        raise ValueError('Reserved timing helper space occupied')
    carrier['asm']+='\n'+'nop\n'*pad+assembly()
    raw=bytes(ks.asm(carrier['asm'].format(**values),0x144000000+carrier['code_offset'])[0])
    if not raw.startswith(old) or len(raw)>carrier['code_capacity']:
        raise ValueError('Timing helper exceeds its existing owned slot')
    entry=hooks[ENTRY]
    entry['asm']=_once(entry['asm'],'jmp {data} + 0xD300\n',f'jmp {{data}} + {OFFSET-0xF000}\n')
    # Native consecutive throws alternate between 986/612 and 166/613.
    # Their lookup already falls through to the common bank. Extend only the
    # exact common-motion input/injury guards, retaining the game's transitions.
    for name,suffix in (('HE_InputA','a'),('HE_InputB','b')):
        anchor=f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        extra=''.join(f'mov ecx, {RULES[a][1]}\ncmp dword ptr [rdx], {a}\nje special_item_input_found_{suffix}\n' for a in CHAIN_SCHEDULES)
        hooks[name]['asm']=_once(hooks[name]['asm'],anchor,extra+anchor)
    ch=hooks[CHAIN_CARRIER]
    values['return']=0x140000000+ch['rva']+ch['length']
    before=bytes(ks.asm(ch['asm'].format(**values),0x144000000+ch['code_offset'])[0])
    padding=CHAIN_OFFSET-ch['code_offset']-len(before)
    if padding<0:raise ValueError('Reserved chain schedule space occupied')
    ch['asm']+='\n'+'nop\n'*padding+'.byte '+','.join(map(str,CHAIN_ROWS))+'\n'
    intervals=plan.setdefault('abyss_assembly_code_intervals',{})
    if CHAIN_CARRIER in intervals:raise ValueError('Unexpected existing chain-carrier code intervals')
    intervals[CHAIN_CARRIER]=[[0,CHAIN_OFFSET-ch['code_offset']]]
    ih=hooks[hurt.CODE_CARRIER]
    anchor='jne item_hurt_cast_scan\njmp item_hurt_reject\nitem_hurt_cast_found:\n'
    extra='jne item_hurt_cast_scan\n'
    for i,a in enumerate(CHAIN_SCHEDULES):
        extra+=f'''cmp edx, {a}
jne jutsu_chain_hurt_next_{a}
lea rdi, [r15+{CHAIN_OFFSET-0xF000+i*104}]
jmp item_hurt_cast_found
jutsu_chain_hurt_next_{a}:
'''
    ih['asm']=_once(ih['asm'],anchor,extra+'jmp item_hurt_reject\nitem_hurt_cast_found:\n')
    changed=[]
    for nh,oh in zip(plan['hooks'],parent['hooks']):
        if nh['asm']==oh['asm']:continue
        changed.append(nh['name'])
        values['return']=0x140000000+nh['rva']+nh['length']
        encoded=bytes(ks.asm(nh['asm'].format(**values),0x144000000+nh['code_offset'])[0])
        if len(encoded)>nh['code_capacity']:raise ValueError('Timing/chain capacity exceeded: '+nh['name'])
    plan['general_jutsu_timing_candidate']=dict(revision=1,actions=sorted(RULES),
        changed_hooks=changed,marker_value=3,observed_kunai_item=57728,
        one_missing_creation_frame=True,zero_frame_events_not_replayed=True,
        native_projectile_release_and_stock=True,live_confirmation_pending=True)
    return plan
