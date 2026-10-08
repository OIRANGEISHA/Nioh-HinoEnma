"""Keep the current Boss player during template-wide script enemy cleanup.

Load::UnloadCharacter resolves a template and calls 8B1800. That routine
removes every matching actor, kind4 child and model dependency. A Boss player
shares an enemy template, so instance1 must be protected in this one script
call. Scene teardown, foreign actors, missing ownership and unloaded players
retain the full native cleanup. Only four new private counters may be written.
"""
from copy import deepcopy


EXPECTED_SLOTS = (
    (45, 'HE_SameTemplateUnloadChild', 0x8B1874, 7, 0x10000, 0x800),
    (46, 'HE_SameTemplateUnloadActor', 0x8B18C9, 11, 0x10800, 0x800),
    (47, 'HE_SameTemplateUnloadWorldActor', 0x8B1955, 8, 0x11000, 0x800),
    (48, 'HE_SameTemplateUnloadResources', 0x8B1A10, 5, 0x11800, 0x800),
)
ORIGINAL_BYTES = (
    '39 30 74 1E 48 8B 01',
    '39 31 75 26 48 8B 81 40 02 00 00',
    '39 30 75 09 48 8D 4F 20',
    'E8 0B FF 6D 00',
)
UNLOAD_TARGETS = {
    'same_template_script_return': 0x89C0AD,
    'same_template_object_match': 0x8B1896,
    'same_template_actor_next': 0x8B18F3,
    'same_template_world_next': 0x8B1962,
    'same_template_resource_release': 0xF91920,
    'same_template_unload_epilogue': 0x8B1C1E,
}
NATIVE_SIGNATURE_SPANS = (
    ('same_template_script_call', 0x89C09D, 0x10),
    ('same_template_unload_prologue', 0x8B1800, 0x17),
    ('same_template_child_owner_layout', 0x8B1861, 0x13),
    ('same_template_child_native_remove', 0x8B187B, 0x2A),
    ('same_template_actor_native_remove', 0x8B18D4, 0x1F),
    ('same_template_actor_tree_next', 0x8B18F3, 0x56),
    ('same_template_world_actor_load', 0x8B1949, 0xC),
    ('same_template_world_actor_remove', 0x8B195D, 5),
    ('same_template_resource_release_setup', 0x8B19E9, 0x27),
    ('same_template_resource_dependency_cleanup', 0x8B1A15, 0x46),
    ('same_template_unload_epilogue', 0x8B1C1E, 0xB),
)

# The native function has five pushes (28) and a 40-byte frame. Every hook
# arrives at that same stack depth. These five extra pushes put the original
# caller return at90; no calls, SSE instructions or native writes are added.
_SAVE = '''pushfq
push rax
push rdx
push r10
push r11
'''
_RESTORE = '''pop r11
pop r10
pop rdx
pop rax
popfq
'''
_GUARD = '''mov rax, {same_template_script_return}
cmp qword ptr [rsp+0x90], rax
jne unload_SUFFIX_native
mov r11, {data}
mov r10, qword ptr [r11+0x10]
test r10, r10
je unload_SUFFIX_native
mov rax, {player_slot}
cmp qword ptr [rax], r10
jne unload_SUFFIX_native
cmp dword ptr [r10+4], 0x10000
jne unload_SUFFIX_native
mov edx, dword ptr [r10]
cmp edx, 0x58E5E
je unload_SUFFIX_template
cmp edx, 0x51BE1
jne unload_SUFFIX_native
unload_SUFFIX_template:
cmp edx, esi
jne unload_SUFFIX_native
mov eax, dword ptr [r11]
cmp eax, 0x58E5E
je unload_SUFFIX_selected
cmp eax, 0x51BE1
jne unload_SUFFIX_native
unload_SUFFIX_selected:
cmp edx, dword ptr [r11+4]
jne unload_SUFFIX_native
cmp dword ptr [r10+0xEF0], 0
jne unload_SUFFIX_native
mov rax, qword ptr [r10+0xE90]
test rax, rax
je unload_SUFFIX_native
cmp dword ptr [rax], edx
jne unload_SUFFIX_native
cmp dword ptr [rax+0x0C], 1
jne unload_SUFFIX_native
mov rdx, qword ptr [r10+0x240]
test rdx, rdx
je unload_SUFFIX_native
cmp qword ptr [rdx], r10
jne unload_SUFFIX_native
cmp qword ptr [rdx+0x108], r10
jne unload_SUFFIX_native
cmp qword ptr [rdx+0x20], 0
jle unload_SUFFIX_native
mov rdx, qword ptr [r10+0x230]
test rdx, rdx
je unload_SUFFIX_native
cmp qword ptr [rdx], r10
jne unload_SUFFIX_native
mov rdx, qword ptr [rdx+8]
test rdx, rdx
je unload_SUFFIX_native
cmp qword ptr [rdx+0x50], r10
jne unload_SUFFIX_native
'''


def _asm(suffix, extra, protected, original):
    counter = {'child': 0x4000, 'actor': 0x4004, 'world': 0x4008, 'resources': 0x400C}[suffix]
    observe = 'mov r11, {data}\nlock inc dword ptr [r11+0x%X]\n' % counter
    return (_SAVE + _GUARD + extra + observe + _RESTORE + protected
            + 'unload_SUFFIX_native:\n' + _RESTORE + original).replace('SUFFIX', suffix)


CHILD_ASM = _asm('child', '''cmp qword ptr [rsp+0x18], r10
jne unload_SUFFIX_native
test r9, r9
je unload_SUFFIX_native
cmp word ptr [r9+4], 4
jne unload_SUFFIX_native
cmp qword ptr [r9+0x200], r10
jne unload_SUFFIX_native
''', '''cmp dword ptr [rax], esi
mov rax, qword ptr [rcx]
jmp {return}
''', '''cmp dword ptr [rax], esi
je {same_template_object_match}
mov rax, qword ptr [rcx]
jmp {return}
''')

ACTOR_ASM = _asm('actor', '''cmp rcx, r10
jne unload_SUFFIX_native
''', '''cmp dword ptr [rcx], esi
jmp {same_template_actor_next}
''', '''cmp dword ptr [rcx], esi
jne {same_template_actor_next}
mov rax, qword ptr [rcx+0x240]
jmp {return}
''')

WORLD_ACTOR_ASM = _asm('world', '''cmp qword ptr [rsp+0x18], r10
jne unload_SUFFIX_native
''', '''cmp dword ptr [rax], esi
jmp {same_template_world_next}
''', '''cmp dword ptr [rax], esi
jne {same_template_world_next}
lea rcx, [rdi+0x20]
jmp {return}
''')

RESOURCES_ASM = _asm('resources', '', '''jmp {same_template_unload_epilogue}
''', '''call {same_template_resource_release}
jmp {return}
''')


def apply_same_template_unload(previous_profile):
    """Pure0.45→0.46; preserve all original45 hook dictionaries and payloads."""
    if previous_profile.get('tool_version') != '0.45' or len(previous_profile['hooks']) != 45:
        raise ValueError('Same-template protection requires complete verified v0.45')
    if previous_profile.get('allocation_size') != 0x10000 or previous_profile.get('data_offset') != 0xF000:
        raise ValueError('Unexpected private allocation/data layout')
    plan = deepcopy(previous_profile)
    for row, original, asm, purpose in zip(EXPECTED_SLOTS, ORIGINAL_BYTES,
            (CHILD_ASM, ACTOR_ASM, WORLD_ACTOR_ASM, RESOURCES_ASM), (
                'Keep current-player-owned kind4 children while script removes enemy children',
                'Keep the exact current Boss player while the native actor tree removes enemies',
                'Keep world140 only when it is the exact current Boss player',
                'Keep current Boss model/dependency resources through the complete native epilogue')):
        index, name, rva, length, offset, capacity = row
        if index != len(plan['hooks']):
            raise ValueError('Unexpected new unload hook ordering')
        plan['hooks'].append(dict(name=name, rva=rva, length=length,
            code_offset=offset, code_capacity=capacity, original=original,
            asm=asm, purpose=purpose))
    plan['targets'].update(UNLOAD_TARGETS)
    plan.update(tool_version='0.46', stage='scoped_same_template_script_unload',
        allocation_size=0x14000, same_template_unload_revision=1,
        same_template_unload_added_hook_indices=[45, 46, 47, 48],
        same_template_unload_script_return=0x89C0AD,
        same_template_unload_private_counter_offsets=[0x4000, 0x4004, 0x4008, 0x400C],
        same_template_unload_native_data_writes=False,
        same_template_unload_requires_fresh_allocation=True,
        same_template_unload_gameplay_confirmation_pending=True)
    return plan
