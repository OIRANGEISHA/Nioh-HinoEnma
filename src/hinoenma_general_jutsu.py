"""Native action-family dispatch for items, ninjutsu and Onmyo.

An item is obtained through the game's own definition lookup. Its native
category selects a verified common-bank action; its own effects and spawn
template are retained. No inventory, spell effect, damage or save is edited.
The separately tested teleport/death/weapon-familiarity paths stay intact.
"""
from copy import deepcopy
import hashlib
import json
import struct

from source_assembler import Ks, KS_ARCH_X86, KS_MODE_64
from hinoenma_special_item_actions import (_once, _schedules,
    SCHEDULE_HEX as SPECIAL_SCHEDULES, EVENT_GUARDS as SPECIAL_GUARDS)
import hinoenma_wind_weakness_dragon as spells
import hinoenma_nine_talismans as nine
import hinoenma_item_hurt_lookup as hurt
from hinoenma_general_jutsu_data import FAMILIES, NEW_SCHEDULES as ADDITIONAL_SCHEDULES, NEW_EVENT_GUARDS as ADDITIONAL_GUARDS

# These two already validated families originally lived in a different helper.
NEW_SCHEDULES = {**ADDITIONAL_SCHEDULES, **{a:SPECIAL_SCHEDULES[a] for a in (982,610)}}
NEW_EVENT_GUARDS = {**ADDITIONAL_GUARDS, **{a:SPECIAL_GUARDS[a] for a in (982,610)}}

PARENT_SHA256 = 'dd9da4fbfba3e0217b6eec5b66d797eddda37e370999b2b69d8aa17ccafdaa52'
GUARD_CARRIER = 'HE_MapPreviewCameraHeightPrivate'
GUARD_OFFSET = 0x2B600
SCHEDULE_CARRIER = 'HE_MapPreviewCameraDistancePrivate'
SCHEDULE_OFFSET = 0x2A600
DEFINITION_FIELDS = (0, 0x104, 0x10C, 0x114, 0x11C)


def digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def definition_guard():
    """RAX=game definition, RDI=controller; R10/R11=action/motion or zero.

Only RCX, R10, R11 and flags are scratch. Different IDs, native effects and
templates within a family are intentional. Caller snapshots the full routing
fields and compares them again after every resource callback.
"""
    s = '''general_jutsu_definition:
xor r10d, r10d
xor r11d, r11d
mov ecx, dword ptr [rdi+0x548]
test ecx, ecx
js general_jutsu_definition_no
cmp dword ptr [rax], ecx
jne general_jutsu_definition_no
mov ecx, dword ptr [rdi+0x54C]
cmp dword ptr [rax+0x10C], ecx
jne general_jutsu_definition_no
cmp byte ptr [rdi+0x570], 0
jne general_jutsu_definition_no
'''
    for off in (0x110, 0x114, 0x118):
        s += f'cmp dword ptr [rax+{off}], 0xFFFF\nja general_jutsu_definition_no\n'
    s += 'cmp dword ptr [rax+0x11C], 0xFFFFF\nja general_jutsu_definition_no\n'
    for cat in FAMILIES:
        s += f'cmp ecx, {cat}\nje general_jutsu_family_{cat}\n'
    s += 'jmp general_jutsu_definition_no\n'
    for cat, row in FAMILIES.items():
        action, motion, contracts = row
        s += f'general_jutsu_family_{cat}:\n'
        for i, (kind, flags) in enumerate(contracts):
            s += f'''cmp word ptr [rax+4], {kind}
jne general_jutsu_contract_{cat}_{i}
cmp dword ptr [rax+0x104], {flags}
je general_jutsu_family_ok_{cat}
general_jutsu_contract_{cat}_{i}:
'''
        s += 'jmp general_jutsu_definition_no\n'
        s += f'general_jutsu_family_ok_{cat}:\nmov r10d, {action}\nmov r11d, {motion}\nret\n'
    return s + 'general_jutsu_definition_no:\nxor r10d, r10d\nxor r11d, r11d\nret\n'


def snapshot(local, failure=None):
    s = ''
    for i, off in enumerate(DEFINITION_FIELDS):
        width = 'dword' if off == 0x11C else 'qword'
        reg = 'ecx' if width == 'dword' else 'rcx'
        s += f'mov {reg}, {width} ptr [rax+{off}]\n'
        if failure:
            s += f'cmp {width} ptr [rsp+{local+i*8}], {reg}\njne {failure}\n'
        else:
            s += f'mov {width} ptr [rsp+{local+i*8}], {reg}\n'
    return s


def entry_definition(prefix, local):
    return f'''mov dword ptr [rsp+0xA4], 0
call {{data}} + {GUARD_OFFSET-0xF000}
test r10d, r10d
je general_jutsu_{prefix}_legacy
mov dword ptr [rsp+0xA4], 1
mov dword ptr [rsp+0x94], r10d
mov dword ptr [rsp+0x98], r11d
''' + snapshot(local) + f'''jmp {prefix}_definition_done
general_jutsu_{prefix}_legacy:
'''


def post_definition(prefix, local, success):
    return f'''cmp dword ptr [rsp+0xA4], 1
jne general_jutsu_{prefix}_post_legacy
mov rax, qword ptr [rsp+0xC8]
''' + snapshot(local, prefix+'_restore') + f'''call {{data}} + {GUARD_OFFSET-0xF000}
cmp r10d, dword ptr [rsp+0x94]
jne {prefix}_restore
cmp r11d, dword ptr [rsp+0x98]
jne {prefix}_restore
jmp {success}
general_jutsu_{prefix}_post_legacy:
'''


def schedule_asm():
    s = 'general_jutsu_schedule_entry:\n'
    for action in NEW_SCHEDULES:
        s += f'cmp edx, {action}\nje general_jutsu_new_schedule\n'
    s += f'jmp {{data}} + {nine.SCHEDULE_OFFSET-0xF000}\ngeneral_jutsu_new_schedule:\n'
    return s + _schedules(NEW_SCHEDULES, NEW_EVENT_GUARDS).replace('special_item_', 'general_jutsu_')


def apply_general_jutsu(parent):
    if digest(parent) != PARENT_SHA256:
        raise ValueError('Exact published Beta6.1.3 required')
    plan = deepcopy(parent)
    hooks = {h['name']: h for h in plan['hooks']}
    ks = Ks(KS_ARCH_X86, KS_MODE_64)

    def encode(text, h, off):
        v = {k: 0x140000000 + r for k, r in plan['targets'].items()}
        v.update(data=0x144000000+plan['data_offset'], **{'return': 0x140000000+h['rva']+h['length']})
        return bytes(ks.asm(text.format(**v), 0x144000000+off)[0])

    def append(name, offset, text):
        h = hooks[name]
        before = encode(h['asm'], h, h['code_offset'])
        padding = offset-h['code_offset']-len(before)
        if padding < 0:
            raise ValueError('Occupied helper space: '+name)
        h['asm'] += '\n'+'nop\n'*padding+text
        after = encode(h['asm'], h, h['code_offset'])
        if not after.startswith(before):
            raise ValueError('Carrier prefix changed: '+name)

    append(GUARD_CARRIER, GUARD_OFFSET, definition_guard())
    append(SCHEDULE_CARRIER, SCHEDULE_OFFSET, schedule_asm())
    carrier = hooks[spells.CARRIER_NAME]
    prefix, rest = carrier['asm'].split('dung_fan_helper:')
    helper, rest = ('dung_fan_helper:'+rest).split('arrow_sloth_lookup_entry:')
    lookup, tail = ('arrow_sloth_lookup_entry:'+rest).split(spells.EXTRA_GUARD_ASM)

    def unpad(text):
        text = text.rstrip()+'\n'
        while text.endswith('nop\n'):
            text = text[:-4]
        return text.rstrip()+'\n'

    helper, lookup = unpad(helper), unpad(lookup)
    # Preserve all existing locals and ABI alignment; the extra space stores
    # the variable definition fields for the post-callback identity check.
    helper = _once(helper, 'sub rsp, 0xE8\n', 'sub rsp, 0x118\n')
    helper = _once(helper, 'add rsp, 0xE8\n', 'add rsp, 0x118\n')
    anchor = 'mov qword ptr [rsp+0xC8], rax\n'
    helper = _once(helper, anchor, anchor+entry_definition('dung_fan', 0xE8))
    helper = _once(helper, 'cmp dword ptr [rdi+0x548], 26116\nje wind_weakness_dragon_post_26116\n',
        post_definition('dung_fan', 0xE8, 'wind_weakness_dragon_post_resources')+
        'cmp dword ptr [rdi+0x548], 26116\nje wind_weakness_dragon_post_26116\n')
    helper = _once(helper, f'dung_fan_schedule:\njmp {{data}} + {nine.SCHEDULE_OFFSET-0xF000}\n',
        f'dung_fan_schedule:\njmp {{data}} + {SCHEDULE_OFFSET-0xF000}\n')

    actions = dict((r[0], r[1]) for r in FAMILIES.values())
    start = lookup.index('cmp edx, 3025\n')
    end = lookup.index('arrow_sloth_lookup_role:\n', start)
    lookup = lookup[:start]+''.join(f'cmp edx, {a}\nje arrow_sloth_lookup_role\n' for a in sorted({3025, *actions}))+\
        'jmp arrow_sloth_lookup_restore\n'+lookup[end:]
    lookup = _once(lookup, anchor, anchor+entry_definition('arrow_sloth_lookup', 0x128))
    lookup = _once(lookup, 'cmp dword ptr [rdi+0x548], 64367\nje arrow_sloth_lookup_post_definition_64367\n',
        post_definition('arrow_sloth_lookup', 0x128, 'arrow_sloth_lookup_success')+
        'cmp dword ptr [rdi+0x548], 64367\nje arrow_sloth_lookup_post_definition_64367\n')
    motion_check = ''
    for a, motion in actions.items():
        motion_check += f'cmp ecx, {a}\nje general_jutsu_lookup_motion_{a}\n'
    motion_check += 'jmp arrow_sloth_lookup_restore\n'
    for a, motion in actions.items():
        motion_check += f'general_jutsu_lookup_motion_{a}:\nmov ecx, {motion}\njmp general_jutsu_lookup_motion_ready\n'
    motion_check += 'general_jutsu_lookup_motion_ready:\n'
    lookup = _once(lookup, 'add ecx, 69\n', motion_check)
    # The same common schedule resolver now covers every admitted family.
    lookup = lookup[:lookup.index('arrow_sloth_lookup_schedule:')]+\
        f'arrow_sloth_lookup_schedule:\njmp {{data}} + {SCHEDULE_OFFSET-0xF000}\n'
    # Positive alternate90111 is verified as a timing resource by the existing
    # Wind helper, rather than treated as a body animation clip.
    old_alt = 'cmp dword ptr [rax+0x34], -1\njne arrow_sloth_lookup_restore\n'
    if lookup.count(old_alt) != 2:
        raise ValueError('Unexpected lookup alternate checks')
    for suffix in ('pre', 'post'):
        lookup = lookup.replace(old_alt, f'''mov ecx, -1
cmp dword ptr [rsp+0x94], 1165
jne general_jutsu_alternate_{suffix}
mov ecx, 90111
general_jutsu_alternate_{suffix}:
cmp dword ptr [rax+0x34], ecx
jne arrow_sloth_lookup_restore
''', 1)
    lookup = _once(lookup, 'call {data} + 0x3E00\ntest al, al\nje arrow_sloth_lookup_restore\n', '''call {data} + 0x3E00
test al, al
je arrow_sloth_lookup_restore
cmp dword ptr [rsp+0x94], 1165
jne general_jutsu_lookup_aux_done
mov rcx, rdi
mov edx, 1165
mov r8, qword ptr [rsp+0x80]
mov r9, qword ptr [rsp+0xD0]
call {data} + 0x58C00
test al, al
je arrow_sloth_lookup_restore
general_jutsu_lookup_aux_done:
''')
    hs = len(encode(helper, carrier, spells.HELPER_OFFSET))
    ls = len(encode(lookup, carrier, spells.LOOKUP_OFFSET))
    if hs > 0x1800 or ls > 0x1400:
        raise ValueError(f'Fixed helper capacity exhausted: {hs:x}/{ls:x}')
    carrier['asm'] = prefix+helper+'\n'+'nop\n'*(0x1800-hs)+lookup+'\n'+'nop\n'*(0x1400-ls)+spells.EXTRA_GUARD_ASM+tail

    # The skipped first event recovery is tied to a verified native family,
    # not an individual talisman. The complete player/epoch/event schedule and
    # exactly-once marker checks surrounding this guard are unchanged.
    g = hooks[nine.GUARD_CARRIER]
    for action, cat in ((42, 9), (611, 23), (1165, 25)):
        anchor = f'nine_talismans_gap_{action}:\n'
        g['asm'] = _once(g['asm'], anchor, anchor+f'''cmp dword ptr [rcx+0x548], 0
jl nine_talismans_gap_no
cmp dword ptr [rcx+0x54C], {cat}
je nine_talismans_gap_match_{action}
''')

    # Suppress Boss-key remapping for every admitted common item animation.
    previous_actions = set(hurt.CAST_MOTIONS) | {611}
    added = [(a, m) for a, m in actions.items() if a not in previous_actions]
    for name, suffix in (('HE_InputA', 'a'), ('HE_InputB', 'b')):
        h = hooks[name]
        anchor = f'pop rcx\njmp signpost_input_continue_{suffix}\n'
        extra = ''.join(f'mov ecx, {m}\ncmp dword ptr [rdx], {a}\nje special_item_input_found_{suffix}\n' for a, m in added)
        h['asm'] = _once(h['asm'], anchor, extra+anchor)
    # Injury routing selects native common reactions for the new action
    # families too; never reinterpret a human hurt ID as a Boss ability.
    table = hooks[hurt.DATA_CARRIER]
    old_table = hurt.TABLE_BYTES+struct.pack('<2i96s', 611, 110, bytes.fromhex(nine.AREA_SCHEDULE))
    new_table = old_table+b''.join(struct.pack('<2i96s', a, m, bytes.fromhex(NEW_SCHEDULES[a])) for a, m in added)
    table['asm'] = _once(table['asm'], '.byte '+','.join(map(str, old_table))+'\n', '.byte '+','.join(map(str, new_table))+'\n')
    count = len(hurt.CAST_ROWS)+1
    h = hooks[hurt.CODE_CARRIER]
    h['asm'] = _once(h['asm'], f'mov ecx, {count}\nitem_hurt_cast_scan:\n', f'mov ecx, {count+len(added)}\nitem_hurt_cast_scan:\n')

    changed = []
    for h, old in zip(plan['hooks'], parent['hooks']):
        if h['asm'] == old['asm']:
            continue
        changed.append(h['name'])
        raw = encode(h['asm'], h, h['code_offset'])
        if len(raw) > h['code_capacity']:
            raise ValueError(f"Capacity exceeded: {h['name']} {len(raw):x}/{h['code_capacity']:x}")
    plan['general_jutsu_candidate'] = dict(revision=1, categories=sorted(FAMILIES),
        actions=sorted(actions), changed_hooks=changed, native_item_definition_drives_effect=True,
        direct_item_inventory_save_writes=False, player_only=True,
        native_injury_and_recast_protection=True, live_confirmation_pending=True)
    if digest(parent) != PARENT_SHA256:
        raise ValueError('Parent mutated')
    return plan
