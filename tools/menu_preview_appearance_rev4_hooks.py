"""Private revision4: also suppress the exact in-construction body fallback.

The native actor reset initializes its max/current parameter while the
private spawner stack frame still exists. That invokes the gear binder
before global slot registration. This route is accepted only when all five
native return slots and the restored visual frame bind the exact map actor.
Completed map paths keep the frozen revision3 global player-slot guards.
"""
from __future__ import annotations

import menu_preview_appearance_rev3_hooks as frozen
from menu_preview_preload_hooks import _pointer

ALLOCATION_SIZE, DATA_OFFSET = frozen.ALLOCATION_SIZE, frozen.DATA_OFFSET
HOOK_RVA, ORIGINAL = frozen.HOOK_RVA, frozen.ORIGINAL
IDLE_RVA, IDLE_ORIGINAL = frozen.IDLE_RVA, frozen.IDLE_ORIGINAL
IDLE_SELECT_RVA, IDLE_SELECT_ORIGINAL = frozen.IDLE_SELECT_RVA, frozen.IDLE_SELECT_ORIGINAL
LOADOUT_RVA, LOADOUT_ORIGINAL = frozen.LOADOUT_RVA, frozen.LOADOUT_ORIGINAL
HOOKS = frozen.HOOKS
TARGET_RVAS = dict(frozen.TARGET_RVAS, reset_parameter_return=0x76A0B1,
    actor_reset_return=0x761071)
CONSTRUCTION_SUPPRESSED_OFFSET, OWN_DATA_SIZE = 0x3C, 0x40
GEAR_SAVE_SIZE, NATIVE_CONSTRUCTION_FRAME_OFFSET = 0xF0, 0x330
ADDITIONAL_NATIVE_SPANS = ((0x7698E0, 0x1F), (0x76A08C, 0x25),
    (0x761067, 0xB), (0x7B57C0, 0xF), (0x7608A8, 0x8D))
NATIVE_SPANS = frozen.NATIVE_SPANS + ADDITIONAL_NATIVE_SPANS


def _scope_call():
    return '''lea r11, [rsp]
call appearance_ctor_scope
test eax, eax
je appearance_done
'''


def _construction_scope():
    """Pure internal checker. R11 is the saved gear stack base; no native calls.

The internal CALL's eight-byte return slot does not affect these offsets.
No per-call context is placed in global scratch. RDX is restored from the
caller's saved actor local; nonvolatile registers and XMMs are untouched.
"""
    source = 'appearance_ctor_scope:\n'
    for offset,target in ((0x238,'initial_parameter_return'),(0x268,'reset_parameter_return'),
            (0x2D8,'actor_reset_return'),(0x3A8,'ctor_return'),(0x418,'wrapper_continuation')):
        source += f'''mov rax, {{{target}}}
cmp qword ptr [r11+0x{offset:X}], rax
jne appearance_ctor_reject
'''
    source += '''lea r9, [r11+0x420]
lea rax, [r9-0xCF]
cmp qword ptr [r11+0x2D0], rax
jne appearance_ctor_reject
cmp dword ptr [r9+0x20], 3
jne appearance_ctor_reject
mov rdx, qword ptr [r11+0x90]
cmp qword ptr [r9+0x38], rdx
jne appearance_ctor_reject
cmp dword ptr [rdx], 100
jne appearance_ctor_reject
cmp dword ptr [rdx+4], 0x10000
jne appearance_ctor_reject
cmp byte ptr [rdx+0x434], 0
jne appearance_ctor_reject
cmp byte ptr [rdx+0x435], 0
jne appearance_ctor_reject
mov rax, qword ptr [r9+0x40]
'''
    source += _pointer('rax','appearance_ctor_reject')+'''cmp rax, qword ptr [r9+0x30]
je appearance_ctor_reject
mov rax, qword ptr [r9+0x28]
'''
    source += _pointer('rax','appearance_ctor_reject')+'''mov rcx, {base_mode_vtable}
cmp qword ptr [rax], rcx
jne appearance_ctor_reject
cmp dword ptr [rax+0x1C], 0
jne appearance_ctor_reject
mov rcx, {visual_data}
cmp qword ptr [rcx], rax
jne appearance_ctor_reject
mov ecx, dword ptr [r11+0x88]
cmp dword ptr [r9+0x48], ecx
jne appearance_ctor_reject
mov rax, {production_data}
cmp dword ptr [rax], ecx
jne appearance_ctor_reject
mov r8, qword ptr [r9+0x30]
'''
    source += _pointer('r8','appearance_ctor_reject')+'''cmp byte ptr [r8+0x160], 0
je appearance_ctor_reject
mov r8, qword ptr [r8+8]
'''
    source += _pointer('r8','appearance_ctor_reject')+'''mov rax, qword ptr [rdx+0x18]
'''
    source += _pointer('rax','appearance_ctor_reject')+'''cmp qword ptr [rax], rdx
jne appearance_ctor_reject
cmp qword ptr [rax+0x188], r8
jne appearance_ctor_reject
mov eax, 1
ret
appearance_ctor_reject:
xor eax, eax
ret
'''
    return source


def appearance_asm():
    source = frozen.appearance_asm()
    source = source.replace('sub rsp, 0xA0','sub rsp, 0xB0')
    source = source.replace('add rsp, 0xA0','add rsp, 0xB0')
    source = source.replace('[rsp+0x228]','[rsp+0x238]').replace('[rsp+0x258]','[rsp+0x268]')
    source = source.replace('mov dword ptr [rsp+0x8C], 0\n',
        'mov dword ptr [rsp+0x8C], 0\nmov dword ptr [rsp+0xA0], 0\n',1)
    slot = '''mov rax, {player_slot}
cmp qword ptr [rax], rdx
jne appearance_done
'''
    if source.count(slot)!=2:
        raise ValueError('Frozen two global slot guards changed')
    source = source.replace(slot,'',1)
    route = '''mov rax, {initial_parameter_return}
cmp qword ptr [rsp+0x238], rax
jne appearance_registered_route
mov rax, {reset_parameter_return}
cmp qword ptr [rsp+0x268], rax
jne appearance_registered_route
'''+_scope_call()+'''mov dword ptr [rsp+0xA0], 1
jmp appearance_route_ready
appearance_registered_route:
'''+slot+'''appearance_route_ready:
'''
    source = source.replace('mov dword ptr [rsp+0x88], eax\n',
        'mov dword ptr [rsp+0x88], eax\n'+route,1)
    for suffix in ('','_recheck'):
        ready = 'appearance_owner_recheck' if suffix else 'appearance_owner_ready'
        old = f'appearance_initial{suffix}:\nmov rcx, {{initial_stats_return}}\n'
        new = f'''appearance_initial{suffix}:
cmp dword ptr [rsp+0xA0], 1
jne appearance_registered_initial{suffix}
'''+_scope_call()+f'''mov r11, {{visual_data}}
mov rax, qword ptr [r11]
jmp {ready}
appearance_registered_initial{suffix}:
mov rcx, {{initial_stats_return}}
'''
        if source.count(old)!=1:
            raise ValueError('Frozen initial gear ticket boundary changed')
        source = source.replace(old,new)
    checked_slot = '''cmp dword ptr [rsp+0xA0], 1
jne appearance_registered_recheck
'''+_scope_call()+'''jmp appearance_registration_rechecked
appearance_registered_recheck:
'''+slot+'''appearance_registration_rechecked:
'''
    post_slot='mov rdx, qword ptr [rsp+0x90]\n'+slot
    if source.count(post_slot)!=1:
        raise ValueError('Frozen post-lookup actor registration boundary changed')
    source = source.replace(post_slot,'mov rdx, qword ptr [rsp+0x90]\n'+checked_slot,1)
    # The route includes its own slot check; target only the post-lookup one.
    if source.count('appearance_registered_recheck:')!=1:
        raise ValueError('Expected exactly one post-lookup registration guard')
    handle = '''cmp byte ptr [rax+0x160], 0
je appearance_done
mov rax, qword ptr [rax+8]
'''
    bound_handle = '''cmp byte ptr [rax+0x160], 0
je appearance_done
cmp dword ptr [rsp+0xA0], 1
jne appearance_handle_ready
cmp qword ptr [rsp+0x450], rax
jne appearance_done
appearance_handle_ready:
mov rax, qword ptr [rax+8]
'''
    if source.count(handle)!=1:
        raise ValueError('Frozen ready handle guard changed')
    source = source.replace(handle,bound_handle)
    source = source.replace('mov dword ptr [rsp+0x8C], 1\n',
        '''cmp dword ptr [rsp+0xA0], 1
jne appearance_success_counted
inc dword ptr [r11+0x3C]
appearance_success_counted:
mov dword ptr [rsp+0x8C], 1
''',1)
    return source+_construction_scope()


def build_plan(base: int, production_data: int, visual_data: int, allocation: int) -> dict:
    plan = frozen.build_plan(base,production_data,visual_data,allocation)
    plan['tool_version']='menu-appearance-private-4'
    plan['targets']=dict(plan['targets'],**TARGET_RVAS)
    plan['hooks'][0]['asm']=appearance_asm()
    plan['hooks'][0]['purpose']='Suppress exact primary map constructor and registered map body binders'
    plan['constructor_suppressed_offset']=CONSTRUCTION_SUPPRESSED_OFFSET
    plan['own_data_size']=OWN_DATA_SIZE
    plan['construction_scope']=dict(phase=3,native_frame_offset=0x330,
        native_returns=[0x7B4C10,0x76A0B1,0x761071,0x75525E],
        private_wrapper_continuation=plan['wrapper_continuation'],
        saved_return_offsets=[0x238,0x268,0x2D8,0x3A8,0x418],
        saved_ctor_rbp_offset=0x2D0,gear_save_size=GEAR_SAVE_SIZE,
        global_player_ignored_only_in_exact_live_constructor=True)
    return plan


def native_signatures(code=None):
    if code is None:
        from code_inspect import CodeImage
        code=CodeImage()
    signatures=frozen.native_signatures(code)
    for rva,length in ADDITIONAL_NATIVE_SPANS:
        at=code.file_offset(rva)
        signatures.append(dict(rva=rva,length=length,
            original=bytes(code.data[at:at+length]).hex()))
    return signatures
