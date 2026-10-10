"""Regenerate the frozen Steam payload without proprietary game files."""
from __future__ import annotations

import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hinoenma_hooks import BLOCK_SIZE, EXPERIMENTAL_HOOKS, TARGETS
from hinoenma_attributes import ATTRIBUTE_TARGETS
from hinoenma_weapon_view import compatible_weapon_hooks, HUD_HOOK, HUD_REFRESH_HOOKS
from hinoenma_revenant import PLAYER_REVENANT_INTERACTION
from hinoenma_grab import GRAB_TARGETS, automatic_grab_hook
from hinoenma_locks import skill_locks_hook
from hinoenma_spirit_stone import spirit_stones_hook
from hinoenma_tutorial import TUTORIAL_HOOKS, TUTORIAL_TARGETS
from hinoenma_tutorial_defense_hint import DEFENSE_HINT_GUARD, DEFENSE_HINT_TARGETS
from hinoenma_tutorial_ki_pulse import KI_PULSE_HINT_SPACE, KI_PULSE_TARGETS
from hinoenma_purification import PURIFICATION_TARGETS
from hinoenma_manual_purification import manual_purification_hooks
from hinoenma_tutorial_weapon import weapon_hint_hook, WEAPON_HINT_TARGETS
from hinoenma_tutorial_shot import shot_hint_hook, SHOT_HINT_TARGETS
from hinoenma_roar_key import roar_key_hook
from hinoenma_tutorial_living_weapon import living_weapon_hint_hook, LIVING_WEAPON_HINT_TARGETS
from hinoenma_living_weapon import LIVING_WEAPON_TARGETS
from hinoenma_guardian_spirit import GUARDIAN_TARGETS
from hinoenma_guardian_combat import GUARDIAN_COMBAT_TARGETS
from hinoenma_nine_handles import guardian_handle_width_hooks
from hinoenma_ladder import queued_ladder_hook, common_ladder_lookup_hook, LADDER_TARGETS
from hinoenma_talisman_items import apply_talisman_items
from hinoenma_element_eligibility import apply_element_eligibility
from hinoenma_projectile_elements import apply_projectile_elements
from hinoenma_grab_elements import apply_grab_elements
from hinoenma_projectile_intrinsic import apply_projectile_intrinsic_protection
from hinoenma_guardian_recovery import apply_guardian_recovery
from hinoenma_hp_growth import apply_hp_growth
from hinoenma_combat_growth import apply_combat_growth
from hinoenma_hot_spring import apply_hot_spring
from hinoenma_signpost import apply_signpost
from hinoenma_same_template_unload import apply_same_template_unload
from hinoenma_same_template_unload_safe_entry import apply_safe_entry
from hinoenma_latched_door import apply_latched_door
from hinoenma_talk import apply_talk
from hinoenma_rescue import apply_rescue
from hinoenma_latched_door_instances import apply_latched_door_instances
from hinoenma_special_items import apply_special_items
from hinoenma_salt_isolation import apply_salt_isolation
from hinoenma_salt_event_catchup import apply_salt_event_catchup
from hinoenma_salt_hurt_compatibility import apply_salt_hurt_compatibility
from hinoenma_salt_damage96_draft import apply_salt_damage96_draft
from hinoenma_salt_damage205_draft import apply_salt_damage205_draft, ROUTES_OFFSET, ROUTE_BYTES
from hinoenma_postdefeat_grab import addon as apply_postdefeat_grab
from hinoenma_ladder_scale import apply_ladder_scale
from hinoenma_inherent_element import apply_inherent_elements, BASE_VERSION, PROTECTED_DATA_PAGES
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

BASE = 0x140000000
ALLOCATION = 0x144000000
IDENTIFIER = r'[A-Za-z_][A-Za-z0-9_]*'
LABEL_DEFINITION = re.compile(r'(?m)^\s*(' + IDENTIFIER + r'):')
LABEL_DECLARATION = re.compile(r'(?m)^label\((' + IDENTIFIER + r')\)$')


def baseline_specs() -> tuple[list[dict], dict]:
    """Reconstruct the original 40-hook source basis without game files."""
    specs = [skill_locks_hook() if item["name"] == "HE_Consumables" else item
             for item in EXPERIMENTAL_HOOKS]
    specs = [spirit_stones_hook(item) if item["name"] == "HE_Consumables" else item
             for item in specs]
    specs += compatible_weapon_hooks() + [HUD_HOOK]
    specs += list(HUD_REFRESH_HOOKS) + [PLAYER_REVENANT_INTERACTION, automatic_grab_hook()]
    specs += list(TUTORIAL_HOOKS) + [DEFENSE_HINT_GUARD, KI_PULSE_HINT_SPACE]
    specs += manual_purification_hooks()
    specs += [weapon_hint_hook(), shot_hint_hook(), roar_key_hook(), living_weapon_hint_hook()]
    specs += guardian_handle_width_hooks()
    specs = [queued_ladder_hook(item) if item["name"] == "HE_QueuedDoor" else item for item in specs]
    specs += [common_ladder_lookup_hook()]
    targets = dict(TARGETS)
    for extra in (ATTRIBUTE_TARGETS, GRAB_TARGETS, TUTORIAL_TARGETS, DEFENSE_HINT_TARGETS,
                  KI_PULSE_TARGETS, PURIFICATION_TARGETS, WEAPON_HINT_TARGETS, SHOT_HINT_TARGETS,
                  LIVING_WEAPON_HINT_TARGETS, GUARDIAN_COMBAT_TARGETS, GUARDIAN_TARGETS,
                  LIVING_WEAPON_TARGETS, LADDER_TARGETS):
        targets.update(extra)
    return specs, targets


def source_plan_v050(frozen: dict) -> dict:
    """Apply each pure revision to the public signatures and source basis.

    The small entry signatures in the frozen public profile are the only
    external input. No private verifier, process snapshot or game file is read.
    Source controls every ASM body, native target and code-slot layout.
    """
    specs, targets = baseline_specs()
    signatures = {hook['name']: hook for hook in frozen['hooks']}
    baseline = deepcopy(frozen)
    baseline.update(tool_version='0.35', allocation_size=0x10000, data_offset=0xF000,
                    targets=targets, hooks=[])
    offset = 0
    for source in specs:
        hook = deepcopy(source)
        original = signatures.get(hook['name'])
        if original is None or any(hook[key] != original[key] for key in ('rva', 'length')):
            raise ValueError('Public entry signature differs from source: ' + hook['name'])
        hook['original'] = original['original']
        hook['code_offset'] = hook.get('code_offset', offset)
        hook['code_capacity'] = hook.get('code_capacity', BLOCK_SIZE)
        if hook['code_offset'] < offset:
            raise ValueError('Original source code slots overlap')
        offset = hook['code_offset'] + hook['code_capacity']
        baseline['hooks'].append(hook)
    for apply_revision in (apply_talisman_items, apply_element_eligibility,
            apply_projectile_elements, apply_grab_elements,
            apply_projectile_intrinsic_protection, apply_guardian_recovery,
            apply_hp_growth, apply_combat_growth, apply_hot_spring, apply_signpost,
            apply_same_template_unload, apply_safe_entry, apply_latched_door,
            apply_talk, apply_rescue):
        baseline = apply_revision(baseline)
    if baseline['tool_version'] != '0.50' or len(baseline['hooks']) != 49:
        raise ValueError('Expected the complete 49-hook current source revision')
    return baseline


def source_plan_v051(frozen: dict) -> dict:
    """Preserve the complete public Beta 4.1 source as a regression basis."""
    plan = apply_latched_door_instances(source_plan_v050(frozen))
    if plan['tool_version'] != '0.51' or len(plan['hooks']) != 49:
        raise ValueError('Expected the complete 49-hook local 0.51 source revision')
    return plan


def source_plan_v058(frozen: dict) -> dict:
    """Rebuild Beta 5 from pure source and bounded public entry signatures.

    Native damage, input, item quantity and shared game resources stay native.
    Saved research records and private verifier modules are never imported.
    """
    items = apply_special_items(source_plan_v051(frozen))
    isolated = apply_salt_isolation(items)
    signatures = [h for h in frozen['hooks'] if h['name'] == 'HE_SaltEventCatchup']
    if len(signatures) != 1:
        raise ValueError('Exactly one public Salt scheduler entry signature required')
    hook = signatures[0]
    if (hook['rva'], hook['length'], hook['code_offset'], hook['code_capacity']) != (0x718950, 5, 0x1040, 0x3C0):
        raise ValueError('Public Salt scheduler entry shape differs')
    event = apply_salt_event_catchup(isolated, items, bytes.fromhex(hook['original']))
    rear = apply_salt_hurt_compatibility(event)
    front = apply_salt_damage96_draft(rear)
    plan = apply_salt_damage205_draft(front)
    if plan['tool_version'] != '0.58-experimental' or len(plan['hooks']) != 50:
        raise ValueError('Expected the complete 50-hook local 0.58 source revision')
    return plan


def source_plan_v059(frozen: dict) -> dict:
    """Integrate the bounded post-defeat visual pair into the frozen Beta 5 base."""
    plan = apply_postdefeat_grab(source_plan_v058(frozen))
    plan['tool_version'] = '0.59'
    if len(plan['hooks']) != 55:
        raise ValueError('Expected the complete 55-hook local 0.59 source revision')
    return plan


def source_plan_hotfix(frozen: dict) -> dict:
    """Append the tested ladder sampler repair without changing Beta 5.1 hooks."""
    previous = source_plan_v059(frozen)
    # Rebuild the exact former allocation before appending the four new slots.
    previous['allocation_size'] = 0x19000
    plan = apply_ladder_scale(previous)
    if len(plan['hooks']) != 59 or plan['hooks'][:55] != previous['hooks']:
        raise ValueError('Hotfix must preserve all 55 Beta 5.1 hooks')
    plan['tool_version'] = BASE_VERSION
    return plan


def source_plan_beta52(frozen: dict) -> dict:
    """Rebuild Beta 5.2 from the exact public Hotfix and innate-element revision."""
    plan = apply_inherent_elements(source_plan_hotfix(frozen))
    if len(plan['hooks']) != 60 or plan.get('inherent_element_revision') != 2:
        raise ValueError('Expected the complete reviewed 60-hook Beta 5.2 source')
    plan['tool_version'] = '1.0.0-beta.5.2'
    return plan


def source_plan(frozen: dict) -> dict:
    """Rebuild Beta 5.3.2 from the unchanged 60-hook gameplay basis."""
    from menu_preview_coldstart_portable import apply_menu_preview
    return apply_menu_preview(source_plan_beta52(frozen))


def legacy_plans(frozen: dict) -> list[dict]:
    """Exact older payloads are read-only identities, never migration inputs."""
    beta51 = source_plan_v059(frozen)
    beta51.update(tool_version='1.0.0-beta.5.1', allocation_size=0x19000)
    from menu_preview_portable_integration import apply_menu_preview as beta53
    from menu_preview_reload_portable import apply_menu_preview as beta531
    return [beta51, source_plan_hotfix(frozen), source_plan_beta52(frozen), beta53(source_plan_beta52(frozen)), beta531(source_plan_beta52(frozen))]


def validate_layout(plan: dict) -> None:
    if len(plan.get('hooks', ())) == 71:
        if plan.get('tool_version') == '1.0.0-beta.5.3.2':
            from menu_preview_coldstart_portable import validate_layout as validate_reload_layout
        else:
            from menu_preview_reload_portable import validate_layout as validate_reload_layout
        validate_reload_layout(plan)
        return
    if len(plan.get('hooks', ())) == 70:
        from menu_preview_portable_integration import validate_layout as validate_menu_layout
        validate_menu_layout(plan)
        return
    """Reject code capacity in core, paired-grab scratch, or innate-cache pages."""
    code_ranges = sorted((hook['code_offset'], hook['code_offset']
                          + hook.get('code_capacity', BLOCK_SIZE)) for hook in plan['hooks'])
    if (not code_ranges or code_ranges[0][0] < 0
            or any(left[1] > right[0] for left, right in zip(code_ranges, code_ranges[1:]))
            or code_ranges[-1][1] > plan['allocation_size']
            or (plan['data_offset'], plan['allocation_size']) != (0xF000, 0x20000)
            or plan.get('inherent_element_cache_offset') != 0x1F000
            or plan.get('inherent_element_cache_size') != 0x40
            or any(max(start, protected_start) < min(end, protected_end)
                   for start, end in code_ranges
                   for protected_start, protected_end in PROTECTED_DATA_PAGES)):
        raise ValueError('Code and protected data slots overlap')


def source_specs() -> tuple[list[dict], dict]:
    frozen = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
    plan = source_plan(frozen)
    return plan['hooks'], plan['targets']


def load_plan() -> dict:
    plan = json.loads((ROOT / "profiles/steam-1.24.8.json").read_text("utf-8"))
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    if plan["tool_version"] != version["version"]:
        raise ValueError("Manifest and release version differ")
    rebuilt = source_plan(plan)
    specs, targets = rebuilt['hooks'], rebuilt['targets']
    if len(specs) != len(plan["hooks"]):
        raise ValueError("Frozen hook list differs from source")
    if plan["targets"] != targets:
        raise ValueError("Frozen native targets differ from source")
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for frozen, source in zip(plan["hooks"], specs):
        for key in ("name", "rva", "length", "original"):
            if frozen[key] != source[key]:
                raise ValueError("Frozen hook specification differs: " + frozen["name"])
        source_offset = source['code_offset']
        if (frozen["code_offset"] != source_offset
                or frozen.get("code_capacity", BLOCK_SIZE) != source.get("code_capacity", BLOCK_SIZE)):
            raise ValueError("Frozen hook code slot differs")
        original = bytes.fromhex(frozen["original"])
        if len(original) != frozen["length"] or sum(i.size for i in md.disasm(original, BASE + frozen["rva"])) != len(original):
            raise ValueError("Frozen signature truncates a native instruction")
        frozen["asm"] = source["asm"]
    validate_layout(plan)
    native_ranges = sorted((hook["rva"], hook["rva"] + hook["length"]) for hook in plan["hooks"])
    if any(left[1] > right[0] for left, right in zip(native_ranges, native_ranges[1:])):
        raise ValueError("Native hook sites overlap")
    return plan


def assemble(plan: dict, module_base: int, allocation: int) -> list[dict]:
    assembler = Ks(KS_ARCH_X86, KS_MODE_64)
    result = []
    for hook in plan["hooks"]:
        site = module_base + hook["rva"]
        target = allocation + hook["code_offset"]
        values = {key: hex(module_base + rva) for key, rva in plan["targets"].items()}
        values.update(data=hex(allocation + plan["data_offset"]), **{"return": hex(site + hook["length"])})
        encoded, _ = assembler.asm(hook["asm"].format(**values), target)
        payload = bytes(encoded)
        if len(payload) > hook.get("code_capacity", BLOCK_SIZE):
            raise ValueError("Code slot capacity exceeded: " + hook["name"])
        delta = target - (site + 5)
        if not -(1 << 31) <= delta < (1 << 31):
            raise ValueError("Allocation outside rel32 range")
        patched = b"\xE9" + struct.pack("<i", delta) + b"\x90" * (hook["length"] - 5)
        result.append(dict(hook, site=site, target=target, payload=payload, patched=patched))
    return result


def relocation_specs(plan: dict) -> list[dict]:
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    md.detail = True
    result = []
    for hook in assemble(plan, BASE, ALLOCATION):
        fixups = []
        # The Salt source declares one fixed, unreachable 14-row WORD table.
        # Keep data out of instruction/relocation decoding; every byte still
        # participates in all compiled-payload and CT namespace comparisons.
        ranges = [(0, len(hook["payload"]))]
        if hook["name"] == "HE_Preload" and plan.get("salt_damage205_draft"):
            end = ROUTES_OFFSET + len(ROUTE_BYTES)
            if hook["payload"][ROUTES_OFFSET:end] != ROUTE_BYTES or end != len(hook["payload"]):
                raise ValueError("Salt route data interval differs from pure source")
            ranges = [(0, ROUTES_OFFSET)]
        decoded = []
        for start, end in ranges:
            instructions = list(md.disasm(hook["payload"][start:end], hook["target"] + start))
            if sum(i.size for i in instructions) != end - start:
                raise ValueError("Incomplete instruction payload disassembly: " + hook["name"])
            decoded.extend(instructions)
        for ins in decoded:
            for operand in ins.operands:
                if operand.type != CS_OP_IMM:
                    continue
                offset = ins.address - hook["target"] + ins.imm_offset
                if operand.imm == ALLOCATION + plan["data_offset"]:
                    if ins.imm_size != 8 or ins.mnemonic != "movabs":
                        raise ValueError("Unexpected data pointer encoding")
                    fixups.append(dict(offset=offset, kind=0, target=0, next=0))
                elif BASE <= operand.imm < BASE + plan["image_size"]:
                    if ins.imm_size == 8 and ins.mnemonic == "movabs":
                        fixups.append(dict(offset=offset, kind=2, target=operand.imm - BASE, next=0))
                        continue
                    if ins.imm_size != 4 or ins.mnemonic not in ("call", "jmp", "jne", "je"):
                        raise ValueError("Unexpected external branch encoding")
                    fixups.append(dict(offset=offset, kind=1, target=operand.imm - BASE,
                                       next=ins.address - hook["target"] + ins.size))
        result.append(dict(name=hook["name"], rva=hook["rva"], code_offset=hook["code_offset"],
                           original=hook["original"], template=base64.b64encode(hook["payload"]).decode(), fixups=fixups))
    return result


def generate(plan: dict) -> str:
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    lines = [
        f'// Generated from the {plan["tool_version"]} profile. Includes native Fragment, Kodama and classified self-consumable compatibility paths.',
        '// Character-change mechanism adapted from the user-provided Bryanyora CT.',
        'using System;', 'namespace HinoEnmaTool { internal static class Profile {',
        f'internal const string Sha256 = "{plan["disk_sha256"]}";',
        f'internal const int ImageSize = {plan["image_size"]};',
        f'internal const uint Timestamp = {int(plan["pe_timestamp_hex"],16)}U;',
        f'internal const int AllocationSize = {plan["allocation_size"]};',
        f'internal const int DataOffset = {plan["data_offset"]};',
        f'internal const string Version = "{plan["tool_version"]}";',
        f'internal const string DisplayVersion = "{version["display_version"]}";',
        'internal static readonly MemorySpan[] ProtectedDataPages = new MemorySpan[] {' +
            ','.join(f'new MemorySpan({start},{end})' for start, end in plan.get('protected_data_pages', PROTECTED_DATA_PAGES)) + '};',
    ]
    for constant, key in (("ManualPurification", "manual_purification"),
                          ("LivingWeapon", "actual_living_weapon_activation_added"),
                          ("YokaiGrab", "yokai_grab"),
                          ("AttributeOverlay", "attribute_overlay"), ("WeaponStatsOverlay", "weapon_stats_overlay"),
                          ("WeaponHudView", "weapon_hud_view"), ("WeaponHudRefreshView", "weapon_hud_refresh_view"),
                          ("RevenantInteraction", "revenant_interaction")):
        lines.append(f'internal const bool {constant} = {str(plan.get(key, False)).lower()};')
    lines += [
        'internal const uint PlayerSlotRva = 0x18A0490U;',
        'internal const uint LookupRva = 0x755DC0U;',
        'internal static readonly byte[] LookupBytes = Convert.FromBase64String("' + base64.b64encode(bytes.fromhex('83 F9 03 77 13 48 63 C1 48 8D 0D C1 A6 14 01 48 8D 04 40 48 8B 04 C1 C3')).decode() + '");',
        'internal static readonly HookSpec[] Hooks = new HookSpec[] {'
    ]
    for item in relocation_specs(plan):
        original = base64.b64encode(bytes.fromhex(item["original"])).decode()
        fixups = ','.join(f'new Fixup({f["offset"]},{f["kind"]},{f["target"]}U,{f["next"]})' for f in item["fixups"])
        capacity = next(hook.get('code_capacity', BLOCK_SIZE) for hook in plan['hooks']
                        if hook['name'] == item['name'])
        lines.append(f'new HookSpec("{item["name"]}",{item["rva"]}U,{item["code_offset"]},{capacity},"{original}","{item["template"]}",new Fixup[]{{{fixups}}}),')
    lines += ['};', 'internal static readonly LegacyProfile[] LegacyProfiles = new LegacyProfile[] {']
    for previous in legacy_plans(plan):
        lines.append(f'new LegacyProfile("{previous["tool_version"]}",{previous["data_offset"]},{previous["allocation_size"]},new HookSpec[] {{')
        for item in relocation_specs(previous):
            original = base64.b64encode(bytes.fromhex(item['original'])).decode()
            fixups = ','.join(f'new Fixup({f["offset"]},{f["kind"]},{f["target"]}U,{f["next"]})' for f in item['fixups'])
            capacity = next(hook.get('code_capacity', BLOCK_SIZE) for hook in previous['hooks']
                            if hook['name'] == item['name'])
            lines.append(f'new HookSpec("{item["name"]}",{item["rva"]}U,{item["code_offset"]},{capacity},"{original}","{item["template"]}",new Fixup[]{{{fixups}}}),')
        lines.append('}),')
    return '\n'.join(lines + ['};', '} }']) + '\n'


def ct_render_plan(plan: dict) -> tuple[dict, list[str]]:
    """Give all source labels a unique CT-wide namespace, including digits."""
    rendered = deepcopy(plan)
    local_labels = []
    for hook in rendered['hooks']:
        labels = LABEL_DEFINITION.findall(hook['asm'])
        if len(labels) != len({label.casefold() for label in labels}):
            raise ValueError('Duplicate local label in ' + hook['name'])
        mapping = {label: 'ct_' + hook['name'].lower() + '_' + label for label in labels}
        if mapping:
            pattern = re.compile(r'\b(' + '|'.join(re.escape(label) for label in mapping) + r')\b')
            hook['asm'] = pattern.sub(lambda match: mapping[match.group(0)], hook['asm'])
        local_labels.extend(mapping.values())
    if len(local_labels) != len({label.casefold() for label in local_labels}):
        raise ValueError('Duplicate CT local label')
    return rendered, local_labels


def validate_ct_labels(source: str, local_labels: list[str]) -> None:
    definitions = LABEL_DEFINITION.findall(source)
    declarations = LABEL_DECLARATION.findall(source)
    for names in (definitions, declarations):
        if len(names) != len({name.casefold() for name in names}):
            raise ValueError('Duplicate CT label definition or declaration')
    if (not set(local_labels) <= set(definitions)
            or not set(local_labels) <= set(declarations)
            or not set(declarations) <= set(definitions)):
        raise ValueError('CT labels are not all defined and declared')


def aa_source(plan: dict) -> str:
    from menu_preview_coldstart_portable import ct_compatible_plan
    # The standalone source tests also exercise an explicitly converted plan.
    # Accept only the exact conversion of the reconstructed source profile;
    # never infer numeric semantics from arbitrary modified assembly text.
    try:
        validate_layout(plan)
    except ValueError:
        if len(plan['hooks']) == 71 and plan.get('tool_version') == '1.0.0-beta.5.3.1':
            from menu_preview_reload_portable import apply_menu_preview as beta531
            canonical = beta531(source_plan_beta52(plan))
        else:
            canonical = source_plan(plan) if len(plan['hooks'])==71 else __import__('menu_preview_portable_integration').apply_menu_preview(source_plan_beta52(plan))
        if plan != ct_compatible_plan(canonical):
            raise ValueError('Expected raw source or exact CT numeric conversion')
        plan = canonical
    plan, local_labels = ct_render_plan(ct_compatible_plan(plan))
    checks = [
        "[ENABLE]", "{$lua}", "if syntaxcheck then return end",
        'if getAddressSafe("HE_Prototype_Code") then error("飞缘魔测试版已启用。") end',
        'local module',
        'for _, item in pairs(enumModules()) do if item.Name:lower()=="nioh.exe" then module=item end end',
        'if not module then error("请先选择 nioh.exe 进程。") end',
        f'if getModuleSize("nioh.exe")~={plan["image_size"]} then error("游戏模块与测试版不匹配。") end',
        f'if md5file(module.PathToFile):lower()~="{plan["disk_md5"]}" then error("本表只适配已核对的 Steam 1.24.8 程序。") end',
        '_G.HE_Prototype_PID=getOpenedProcessID()',
        "{$asm}",
    ]
    for hook in plan["hooks"]:
        checks.append(f'assert(nioh.exe+{hook["rva"]:X},{hook["original"]})')
    checks += [
        f'alloc(HE_Prototype_Code,{plan["allocation_size"]:X},nioh.exe+89B424)',
        'define(HE_Prototype_Data,HE_Prototype_Code+F000)',
        'registersymbol(HE_Prototype_Code)', 'registersymbol(HE_Prototype_Data)',
    ]
    for hook in plan["hooks"]:
        checks += [f'label({hook["name"]})', f'registersymbol({hook["name"]})']
    checks += [f"label({label})" for label in local_labels]
    for hook in plan["hooks"]:
        values = {key: f"nioh.exe+{rva:X}" for key, rva in plan["targets"].items()}
        values.update(data="HE_Prototype_Data", **{"return": f'nioh.exe+{hook["rva"]+hook["length"]:X}'})
        source = re.sub(r"0x([0-9A-Fa-f]+)", r"\1", hook["asm"].format(**values))
        source = re.sub(r"(?m)^\.byte ([0-9,]+)$", lambda m: "db " +
                        " ".join(f"{int(x):02X}" for x in m.group(1).split(",")), source)
        checks += [f'HE_Prototype_Code+{hook["code_offset"]:X}:', f'{hook["name"]}:', source]
    checks += ['HE_Prototype_Data:', 'dd 00058E5E', 'dd 00000000',
               'HE_Prototype_Data+28:', f'db 00 00 {plan.get("initial_interaction_mode", 1):02X}']
    if plan.get('attribute_overlay'):
        checks += ['HE_Prototype_Data+58:', 'db 01']
    for hook in plan["hooks"]:
        checks += [f'nioh.exe+{hook["rva"]:X}:', f'jmp {hook["name"]}']
        if hook["length"] > 5:
            checks.append('db ' + ' '.join(['90'] * (hook["length"] - 5)))
    checks += ["[DISABLE]", "{$lua}", "if syntaxcheck then return end",
               'if _G.HE_Prototype_PID~=getOpenedProcessID() then error("游戏进程已变化，请重新打开测试表。") end']
    # Refuse to restore over another table's edits. Allocations remain until process exit,
    # so a game thread already inside a hook cannot jump into freed memory.
    for hook in plan["hooks"]:
        checks += [
            f'local site=getAddress("nioh.exe+{hook["rva"]:X}")',
            'local bytes=readBytes(site,5,true)',
            f'if not bytes or bytes[1]~=0xE9 then error("{hook["name"]} 已被其他脚本改动。") end',
            'local delta=bytes[2]+bytes[3]*256+bytes[4]*65536+bytes[5]*16777216',
            'if delta>=2147483648 then delta=delta-4294967296 end',
            f'if site+5+delta~=getAddress("{hook["name"]}") then error("跳转目标已变化，停止恢复。") end',
        ]
    checks += ["{$asm}"]
    for hook in plan["hooks"]:
        checks += [f'nioh.exe+{hook["rva"]:X}:', f'db {hook["original"]}', f'unregistersymbol({hook["name"]})']
    checks += ['unregistersymbol(HE_Prototype_Data)', 'unregistersymbol(HE_Prototype_Code)',
               '// Prototype allocations are reclaimed when nioh.exe exits.']
    result = "\n".join(checks) + "\n"
    validate_ct_labels(result, local_labels)
    return result


def ct_source(plan: dict, display_version: str) -> str:
    """Build the current guarded CT from the same pure hooks as the EXE."""
    experimental_interactions = True
    doc = ET.Element("CheatTable", CheatEngineTableVersion="45")
    entries = ET.SubElement(doc, "CheatEntries")
    item = ET.SubElement(entries, "CheatEntry")
    ET.SubElement(item, "ID").text = "1000"
    title = f"飞缘魔 {display_version}：在标题菜单启用"
    ET.SubElement(item, "Description").text = f'"{title}"'
    ET.SubElement(item, "Options", moHideChildren="1", moDeactivateChildrenAsWell="1")
    ET.SubElement(item, "VariableType").text = "Auto Assembler Script"
    ET.SubElement(item, "AssemblerScript").text = aa_source(plan)
    children = ET.SubElement(item, "CheatEntries")
    definitions = [
        (1001, "下次载入的角色", "4 Bytes", 0, '00000000:威廉\n00058E5E:飞缘魔 A\n00051BE1:飞缘魔 B', True),
        (1002, "操控辅助 A（沿用旧表）", "Byte", 0x28, '00:默认\n01:开启', True),
        (1003, "操控辅助 B（沿用旧表）", "Byte", 0x29, '00:默认\n01:模式 1\n02:模式 2', True),
        (1004, "交互兼容模式" if experimental_interactions else "箱子与钥匙门交互兼容", "Byte", 0x2A,
         '00:关闭\n01:原有箱子与当前钥匙门\n02:通用物件启动（实验）' if experimental_interactions else '00:关闭\n01:开启', True),
        (1010, "检查：已加载的模板", "4 Bytes", 4, None, True),
        (1011, "检查：资源加载次数", "4 Bytes", 0x18, None, False),
        (1012, "检查：玩家生成次数", "4 Bytes", 0x1C, None, False),
        (1013, "检查：玩家组件初始化次数", "4 Bytes", 0x20, None, False),
        (1014, "检查：辅助输入命中次数", "4 Bytes", 0x24, None, False),
        (1015, "检查：箱子交互兼容次数", "4 Bytes", 0x2C, None, False),
        (1016, "检查：当前钥匙门兼容次数", "4 Bytes", 0x30, None, False),
    ]
    if experimental_interactions:
        definitions += [
            (1017, "检查：通用物件启动次数", "4 Bytes", 0x34, None, False),
            (1018, "检查：最近交互请求编号", "4 Bytes", 0x38, None, False),
            (1019, "检查：最近物件编号", "4 Bytes", 0x3C, None, False),
            (1020, "检查：单侧门开始事件次数", "4 Bytes", 0x40, None, False),
            (1021, "检查：动作镜头兼容次数", "4 Bytes", 0x44, None, False),
            (1022, "检查：神篱碎片使用兼容次数", "4 Bytes", 0x48, None, False),
            (1023, "检查：木灵回家交互兼容次数", "4 Bytes", 0x4C, None, False),
            (1024, "检查：恢复与增益道具使用兼容次数", "4 Bytes", 0x50, None, False),
            (1025, "检查：最近兼容的恢复或增益道具", "4 Bytes", 0x54, None, False),
        ]
        if plan.get('attribute_overlay'):
            definitions += [
                (1026, '成长与装备叠加（保留 Boss 基础）', 'Byte', 0x58, '00:关闭\n01:开启', True),
                (1027, '检查：原生成长与效果缓冲区初始化次数', '4 Bytes', 0x5C, None, False),
                (1028, '检查：成长与装备重新计算次数', '4 Bytes', 0x60, None, False),
                (1029, '检查：本次 Boss 基础生命', '4 Bytes', 0x64, None, False),
                (1030, '检查：本次生命成长与装备加成', '4 Bytes', 0x68, None, False),
                (1031, '检查：本次 Boss 基础精力', '4 Bytes', 0x6C, None, False),
                (1032, '检查：本次精力成长与装备加成', '4 Bytes', 0x70, None, False),
                (1033, '检查：本次 Boss 基础防御', '4 Bytes', 0x74, None, False),
                (1034, '检查：本次防具防御加成', '4 Bytes', 0x78, None, False),
            ]
        if plan.get('weapon_stats_overlay'):
            definitions += [
                (1035, '检查：Boss 基础攻击', '4 Bytes', 0x7C, None, False),
                (1036, '检查：当前武器与成长攻击加成', '4 Bytes', 0x80, None, False),
                (1037, '检查：当前近战武器槽', '4 Bytes', 0x8C, '0:第一槽\n1:第二槽', False),
                (1038, '检查：当前武器的原生计算攻击', '4 Bytes', 0x90, None, False),
                (1039, '检查：空装基准攻击', '4 Bytes', 0x94, None, False),
                (1040, '检查：当前武器编号', '4 Bytes', 0x98, None, False),
                (1041, '检查：武器攻击更新次数', '4 Bytes', 0x9C, None, False),
            ]
        if plan.get('weapon_hud_view'):
            definitions += [
                (1042, '检查：武器图标更新次数', '4 Bytes', 0xA0, None, False),
            ]
        if plan.get('weapon_hud_refresh_view'):
            definitions += [
                (1043, '检查：武器图标逐帧读取次数', '4 Bytes', 0xA4, None, False),
                (1044, '检查：近战武器图标切换读取次数', '4 Bytes', 0xA8, None, False),
                (1045, '检查：远程武器图标切换读取次数', '4 Bytes', 0xAC, None, False),
            ]
        if plan.get('revenant_interaction'):
            definitions += [
                (1046, '检查：血刀冢启动事件补回次数', '4 Bytes', 0xB8, None, False),
                (1047, '检查：最近血刀冢实例编号', '4 Bytes', 0xBC, None, False),
                (1048, '检查：血刀冢已接受请求次数', '4 Bytes', 0xC8, None, False),
                (1049, '检查：最近血刀冢按住与完成状态', '4 Bytes', 0xCC, None, True),
            ]
        if plan.get('yokai_grab') and not plan.get('automatic_grab'):
            definitions += [(1050, '检查：妖怪完整吸血目标放行次数', '4 Bytes', 0xF00, None, False)]
    for ident, description, kind, offset, dropdown, show_hex in definitions:
        child = ET.SubElement(children, "CheatEntry")
        ET.SubElement(child, "ID").text = str(ident)
        ET.SubElement(child, "Description").text = f'"{description}"'
        ET.SubElement(child, "VariableType").text = kind
        ET.SubElement(child, "Address").text = f"HE_Prototype_Data+{offset:X}"
        if show_hex:
            ET.SubElement(child, "ShowAsHex").text = "1"
        if dropdown:
            ET.SubElement(child, "DropDownList", DisplayValueAsItem="1").text = dropdown
    ET.SubElement(doc, "Comments").text = (
        f'飞缘魔 {display_version}，适配已核对的 Steam《仁王 完全版》1.24.8（窗口 1.24.08）。\n'
        '根据 Bryanyora 的 Character Change CT 重新适配，保留原作者署名。\n'
        f'同一套 {len(plan["hooks"])} 处处理保留飞缘魔模型、招式、原生 Buff 和成长与装备加成。\n'
        '生命、精力、攻击和防御按神社等级 1—400 映射到 Boss 成长档位 1—1410；保留更高原生档位。\n'
        '数字 1 吸血；5 地面及空中吼叫；9 原生九十九与守护灵战斗召唤；F6 净化常世。\n'
        '支持已测试的元素符、道祖神护符、守护灵取回、梯子及温泉坐下和起身；道具从背包使用。\n'
        '当前这处温泉中，飞缘魔与同版本威廉对照均在松开输入后短暂停留再起身，保留原生流程。\n'
        '未声称等待时长完全相同；所有温泉、交互、关卡、敌人、词条和伤害幅度尚未逐一验证。\n'
        '保留吼叫与俯冲物件的原有属性，未给这些受保护通道强行叠加第二元素；路标符投放与罗盘标记已获实测确认。\n'
        '门闩门、NPC交谈与誾千代倒地救助已获实测；其他NPC/交互变体尚未全部验证。\n'
        '部分非关键道具使用仍未修复；第一栏数字 2 快捷位已确认可用，其余快捷位保留技能。\n'
        '角色选择在主菜单重新载入后生效，威廉为 00000000。道具可从背包或第一栏数字 2 使用。\n'
        '保留八种道具兼容，盐的使用、妖怪精力命中与已测受击恢复获实测确认。\n'
        '本版新增已测战后浓姬倒地目标的完整吸血动画；不额外伤害、回血或复活，结束后恢复倒地姿态。\n'
        '该兼容仅适用于核对过的目标与动画资源；未覆盖全部战后 Boss。\n'
        '盐的全部受击方向与连续受击分支未逐一实测；离线合成 CPU 检查不等同实机验证。\n'
        '武器切换只补教学操作。实际射击和 Boss 实际武器槽切换尚未实现。\n'
        '九十九保留飞缘魔招式；守护灵召唤未执行威廉挥刀的额外精力费用。\n'
        '推荐独立 EXE。本 CT 在 CE 内直接启用尚未实测，同一次游戏请选择 CT 或 EXE 一种方式。\n'
        'Hotfix1 修复梯子途中自动掉下、每步瞬移及离梯过高；当前与待切换公共攀爬动作均使用一致的位移缩放。\n'
        '已测梯子上下攀爬和离梯正常，全部梯子、受击中断仍未逐一实测。\n'
        '升级请先退出游戏；Hotfix 与旧 Beta5.1 不在同一进程叠加启用。\n'
        '本表不包含游戏程序、游戏资源、私有研究快照或旧 CT。')
    ET.indent(doc, space="  ")
    return ET.tostring(doc, encoding="unicode", xml_declaration=True) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    plan = load_plan()
    generated = generate(plan)
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    ct = ct_source(plan, version["display_version"])
    ct_target = ROOT / "ct" / version["ct_file"]
    target = ROOT / "launcher/Profile.generated.cs"
    if args.check:
        if target.read_text("utf-8") != generated:
            raise ValueError("Checked-in Profile.generated.cs differs; regenerate and review")
        if ct_target.read_text("utf-8") != ct:
            raise ValueError("Checked-in CT differs; regenerate and review")
        print(f"Generated profile and CT match all {len(plan['hooks'])} frozen payloads")
    else:
        target.write_text(generated, encoding="utf-8", newline="\n")
        ct_target.write_text(ct, encoding="utf-8", newline="\n")
        print("Generated launcher/Profile.generated.cs and " + ct_target.name)


if __name__ == "__main__":
    main()
