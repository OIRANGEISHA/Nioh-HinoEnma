"""Pure portable map preview: frozen display hooks plus durable camera scope.

No process or game file is opened. New scratch starts zero. Only the already
validated, exact revision4 constructor route publishes a dynamic binding;
the camera requires its completed native owner/ticket and current actor/body.
The two scalar values live in code and private saved stack, not launcher data.
"""
from __future__ import annotations

from copy import deepcopy
import re

import menu_preview_rev4_integration as frozen
import menu_preview_camera_rev2_hooks as distance
import menu_preview_camera_height_hooks as height

BASE_VERSION = frozen.BASE_VERSION
VERSION = '1.0.0-beta.5.3'
CORE_DATA_OFFSET = frozen.CORE_DATA_OFFSET
CODE_OFFSET, SCRATCH_OFFSET = frozen.CODE_OFFSET, frozen.SCRATCH_OFFSET
APPEARANCE_CODE_OFFSET = frozen.APPEARANCE_CODE_OFFSET
APPEARANCE_SCRATCH_OFFSET = frozen.APPEARANCE_SCRATCH_OFFSET
CAMERA_CODE_OFFSET, HEIGHT_CODE_OFFSET, CAMERA_SCRATCH_OFFSET = 0x2A000, 0x2B000, 0x2C000
ALLOCATION_SIZE, CAMERA_SCRATCH_SIZE = 0x2D000, 0x54
PROTECTED_DATA_PAGES = frozen.PROTECTED_DATA_PAGES + ((CAMERA_SCRATCH_OFFSET, ALLOCATION_SIZE),)
CANONICAL_MODULE, CANONICAL_ALLOCATION = frozen.CANONICAL_MODULE, frozen.CANONICAL_ALLOCATION
wrapper_continuation_offset = frozen.wrapper_continuation_offset
SCOPE = dict(selected=0x10, expected_completion=0x14, owner=0x18,
    actor=0x20, body=0x28, valid=0x34, generation=0x38, lock=0x3C,
    visual_swaps=0x4C, visual_restores=0x50)
CAMERA_HOOKS = ((distance.HOOK_NAME,distance.HOOK_RVA,distance.ORIGINAL,CAMERA_CODE_OFFSET),
    (height.HOOK_NAME,height.HOOK_RVA,height.ORIGINAL,HEIGHT_CODE_OFFSET))
TARGET_RVAS = dict(distance.TARGET_RVAS, **{k:v for k,v in height.TARGET_RVAS.items()
    if k not in distance.TARGET_RVAS})
POINTER_LOAD = re.compile(r'(?m)^mov (r(?:ax|cx|dx|[89]|1[01])), '
    r'\{(data|production_data|visual_data|appearance_data|camera_data|camera_scope|wrapper_continuation)\}$')
PRIVATE_POINTER = re.compile(r'\{(data|production_data|visual_data|appearance_data|camera_data|camera_scope|wrapper_continuation)\}')


def _once(source, old, new):
    if source.count(old)!=1:
        raise ValueError('Frozen portable source boundary changed')
    return source.replace(old,new)


def _invalidate_source():
    # The surrounding frozen guard already proves BaseMode/state0/slot-null.
    # No global lifetime state or saved native property is modified.
    return '''mov r11, {camera_scope}
cmp dword ptr [r11+0x34], 0
je portable_camera_invalidate_done
xor eax, eax
mov ecx, 1
lock cmpxchg dword ptr [r11+0x3C], ecx
jne portable_camera_invalidate_done
mov dword ptr [r11+0x34], 0
add dword ptr [r11+0x38], 2
mov dword ptr [r11+0x3C], 0
portable_camera_invalidate_done:
'''


def ready_source():
    source=frozen.ready_asm()
    boundary='mov rax, {player_slot}\ncmp qword ptr [rax], 0\njne preload_probe_done\n'
    return _once(source,boundary,boundary+_invalidate_source())


def _capture_source():
    # Only the surrounding [savedSP+A0]==1 exact constructor route reaches
    # this block. Its post-native-lookup recheck validated all four locals.
    # The completion expectation is1; actual constructor-time epoch is0.
    return '''mov r11, {camera_scope}
xor eax, eax
mov ecx, 1
lock cmpxchg dword ptr [r11+0x3C], ecx
jne portable_camera_capture_done
mov dword ptr [r11+0x34], 0
inc dword ptr [r11+0x38]
mov eax, dword ptr [rsp+0x88]
mov dword ptr [r11+0x10], eax
mov dword ptr [r11+0x14], 1
mov rax, qword ptr [rsp+0x98]
mov qword ptr [r11+0x18], rax
mov rax, qword ptr [rsp+0x90]
mov qword ptr [r11+0x20], rax
mov rax, qword ptr [rsp+0x80]
mov qword ptr [r11+0x28], rax
mov r10, {visual_data}
mov eax, dword ptr [r10+0x2C]
mov dword ptr [r11+0x4C], eax
mov eax, dword ptr [r10+0x30]
mov dword ptr [r11+0x50], eax
inc dword ptr [r11+0x38]
mov dword ptr [r11+0x34], 1
mov dword ptr [r11+0x3C], 0
portable_camera_capture_done:
'''


def appearance_source():
    source=frozen.appearance_asm()
    boundary='inc dword ptr [r11+0x3C]\nappearance_success_counted:\n'
    return _once(source,boundary,'inc dword ptr [r11+0x3C]\n'+_capture_source()+'appearance_success_counted:\n')


def _scope_guard(*, recheck=False):
    source='''mov r11, {data}
cmp dword ptr [r11+0x34], 1
jne camera_native
cmp dword ptr [r11+0x3C], 0
jne camera_native
mov eax, dword ptr [r11+0x38]
test eax, eax
je camera_native
test al, 1
jne camera_native
'''
    source+=('cmp dword ptr [rsp+0x20], eax\njne camera_native\n' if recheck
        else 'mov dword ptr [rsp+0x20], eax\n')
    source+='''mov r10, {visual_data}
mov eax, dword ptr [r10+0x2C]
cmp dword ptr [r11+0x4C], eax
jne camera_native
mov eax, dword ptr [r10+0x30]
cmp dword ptr [r11+0x50], eax
jne camera_native
'''
    return source


def camera_source(*, raised=False):
    scalar, output = ('0xC2340000','xmm6') if raised else ('0x44390000','xmm2')
    entry, overrides, fallbacks = (0x40,0x44,0x48) if raised else (0,4,8)
    source=f'''pushfq
push rax
push rcx
push rdx
push r8
push r9
push r10
push r11
sub rsp, 0x30
mov r11, {{data}}
inc dword ptr [r11+{hex(entry)}]
'''
    caller=height._caller_guard().replace('[rsp+0x98]','[rsp+0xA8]') if raised else ''
    scale='''mov eax, dword ptr [rdi+0x160]
test eax, eax
jle camera_native
cmp eax, 0x7F800000
jae camera_native
''' if raised else ''
    source+=caller+_scope_guard()+distance._guard()+scale+_scope_guard(recheck=True)
    source+='camera_recheck:\n'+caller+distance._guard(recheck=True)+scale+_scope_guard(recheck=True)
    constant='{native_height}' if raised else '{native_distance}'
    source+=f'''mov r11, {{data}}
inc dword ptr [r11+{hex(overrides)}]
mov dword ptr [rsp], {scalar}
movss {output}, dword ptr [rsp]
jmp camera_restore
camera_native:
mov r11, {{data}}
inc dword ptr [r11+{hex(fallbacks)}]
mov r11, {constant}
movss {output}, dword ptr [r11]
camera_restore:
add rsp, 0x30
pop r11
pop r10
pop r9
pop r8
pop rdx
pop rcx
pop rax
popfq
jmp {{return}}
'''
    # Rename labels, not the native target placeholders such as {camera_vtable}.
    return re.sub(r'(?<!\{)\bcamera_', 'portable_height_' if raised else 'portable_distance_',source)


def _bind(source, scratch_offset, continuation_delta):
    matches=list(POINTER_LOAD.finditer(source))
    if len(matches)!=len(PRIVATE_POINTER.findall(source)):
        raise ValueError('Private relocation load syntax differs')
    deltas=dict(data=scratch_offset-CORE_DATA_OFFSET,production_data=0,
        visual_data=SCRATCH_OFFSET-CORE_DATA_OFFSET,
        appearance_data=APPEARANCE_SCRATCH_OFFSET-CORE_DATA_OFFSET,
        camera_data=CAMERA_SCRATCH_OFFSET-CORE_DATA_OFFSET,
        camera_scope=CAMERA_SCRATCH_OFFSET-CORE_DATA_OFFSET,
        wrapper_continuation=continuation_delta)
    def bind(match):
        register,token=match.groups()
        return f'mov {register}, {{data}}'+(f'\nadd {register}, {hex(deltas[token])}' if deltas[token] else '')
    return POINTER_LOAD.sub(bind,source)


def _sources(continuation_delta):
    raw=(ready_source(),frozen.spawn_asm(),frozen.ctor_asm(),frozen.restore_asm(),
        appearance_source(),frozen.idle_asm(),frozen.idle_selection_asm(),frozen.loadout_appearance_asm(),
        camera_source(),camera_source(raised=True))
    offsets=(SCRATCH_OFFSET,)*4+(APPEARANCE_SCRATCH_OFFSET,)*4+(CAMERA_SCRATCH_OFFSET,)*2
    return tuple(_bind(source,offset,continuation_delta) for source,offset in zip(raw,offsets))


def validate_layout(plan):
    if (len(plan.get('hooks',()))!=70 or plan.get('data_offset')!=CORE_DATA_OFFSET
            or plan.get('allocation_size')!=ALLOCATION_SIZE
            or plan.get('menu_camera_scope_offset')!=CAMERA_SCRATCH_OFFSET
            or plan.get('menu_camera_scope_size')!=CAMERA_SCRATCH_SIZE
            or plan.get('menu_camera_dynamic_binding') is not True
            or plan.get('menu_camera_distance')!=740.0 or plan.get('menu_camera_height')!=-45.0
            or tuple(map(tuple,plan.get('protected_data_pages',())))!=PROTECTED_DATA_PAGES):
        raise ValueError('Portable70 layout or scope differs')
    entries=[(name,rva,original,base+offset,0x1000) for group,base in (
        (frozen.HOOKS,CODE_OFFSET),(frozen.APPEARANCE_HOOKS,APPEARANCE_CODE_OFFSET))
        for name,rva,original,offset in group]
    entries+=[(name,rva,original,offset,0x1000) for name,rva,original,offset in CAMERA_HOOKS]
    tail=plan['hooks'][-10:]
    if [(h['name'],h['rva'],h['original'],h['code_offset'],h['code_capacity']) for h in tail]!=entries:
        raise ValueError('Exact ten scoped menu entries required')
    names,sites,codes=set(),[],[]
    for hook in plan['hooks']:
        if hook['name'] in names:raise ValueError('Duplicate hook name')
        names.add(hook['name'])
        if hook['length']!=len(bytes.fromhex(hook['original'])) or hook['length']<5:
            raise ValueError('Native overwrite length differs')
        start,end=hook['code_offset'],hook['code_offset']+hook.get('code_capacity',0x400)
        if start<0 or end>ALLOCATION_SIZE or end<=start or any(max(start,a)<min(end,b) for a,b in PROTECTED_DATA_PAGES):
            raise ValueError('Code/data protection range differs')
        codes.append((start,end));sites.append((hook['rva'],hook['rva']+hook['length']))
    for spans in (codes,sites):
        spans.sort()
        if any(a[1]>b[0] for a,b in zip(spans,spans[1:])):raise ValueError('Overlapping hook ranges')
    continuation=wrapper_continuation_offset(plan,CANONICAL_MODULE,CANONICAL_ALLOCATION)
    delta=continuation-CORE_DATA_OFFSET
    if (plan.get('menu_visual_wrapper_continuation_offset')!=continuation
            or plan.get('menu_visual_core_relative_continuation_delta')!=delta
            or tuple(h['asm'] for h in tail)!=_sources(delta)):
        raise ValueError('Portable source or resolved continuation differs')
    for name,rva in TARGET_RVAS.items():
        if plan['targets'].get(name)!=rva:raise ValueError('Camera native target differs')


def apply_menu_preview(previous):
    plan=frozen.apply_menu_preview(previous)
    # Existing68 source is copied, never changed. Only its two verified
    # saved-register boundaries gain private lifetime bookkeeping here.
    for name,rva in TARGET_RVAS.items():
        if name in plan['targets'] and plan['targets'][name]!=rva:
            raise ValueError('Conflicting camera native target')
        plan['targets'][name]=rva
    delta=plan['menu_visual_core_relative_continuation_delta']
    sources=_sources(delta)
    for hook,source in zip(plan['hooks'][-8:],sources[:8]):hook['asm']=source
    for (name,rva,original,offset),source in zip(CAMERA_HOOKS,sources[8:]):
        plan['hooks'].append(dict(name=name,rva=rva,original=original,length=8,
            code_offset=offset,code_capacity=0x1000,asm=source,
            purpose='Completed dynamic Hino map preview camera740/height−45'))
    plan.update(tool_version=VERSION,allocation_size=ALLOCATION_SIZE,
        protected_data_pages=[list(page) for page in PROTECTED_DATA_PAGES],
        menu_camera_revision=1,menu_camera_dynamic_binding=True,
        menu_camera_scope_offset=CAMERA_SCRATCH_OFFSET,menu_camera_scope_size=CAMERA_SCRATCH_SIZE,
        menu_camera_scope_fields=dict(SCOPE),menu_camera_distance=740.0,menu_camera_height=-45.0,
        menu_camera_scalar_initializers_required=False,
        menu_camera_native_constants_memory_movss=True,
        menu_camera_constructor_capture_only=True,menu_camera_generation_checked=True,
        menu_renderer_validation_pending=False,menu_framing_validation_pending=False,
        menu_camera_fresh_exe_enable_validation_pending=True,
        stage='public_beta53_menu_preview')
    if plan['hooks'][:60]!=previous['hooks']:raise ValueError('Frozen public60 hooks changed')
    validate_layout(plan)
    return plan


def ct_compatible_plan(plan):
    validate_layout(plan)
    result=deepcopy(plan)
    for hook in result['hooks']:
        hook['asm']='\n'.join(line if line.lstrip().startswith('.byte ') else
            frozen.SOURCE_NUMBER.sub(lambda m:hex(int(m.group(0),16 if m.group(0).lower().startswith('0x') else 10)),line)
            for line in hook['asm'].split('\n'))
    return result


def native_signatures(code=None):
    from menu_preview_visual_hooks import native_signatures as visual_signatures
    from menu_preview_appearance_rev4_hooks import native_signatures as appearance_signatures
    if code is None:
        from code_inspect import CodeImage
        code=CodeImage()
    rows=visual_signatures(code)+appearance_signatures(code)+distance.native_signatures(code)+height.native_signatures(code)
    return list({(row['rva'],row['length']):row for row in rows}.values())
