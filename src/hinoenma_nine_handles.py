"""Match the native DWORD resource ID, excluding its untouched alignment pad.

LivingWeapon+60 is a 32-bit ID (7B609D / 7B6765), cleared with a DWORD
write at 7B60BD. +64 is alignment padding, not part of that ID. +68 remains
the native 64-bit attachment pointer. No native state or padding is changed.
The NOP preserves every payload length and relative target of the old hook.
"""
from hinoenma_guardian_combat import guardian_combat_hooks


def guardian_handle_width_hooks():
    hooks = guardian_combat_hooks()
    first = dict(hooks[0])
    old = 'cmp qword ptr [rdx+0x110], 0\n'
    if first['asm'].count(old) != 2:
        raise ValueError('Native attachment resource-ID guards changed')
    first['asm'] = first['asm'].replace(old, 'nop\ncmp dword ptr [rdx+0x110], 0\n')
    first['purpose'] += '; read native resource ID as DWORD, ignoring alignment padding; attachment pointer remains QWORD'
    return [first, *hooks[1:]]
