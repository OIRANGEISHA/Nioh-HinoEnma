"""Regenerate the frozen Steam payload without proprietary game files."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hinoenma_hooks import BLOCK_SIZE, EXPERIMENTAL_HOOKS, TARGETS
from hinoenma_attributes import ATTRIBUTE_TARGETS
from hinoenma_weapon_view import compatible_weapon_hooks, HUD_HOOK, HUD_REFRESH_HOOKS
from hinoenma_revenant import PLAYER_REVENANT_INTERACTION
from keystone import Ks, KS_ARCH_X86, KS_MODE_64
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_OP_IMM

BASE = 0x140000000
ALLOCATION = 0x144000000


def load_plan() -> dict:
    plan = json.loads((ROOT / "profiles/steam-1.24.8.json").read_text("utf-8"))
    version = json.loads((ROOT / "version.json").read_text("utf-8"))
    if plan["tool_version"] != version["version"]:
        raise ValueError("Manifest and release version differ")
    specs = list(EXPERIMENTAL_HOOKS) + compatible_weapon_hooks() + [HUD_HOOK]
    specs += list(HUD_REFRESH_HOOKS) + [PLAYER_REVENANT_INTERACTION]
    if len(specs) != len(plan["hooks"]):
        raise ValueError("Frozen hook list differs from source")
    targets = dict(TARGETS, **ATTRIBUTE_TARGETS)
    if plan["targets"] != targets:
        raise ValueError("Frozen native targets differ from source")
    offset = 0
    md = Cs(CS_ARCH_X86, CS_MODE_64)
    for frozen, source in zip(plan["hooks"], specs):
        for key in ("name", "rva", "length"):
            if frozen[key] != source[key]:
                raise ValueError("Frozen hook specification differs: " + frozen["name"])
        if frozen["code_offset"] != offset or frozen.get("code_capacity", BLOCK_SIZE) != source.get("code_capacity", BLOCK_SIZE):
            raise ValueError("Frozen hook code slot differs")
        original = bytes.fromhex(frozen["original"])
        if len(original) != frozen["length"] or sum(i.size for i in md.disasm(original, BASE + frozen["rva"])) != len(original):
            raise ValueError("Frozen signature truncates a native instruction")
        frozen["asm"] = source["asm"]
        offset += source.get("code_capacity", BLOCK_SIZE)
    if offset > plan["data_offset"] or plan["data_offset"] + 0x1000 > plan["allocation_size"]:
        raise ValueError("Code and data slots overlap")
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
        decoded = list(md.disasm(hook["payload"], hook["target"]))
        if sum(i.size for i in decoded) != len(hook["payload"]):
            raise ValueError("Incomplete payload disassembly")
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
    ]
    for constant, key in (("AttributeOverlay", "attribute_overlay"), ("WeaponStatsOverlay", "weapon_stats_overlay"),
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
        lines.append(f'new HookSpec("{item["name"]}",{item["rva"]}U,{item["code_offset"]},"{original}","{item["template"]}",new Fixup[]{{{fixups}}}),')
    return '\n'.join(lines + ['};', '} }']) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = generate(load_plan())
    target = ROOT / "launcher/Profile.generated.cs"
    if args.check:
        if target.read_text("utf-8") != generated:
            raise ValueError("Checked-in Profile.generated.cs differs; regenerate and review")
        print("Generated profile matches all 21 frozen payloads")
    else:
        target.write_text(generated, encoding="utf-8", newline="\n")
        print("Generated launcher/Profile.generated.cs")


if __name__ == "__main__":
    main()
