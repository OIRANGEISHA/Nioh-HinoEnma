"""Instance-bound visual life-drain for the observed defeated Yuki-Onna.

Each new attempt qualifies the native referenced actor, effective default
action groups and selected-bank victim clip. State contains runtime receipts,
never fixed process pointers. A new player spawn invalidates receipts before
an old target can be read. Native reference registration and action cleanup
remain responsible for pairing lifetime; zero-HP targets grant no healing.
"""
from copy import deepcopy

STATE_OFFSET = 0xC00
STATE_SIZE = 0x200
LAYOUT = {
    'epoch': 0x08, 'source': 0x10, 'source_identity': 0x18,
    'source_controller': 0x20, 'source_stats': 0x28,
    'target': 0x30, 'target_identity': 0x38,
    'target_controller': 0x40, 'target_stats': 0x48,
    'reaction': 0x50, 'reaction_parameters': 0x58, 'clip': 0x60,
    'original_action': 0x68, 'original_parameters': 0x70,
    'active': 0x78, 'candidate_calls': 0x7C, 'candidate_successes': 0x80,
    'damage_skips': 0x84, 'restores': 0x88,
    'motion_controller': 0x90, 'bank': 0x98, 'common_resource': 0xA0,
    'candidate_entries': 0xA8, 'source_attempt_evaluations': 0xAC,
    'heal_skips': 0xB0,
}
TARGETS = {'postdefeat_player_slot': 0x18A0490,
           'postdefeat_pair_candidate': 0x741F30,
           'postdefeat_damage_skip': 0x717C40,
           'postdefeat_native_recovery': 0x731180,
           'postdefeat_script_recovery': 0x7B4AB0}

# The original RCX/RDX/R8 and RSP are E0/D8/D0 and F8 above this frame.
# 68..B0 is local scratch. All volatile SIMD registers and MXCSR survive
# registration; Win64 native calls receive aligned stacks and shadow space.
SAVE = '''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0xB8
movdqu xmmword ptr [rsp], xmm0
movdqu xmmword ptr [rsp+0x10], xmm1
movdqu xmmword ptr [rsp+0x20], xmm2
movdqu xmmword ptr [rsp+0x30], xmm3
movdqu xmmword ptr [rsp+0x40], xmm4
movdqu xmmword ptr [rsp+0x50], xmm5
stmxcsr dword ptr [rsp+0x60]
mov r11, {data}
add r11, 0xC00
'''
RESTORE = '''ldmxcsr dword ptr [rsp+0x60]
movdqu xmm0, xmmword ptr [rsp]
movdqu xmm1, xmmword ptr [rsp+0x10]
movdqu xmm2, xmmword ptr [rsp+0x20]
movdqu xmm3, xmmword ptr [rsp+0x30]
movdqu xmm4, xmmword ptr [rsp+0x40]
movdqu xmm5, xmmword ptr [rsp+0x50]
add rsp, 0xB8
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
'''


def current_source(prefix, *, bound=False, alive=False):
    """Only the captured/native Hino player owns this controller and stats."""
    code = '''mov rax, {data}
cmp dword ptr [rax+4], 0
je P_done
mov r10, qword ptr [rax+0x10]
test r10, r10
je P_done
mov rdx, {postdefeat_player_slot}
cmp r10, qword ptr [rdx]
jne P_done
'''
    if bound:
        code += '''cmp r10, qword ptr [r11+0x10]
jne P_done
mov edx, dword ptr [rax+0x1C]
cmp edx, dword ptr [r11+8]
jne P_done
mov rdx, qword ptr [r11+0x18]
cmp rdx, qword ptr [r10]
jne P_done
'''
    code += '''mov edx, dword ptr [r10]
cmp edx, dword ptr [rax+4]
jne P_done
cmp edx, 0x58E5E
je P_hino
cmp edx, 0x51BE1
jne P_done
P_hino:
cmp dword ptr [r10+4], 0x10000
jne P_done
cmp dword ptr [r10+0xEF0], 0
jne P_done
mov rax, qword ptr [r10+0xE90]
test rax, rax
je P_done
cmp dword ptr [rax+0xC], 1
jne P_done
mov rax, qword ptr [r10+0x240]
test rax, rax
je P_done
cmp r10, qword ptr [rax]
jne P_done
cmp r10, qword ptr [rax+0x108]
jne P_done
'''
    if bound:
        code += 'cmp rax, qword ptr [r11+0x28]\njne P_done\n'
    if alive:
        code += 'cmp qword ptr [rax+0x20], 0\njle P_done\n'
    code += '''mov rax, qword ptr [r10+0x230]
test rax, rax
je P_done
cmp r10, qword ptr [rax]
jne P_done
mov r9, qword ptr [rax+8]
test r9, r9
je P_done
cmp r10, qword ptr [r9+0x50]
jne P_done
'''
    if bound:
        code += 'cmp r9, qword ptr [r11+0x20]\njne P_done\n'
    return code.replace('P_', prefix+'_')


def source_action(prefix, action, motion):
    return f'''mov rax, qword ptr [r9+0x58]
test rax, rax
je {prefix}_done
cmp dword ptr [rax], {action}
jne {prefix}_done
cmp byte ptr [rax+0x40], 1
jne {prefix}_done
mov rax, qword ptr [rax+0x20]
test rax, rax
je {prefix}_done
cmp dword ptr [rax+0x20], {motion}
jne {prefix}_done
'''


def target_owned(prefix, *, bound=False):
    """R8 is a currently native-referenced target, never a stale saved pointer."""
    code = '''test r8, r8
je P_done
cmp r8, r10
je P_done
cmp dword ptr [r8], 0x28EEC
jne P_done
cmp word ptr [r8+4], 0
jne P_done
cmp word ptr [r8+6], 1
je P_done
'''
    if bound:
        code += '''cmp r8, qword ptr [r11+0x30]
jne P_done
mov rax, qword ptr [r11+0x38]
cmp rax, qword ptr [r8]
jne P_done
'''
    code += '''mov rax, qword ptr [r8+0x240]
test rax, rax
je P_done
cmp r8, qword ptr [rax]
jne P_done
cmp r8, qword ptr [rax+0x108]
jne P_done
cmp qword ptr [rax+0x20], 0
jne P_done
cmp dword ptr [rax+0x10], 1
jne P_done
'''
    if bound:
        code += 'cmp rax, qword ptr [r11+0x48]\njne P_done\n'
    code += '''mov rax, qword ptr [r8+0x230]
test rax, rax
je P_done
cmp r8, qword ptr [rax]
jne P_done
mov rax, qword ptr [rax+8]
test rax, rax
je P_done
cmp r8, qword ptr [rax+0x50]
jne P_done
'''
    if bound:
        code += 'cmp rax, qword ptr [r11+0x40]\njne P_done\n'
    return code.replace('P_', prefix+'_')


def effective_action(prefix, action, result_slot, *, common=False):
    """Native first-enabled precedence across default groups 0, 1, 2."""
    code = f'''mov rax, qword ptr [rsp+0x70]
lea rax, [rax+0x70]
mov qword ptr [rsp+0xA8], rax
mov ecx, 3
P_group_loop:
mov rax, qword ptr [rsp+0xA8]
mov rax, qword ptr [rax]
test rax, rax
je P_group_next
mov edx, dword ptr [rax+0x130]
test edx, edx
je P_group_next
cmp edx, 4096
ja P_done
mov r8, qword ptr [rax+0x128]
test r8, r8
je P_done
P_record_loop:
mov rax, qword ptr [r8]
test rax, rax
je P_record_next
cmp dword ptr [rax], {action}
jne P_record_next
cmp byte ptr [rax+0x40], 0
je P_record_next
'''
    if common:
        code += 'cmp ecx, 1\njne P_done\n'
    code += f'''mov qword ptr [rsp+{result_slot:#x}], rax
jmp P_found
P_record_next:
add r8, 8
dec edx
jne P_record_loop
P_group_next:
add qword ptr [rsp+0xA8], 8
dec ecx
jne P_group_loop
jmp P_done
P_found:
'''
    # All lookup failures end the candidate hook, not just this sublookup.
    return code.replace('P_done', 'pd_candidate_done').replace('P_', prefix+'_')


def candidate_asm():
    return (SAVE+'lock inc dword ptr [r11+0xA8]\n'+current_source('pd_candidate', alive=True)+'''
cmp r9, qword ptr [rsp+0xE0]
jne pd_candidate_done
'''+source_action('pd_candidate',62,1100)+'''
lock inc dword ptr [r11+0xAC]
cmp qword ptr [r9+0x5B0], 0
jne pd_candidate_done
mov rax, {data}
mov edx, dword ptr [rax+0x1C]
cmp edx, dword ptr [r11+8]
jne pd_candidate_invalidate
cmp r10, qword ptr [r11+0x10]
jne pd_candidate_invalidate
mov rax, qword ptr [r10]
cmp rax, qword ptr [r11+0x18]
jne pd_candidate_invalidate
cmp r9, qword ptr [r11+0x20]
jne pd_candidate_invalidate
jmp pd_candidate_token
pd_candidate_invalidate:
mov dword ptr [r11+0x78], 0
pd_candidate_token:
cmp dword ptr [r11+0x78], 0
je pd_candidate_ref
cmp dword ptr [r11+0x78], 2
jne pd_candidate_done
pd_candidate_ref:
mov r8, qword ptr [r9+0x670]
'''+target_owned('pd_candidate')+'''
cmp qword ptr [rax+0x5B0], 0
jne pd_candidate_done
mov qword ptr [rsp+0x70], rax
mov qword ptr [rsp+0x68], r8
mov rax, qword ptr [r8+0xE90]
test rax, rax
je pd_candidate_done
cmp dword ptr [rax+0xC], 1
jne pd_candidate_done
mov rax, qword ptr [rsp+0x70]
mov rax, qword ptr [rax+0x58]
test rax, rax
je pd_candidate_done
cmp dword ptr [rax], 3158
jne pd_candidate_done
cmp byte ptr [rax+0x40], 1
jne pd_candidate_done
mov qword ptr [rsp+0x78], rax
'''+effective_action('pd_original',3158,0x80)+'''
cmp rax, qword ptr [rsp+0x78]
jne pd_candidate_done
mov rax, qword ptr [rax+0x20]
test rax, rax
je pd_candidate_done
test qword ptr [rax+0x18], 0x20000000
jne pd_candidate_done
mov qword ptr [rsp+0x88], rax
'''+effective_action('pd_reaction',858,0x90,common=True)+'''
mov rax, qword ptr [rax+0x20]
test rax, rax
je pd_candidate_done
cmp dword ptr [rax+0x20], 44000
jne pd_candidate_done
mov qword ptr [rsp+0x98], rax
mov r8, qword ptr [rsp+0x68]
mov rax, qword ptr [r8+0x38]
test rax, rax
je pd_candidate_done
mov qword ptr [rsp+0xA0], rax
mov edx, dword ptr [rax+0x50]
cmp edx, 1
ja pd_candidate_done
mov dword ptr [rsp+0xB0], edx
shl edx, 5
mov r8, qword ptr [rax+rdx+0x18]
test r8, r8
je pd_candidate_done
mov qword ptr [rsp+0xA8], r8
mov rax, qword ptr [r8+0x480]
test rax, rax
je pd_candidate_done
mov ecx, dword ptr [rax+8]
test ecx, ecx
je pd_candidate_done
cmp ecx, 65536
ja pd_candidate_done
mov r8, qword ptr [rax+0x10]
test r8, r8
je pd_candidate_done
mov eax, 0x5168A21
xor edx, edx
div ecx
mov eax, ecx
pd_candidate_clip_loop:
cmp dword ptr [r8+rdx*8], 44000
je pd_candidate_clip_found
cmp dword ptr [r8+rdx*8], -1
je pd_candidate_done
dec eax
je pd_candidate_done
inc edx
cmp edx, ecx
jb pd_candidate_clip_loop
xor edx, edx
jmp pd_candidate_clip_loop
pd_candidate_clip_found:
mov eax, dword ptr [r8+rdx*8+4]
cmp eax, ecx
jae pd_candidate_done
mov r8, qword ptr [rsp+0xA8]
mov r8, qword ptr [r8+0x468]
test r8, r8
je pd_candidate_done
mov r8, qword ptr [r8+rax*8]
test r8, r8
je pd_candidate_done
cmp dword ptr [r8+0x1C], 0
jle pd_candidate_done
mov qword ptr [rsp+0x78], r8
mov r8, qword ptr [rsp+0x68]
movss xmm0, dword ptr [r10+0xF0]
subss xmm0, dword ptr [r8+0xF0]
mulss xmm0, xmm0
movss xmm1, dword ptr [r10+0xF4]
subss xmm1, dword ptr [r8+0xF4]
mulss xmm1, xmm1
addss xmm0, xmm1
movss xmm1, dword ptr [r10+0xF8]
subss xmm1, dword ptr [r8+0xF8]
mulss xmm1, xmm1
addss xmm0, xmm1
mov eax, 0x46AFC800
movd xmm1, eax
ucomiss xmm0, xmm1
jp pd_candidate_done
ja pd_candidate_done
mov rax, {data}
mov eax, dword ptr [rax+0x1C]
mov dword ptr [r11+8], eax
mov qword ptr [r11+0x10], r10
mov rax, qword ptr [r10]
mov qword ptr [r11+0x18], rax
mov qword ptr [r11+0x20], r9
mov rax, qword ptr [r10+0x240]
mov qword ptr [r11+0x28], rax
mov qword ptr [r11+0x30], r8
mov rax, qword ptr [r8]
mov qword ptr [r11+0x38], rax
mov rax, qword ptr [rsp+0x70]
mov qword ptr [r11+0x40], rax
mov rax, qword ptr [r8+0x240]
mov qword ptr [r11+0x48], rax
mov rax, qword ptr [rsp+0x90]
mov qword ptr [r11+0x50], rax
mov rax, qword ptr [rsp+0x98]
mov qword ptr [r11+0x58], rax
mov rax, qword ptr [rsp+0x78]
mov qword ptr [r11+0x60], rax
mov rax, qword ptr [rsp+0x80]
mov qword ptr [r11+0x68], rax
mov rax, qword ptr [rsp+0x88]
mov qword ptr [r11+0x70], rax
mov rax, qword ptr [rsp+0xA0]
mov qword ptr [r11+0x90], rax
mov eax, dword ptr [rsp+0xB0]
mov dword ptr [r11+0x98], eax
mov rax, qword ptr [rsp+0xA8]
mov qword ptr [r11+0xA0], rax
lock inc dword ptr [r11+0x7C]
mov rcx, r9
mov rdx, r8
xor r8d, r8d
mov rax, rsp
and rsp, -16
sub rsp, 0x30
mov qword ptr [rsp+0x20], rax
call {postdefeat_pair_candidate}
mov rsp, qword ptr [rsp+0x20]
test al, al
je pd_candidate_done
mov r11, {data}
add r11, 0xC00
mov r9, qword ptr [r11+0x20]
mov r8, qword ptr [r11+0x30]
cmp r8, qword ptr [r9+0x5B0]
jne pd_candidate_done
or qword ptr [r9+0x40], 0x400000
mov dword ptr [r11+0x78], 1
lock inc dword ptr [r11+0x80]
pd_candidate_done:
'''+RESTORE+'''mov eax, dword ptr [rcx+0x40]
shr rax, 0x16
jmp {return}
''')


def bound_pair(prefix, *, controller_context=True):
    code = current_source(prefix,bound=True)+f'''cmp dword ptr [r11+0x78], 1
je {prefix}_token_valid
cmp dword ptr [r11+0x78], 2
jne {prefix}_done
{prefix}_token_valid:
'''
    if controller_context:
        code += f'cmp r9, rsi\njne {prefix}_done\n'
    return (code+source_action(prefix,857,1101)+f'''mov r8, qword ptr [r9+0x5B0]
cmp r8, qword ptr [r11+0x30]
jne {prefix}_done
'''+target_owned(prefix,bound=True))


def damage_asm():
    return (SAVE+bound_pair('pd_damage')+'''lock inc dword ptr [r11+0x84]
'''+RESTORE+'''jmp {postdefeat_damage_skip}
pd_damage_done:
'''+RESTORE+'''mov r14, qword ptr [rsi+0x5B0]
jmp {return}
''')


def restore_asm():
    return (SAVE+current_source('pd_restore',bound=True)+'''
cmp dword ptr [r11+0x78], 1
jne pd_restore_done
cmp dword ptr [rsp+0xD8], 858
je pd_restore_done
mov rax, qword ptr [rsp+0xE0]
cmp rax, qword ptr [r11+0x40]
jne pd_restore_done
mov r8, qword ptr [rax+0x50]
cmp r8, qword ptr [r11+0x30]
jne pd_restore_done
'''+target_owned('pd_restore',bound=True)+'''
mov rax, qword ptr [rax+0x58]
cmp rax, qword ptr [r11+0x50]
jne pd_restore_done
test rax, rax
je pd_restore_done
cmp dword ptr [rax], 858
jne pd_restore_done
cmp byte ptr [rax+0x40], 1
jne pd_restore_done
mov rax, qword ptr [r11+0x68]
test rax, rax
je pd_restore_done
cmp dword ptr [rax], 3158
jne pd_restore_done
cmp byte ptr [rax+0x40], 1
jne pd_restore_done
mov rax, qword ptr [rax+0x20]
cmp rax, qword ptr [r11+0x70]
jne pd_restore_done
test rax, rax
je pd_restore_done
test qword ptr [rax+0x18], 0x20000000
jne pd_restore_done
mov qword ptr [rsp+0xD8], 3158
mov qword ptr [rsp+0xD0], 0
mov dword ptr [r11+0x78], 2
lock inc dword ptr [r11+0x88]
pd_restore_done:
'''+RESTORE+'''mov rax, rsp
push rdi
push r12
jmp {return}
''')


def heal_asm():
    return (SAVE+bound_pair('pd_heal')+'''
mov rax, qword ptr [r10+0x230]
cmp rax, qword ptr [rsp+0xE0]
jne pd_heal_done
lock inc dword ptr [r11+0xB0]
'''+RESTORE+'''jmp {return}
pd_heal_done:
'''+RESTORE+'''call {postdefeat_native_recovery}
jmp {return}
''')


def heal_script_asm():
    return (SAVE+bound_pair('pd_heal_script',controller_context=False)+'''
mov rax, qword ptr [r11+0x28]
add rax, 0x10
cmp rax, qword ptr [rsp+0xE0]
jne pd_heal_script_done
lock inc dword ptr [r11+0xB0]
'''+RESTORE+'''jmp {return}
pd_heal_script_done:
'''+RESTORE+'''call {postdefeat_script_recovery}
jmp {return}
''')


def addon(previous_profile):
    """Append five isolated code slots without moving the frozen Beta5 data."""
    if (previous_profile.get('tool_version') != '0.58-experimental'
            or len(previous_profile['hooks']) != 50
            or (previous_profile.get('allocation_size'),previous_profile.get('data_offset'))
            != (0x14000,0xF000)):
        raise ValueError('Post-defeat pairing requires the complete frozen Beta5 profile')
    plan=deepcopy(previous_profile)
    definitions=(
        ('HE_PostDefeatCandidate',0x738B6D,'8B 41 40 48 C1 E8 16',candidate_asm),
        ('HE_PostDefeatDamage',0x717CAE,'4C 8B B6 B0 05 00 00',damage_asm),
        ('HE_PostDefeatRestore',0x70ECE0,'48 8B C4 57 41 54',restore_asm),
        ('HE_PostDefeatHealEvent',0x70B180,'E8 FB 5F 02 00',heal_asm),
        ('HE_PostDefeatHealScript',0x6EF439,'E8 72 56 0C 00',heal_script_asm))
    plan['targets'].update(TARGETS)
    for i,(name,rva,original,builder) in enumerate(definitions):
        plan['hooks'].append(dict(name=name,rva=rva,original=original,
            length=len(bytes.fromhex(original)),code_offset=0x14000+i*0x1000,
            code_capacity=0x1000,asm=builder(),
            purpose='Native-referenced defeated Yuki-Onna visual pairing, scoped damage/healing suppression and pose restoration'))
    plan.update(allocation_size=0x19000,postdefeat_grab_revision=1,
                postdefeat_grab_state_offset=STATE_OFFSET,
                postdefeat_grab_state_size=STATE_SIZE,
                postdefeat_grab_target_template=0x28EEC,
                postdefeat_grab_original_action=3158,
                postdefeat_grab_visual_only=True)
    return plan
