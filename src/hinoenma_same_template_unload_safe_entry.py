"""Move the child hook away from an original NULL-parent branch destination.

The v0.46 span8B1874..187B covered the originalJE1872→1878 entry.
Hook the complete LEA at1868 instead, leaving TEST/JE/CMP/MOV all intact.
All other v0.46 hooks and the entire original v0.45 profile remain unchanged.
"""
from copy import deepcopy

from hinoenma_same_template_unload import (
    EXPECTED_SLOTS as PREVIOUS_SLOTS, NATIVE_SIGNATURE_SPANS as PREVIOUS_SPANS,
    _asm)


EXPECTED_SLOTS = (
    (45, 'HE_SameTemplateUnloadChild', 0x8B1868, 7, 0x10000, 0x800),
) + PREVIOUS_SLOTS[1:]
SAFE_CHILD_ORIGINAL = '4C 8D 89 20 FF FF FF'
NATIVE_SIGNATURE_SPANS = tuple(
    (name, rva, 7 if name=='same_template_child_owner_layout' else size)
    for name,rva,size in PREVIOUS_SPANS
) + (
    ('same_template_safe_child_original_test_and_branch', 0x8B186F, 5),
    ('same_template_safe_child_original_compare_and_next_link', 0x8B1874, 7),
)

# LEA is replayed before saving, so R9 has exactly its original native value.
# Rejection returns to the untouched TEST(parent), including NULL→1878.
# Success replays the original matching CMP before jumping to that same MOV.
SAFE_CHILD_ASM = '''lea r9, [rcx-0xE0]
''' + _asm('child', '''cmp qword ptr [rsp+0x18], r10
jne unload_SUFFIX_native
test r9, r9
je unload_SUFFIX_native
cmp word ptr [r9+4], 4
jne unload_SUFFIX_native
cmp qword ptr [r9+0x200], r10
jne unload_SUFFIX_native
''', '''cmp dword ptr [rax], esi
jmp {same_template_object_next}
''', '''jmp {return}
''')


def apply_safe_entry(previous_profile):
    """Pure0.46→0.47; only the first new child site/payload is replaced."""
    if previous_profile.get('tool_version') != '0.46' or len(previous_profile['hooks']) != 49:
        raise ValueError('Safe child entry requires the complete frozen v0.46 profile')
    if (previous_profile.get('allocation_size'),previous_profile.get('data_offset')) != (0x14000,0xF000):
        raise ValueError('Unexpected expanded allocation/data layout')
    for index,name,rva,length,offset,capacity in PREVIOUS_SLOTS:
        hook=previous_profile['hooks'][index]
        if (hook['name'],hook['rva'],hook['length'],hook['code_offset'],hook['code_capacity']) != (name,rva,length,offset,capacity):
            raise ValueError('Unexpected frozen unload hook layout')
    plan=deepcopy(previous_profile)
    child=plan['hooks'][45]
    child.update(rva=0x8B1868, length=7, original=SAFE_CHILD_ORIGINAL,
        asm=SAFE_CHILD_ASM,
        purpose='Protect current-player-owned kind4 children without covering the native NULL-parent branch destination')
    plan['targets']['same_template_object_next']=0x8B1878
    plan.update(tool_version='0.47', stage='scoped_same_template_script_unload_safe_entry',
        same_template_unload_revision=2,
        same_template_unload_child_safe_entry=True,
        same_template_unload_child_preserved_internal_entry=0x8B1878,
        same_template_unload_gameplay_confirmation_pending=True)
    return plan
