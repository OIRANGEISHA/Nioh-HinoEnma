"""Portable offline cold-start reproduction for the published menu-ready hook.

No game files, process access or captured records. This harness executes the emitted
Beta 5.3.1 payload, including its real preload/root/wait state machine, against
explicit synthetic native RET stubs. The baseline tests document reproduced
failure modes; positive tests cover the revision with synthetic native-call stubs.
"""
from __future__ import annotations

import importlib.util
import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'src')]
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
import unicorn.x86_const as reg
import build_profile as builder
import menu_preview_reload_portable as baseline_source
import menu_preview_coldstart_portable as candidate_source
FROZEN = json.loads((ROOT / 'profiles/steam-1.24.8.json').read_text('utf-8'))
PLAN = baseline_source.apply_menu_preview(builder.source_plan_beta52(FROZEN))

OWNER, IDS, IDNODE, IDVT = 0x31000000, 0x31010000, 0x31011000, 0x31012000
WORLD, TREE1, TREE2, SENTINEL1, SENTINEL2 = (
    0x31020000, 0x31021000, 0x31022000, 0x31023000, 0x31024000)
GATE1, GATE2 = 0x31025000, 0x31026000
STACK_BOTTOM, STACK_TOP = 0x20000000, 0x20010000
LAYOUTS = ((0x140000000, 0x144000000), (0x140000000, 0x138000000),
    (0x240000000, 0x242700000), (0x240000000, 0x22F100000),
    (0x450000000, 0x46FA00000), (0x450000000, 0x434C00000),
    (0x7FF709EB0000, 0x7FF70DEF0000), (0x7FF709EB0000, 0x7FF700000000),
    (0x7FF650000000, 0x7FF663210000), (0x7FF650000000, 0x7FF638FA0000),
    (0x7FE120000000, 0x7FE12AFE0000), (0x7FE120000000, 0x7FE103000000))
GPRS = tuple(getattr(reg, "UC_X86_REG_" + n.upper()) for n in
    ("rax", "rbx", "rcx", "rdx", "rbp", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rsp"))
XMMS = tuple(getattr(reg, "UC_X86_REG_XMM" + str(i)) for i in range(16))
REGISTERS = GPRS + XMMS + (reg.UC_X86_REG_EFLAGS, reg.UC_X86_REG_MXCSR)


class ColdMachine:
    """Zero-ticket construction with controllable native readiness callbacks."""
    executed_frames = 0
    def __init__(self, *, selected=0x58E5E, layout=LAYOUTS[0], ready_at=None,
                 tracked=False, ids=True, world=True, package=None, plan=None,
                 gate1_ready_at=1, gate2_ready_at=1):
        self.plan = PLAN if plan is None else plan
        self.module, self.code = layout
        self.production = self.code + 0xF000
        self.visual = self.code + 0x24000
        self.scope = self.code + 0x2C000
        self.cpu = Uc(UC_ARCH_X86, UC_MODE_64)
        for at, size in ((self.module, 0x1A00000), (self.code, self.plan["allocation_size"]),
                         (OWNER, 0x40000), (STACK_BOTTOM, 0x20000)):
            self.cpu.mem_map(at, size)
        self.hook = builder.assemble(dict(self.plan, hooks=[
            h for h in self.plan["hooks"] if h["name"] == "HE_MapVisualReadyPrivate"]),
            self.module, self.code)[0]
        self.cpu.mem_write(self.hook["target"], self.hook["payload"])
        self.selected, self.ready_at, self.tracked, self.package = selected, ready_at, tracked, package
        self.gate1_ready_at, self.gate2_ready_at = gate1_ready_at, gate2_ready_at
        self.totals = dict(package_get=0, package_tracked=0, preload=0, character_ready=0)
        self.stub_targets = {name: self.plan["targets"][name] for name in self.totals}
        for i, rva in enumerate((0xC448E0, 0xC449A0), 1):
            if rva in self.plan["targets"].values():
                self.totals[f"native_gate_{i}"] = 0
                self.stub_targets[f"native_gate_{i}"] = rva
        for rva in self.stub_targets.values():
            self.cpu.mem_write(self.module + rva, b"\xC3")
        self.put64(self.module + 0x189F430, GATE1)
        self.put64(self.module + 0x189F400, GATE2)
        self.put64(OWNER, self.module + self.plan["targets"]["base_mode_vtable"])
        self.put32(OWNER + 0x1C, 0)
        self.put32(self.production, selected)
        self.put64(self.module + self.plan["targets"]["player_slot"], 0)
        self.put64(IDS + 0x10, IDNODE)
        self.put64(IDNODE + 8, IDVT)
        self.put64(WORLD + 0x568, TREE1)
        self.put64(WORLD + 0x578, TREE2)
        self.put64(TREE1 + 8, SENTINEL1)
        self.put64(TREE2 + 8, SENTINEL2)
        self.roots(ids=ids, world=world)
        self.exit, self.calls, self.writes = None, [], []

    def put32(self, at, value):
        self.cpu.mem_write(at, struct.pack("<I", value & 0xFFFFFFFF))

    def put64(self, at, value):
        self.cpu.mem_write(at, struct.pack("<Q", value))

    def get32(self, at):
        return struct.unpack("<I", self.cpu.mem_read(at, 4))[0]

    def get64(self, at):
        return struct.unpack("<Q", self.cpu.mem_read(at, 8))[0]

    def roots(self, *, ids=True, world=True):
        self.put64(self.module + self.plan["targets"]["package_ids"], IDS if ids else 0)
        self.put64(self.module + self.plan["targets"]["world_manager"], WORLD if world else 0)

    def reset(self):
        for i, r in enumerate(GPRS):
            self.cpu.reg_write(r, 0xBA00000000000000 + i)
        for i, r in enumerate(XMMS):
            self.cpu.reg_write(r, 0xABCDEF01234567899876543210ABCDEF + i)
        self.cpu.reg_write(reg.UC_X86_REG_RSP, STACK_TOP)
        self.cpu.reg_write(reg.UC_X86_REG_RSI, OWNER)
        self.cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0xAD7)
        self.cpu.reg_write(reg.UC_X86_REG_MXCSR, 0x1F80)

    def registers(self):
        return {r: self.cpu.reg_read(r) for r in REGISTERS}

    def ticket(self):
        return {name: self.get32(self.visual + off) for name, off in
            dict(selected=8, requests=0xC, tracked=0x10, status=0x14,
                 package=0x18, waited=0x1C, lock=0x20, fallbacks=0x24, epoch=0x38).items()}

    def trace(self, cpu, address, size, _):
        if address == self.hook["site"] + self.hook["length"]:
            self.exit = "continue"
            cpu.emu_stop()
            return
        if address == self.module + self.plan["targets"]["map_wait"]:
            self.exit = "wait"
            cpu.emu_stop()
            return
        target = next((name for name, rva in self.stub_targets.items() if
            address == self.module + rva), None)
        if target is None:
            return
        arguments = tuple(cpu.reg_read(r) for r in
            (reg.UC_X86_REG_RCX, reg.UC_X86_REG_RDX, reg.UC_X86_REG_R8))
        self.calls.append((target, arguments))
        self.totals[target] += 1
        # Native helpers may clobber all volatile registers and XMM0..5.
        # Deliberately clobber them so every saved-state exit is exercised.
        for i, r in enumerate((reg.UC_X86_REG_RAX, reg.UC_X86_REG_RCX,
                reg.UC_X86_REG_RDX, reg.UC_X86_REG_R8, reg.UC_X86_REG_R9,
                reg.UC_X86_REG_R10, reg.UC_X86_REG_R11)):
            cpu.reg_write(r, 0xCC00000000000000 + i)
        for i, r in enumerate(XMMS[:6]):
            cpu.reg_write(r, 0xDDEEFF0102030405 + i)
        cpu.reg_write(reg.UC_X86_REG_EFLAGS, 0x246)
        if target == "package_get":
            value = self.package if self.package is not None else (232 if self.selected == 0x58E5E else 233)
        elif target == "package_tracked":
            value = int(self.tracked)
        elif target == "character_ready":
            value = int(self.ready_at is not None and self.totals[target] >= self.ready_at)
        elif target in ("native_gate_1", "native_gate_2"):
            threshold = self.gate1_ready_at if target.endswith("1") else self.gate2_ready_at
            value = int(threshold is not None and self.totals[target] >= threshold)
        else:
            value = 0
        cpu.reg_write(reg.UC_X86_REG_EAX, value)

    def frame(self):
        type(self).executed_frames += 1
        self.reset()
        before = self.registers()
        self.exit, self.calls, self.writes = None, [], []
        code = self.cpu.hook_add(UC_HOOK_CODE, self.trace)
        write = self.cpu.hook_add(UC_HOOK_MEM_WRITE,
            lambda cpu, access, at, n, value, user: self.writes.append((at, n)))
        try:
            self.cpu.emu_start(self.hook["target"], 0, count=10000)
        finally:
            self.cpu.hook_del(code)
            self.cpu.hook_del(write)
        if self.exit is None:
            raise AssertionError("Ready hook missed both bounded native exits")
        return before, self.registers()


class PublishedColdStartTests(unittest.TestCase):
    def check_abi(self, m, before, after):
        ignored = () if m.exit == "wait" else (
            reg.UC_X86_REG_RAX, reg.UC_X86_REG_R12, reg.UC_X86_REG_EFLAGS)
        for r in REGISTERS:
            if r not in ignored:
                self.assertEqual(after[r], before[r], f"Register {r} changed on {m.exit}")
        if m.exit == "continue":
            self.assertEqual(after[reg.UC_X86_REG_RAX], m.get32(OWNER + 0x1C))
            self.assertEqual(after[reg.UC_X86_REG_R12], 0)
            self.assertEqual(after[reg.UC_X86_REG_EFLAGS], (before[reg.UC_X86_REG_EFLAGS] & ~0x8D5) | 0x44)
        self.assertEqual(m.ticket()["lock"], 0)
        for at, size in m.writes:
            self.assertTrue((STACK_TOP - 0xE8 <= at and at + size <= STACK_TOP) or
                (m.visual <= at and at + size <= m.visual + 0x40) or
                (m.scope <= at and at + size <= m.scope + 0x54),
                f"Write outside private state/saved stack: {at:x}+{size:x}")

    def test_ready_after_real_request_preserves_abi_12layouts_two_templates(self):
        for layout in LAYOUTS:
            for selected in (0x58E5E, 0x51BE1):
                with self.subTest(layout=layout, selected=hex(selected)):
                    m = ColdMachine(selected=selected, layout=layout, ready_at=3)
                    for expected_exit, status, waited in (("wait", 1, 1), ("wait", 1, 2), ("continue", 7, 2)):
                        before, after = m.frame()
                        self.check_abi(m, before, after)
                        self.assertEqual((m.exit, m.ticket()["status"], m.ticket()["waited"]),
                                         (expected_exit, status, waited))
                    self.assertEqual(m.totals, dict(package_get=1, package_tracked=1, preload=1, character_ready=3))
                    self.assertEqual(m.ticket()["requests"], 1)

    def test_previously_tracked_resources_wait_without_duplicate_preload(self):
        m = ColdMachine(tracked=True, ready_at=2)
        for expected in ("wait", "continue"):
            before, after = m.frame()
            self.check_abi(m, before, after)
            self.assertEqual(m.exit, expected)
        self.assertEqual(m.ticket()["status"], 7)
        self.assertEqual((m.totals["preload"], m.ticket()["tracked"]), (0, 1))

    def test_actual480_timeout_is_terminal_even_when_assets_later_ready(self):
        m = ColdMachine(ready_at=481)
        for frame in range(1, 481):
            before, after = m.frame()
            self.check_abi(m, before, after)
            self.assertEqual(m.exit, "wait" if frame < 480 else "continue")
        self.assertEqual(m.ticket(), dict(selected=0x58E5E, requests=1, tracked=0,
            status=6, package=232, waited=480, lock=0, fallbacks=1, epoch=0))
        before, after = m.frame()
        self.check_abi(m, before, after)
        self.assertEqual(m.exit, "continue")
        self.assertEqual(m.calls, [])
        self.assertEqual(m.totals["character_ready"], 480)

    def test_missing_manager_latches_fallback_without_wait_or_later_retry(self):
        for ids, world, package in ((False, True, 0xFFFF), (True, False, 232)):
            with self.subTest(ids=ids, world=world):
                m = ColdMachine(ids=ids, world=world, ready_at=1)
                before, after = m.frame()
                self.check_abi(m, before, after)
                self.assertEqual((m.exit, m.ticket()["status"], m.ticket()["waited"],
                                  m.ticket()["package"], m.ticket()["fallbacks"]),
                                 ("continue", 6, 0, package, 1))
                m.roots()
                before, after = m.frame()
                self.check_abi(m, before, after)
                self.assertEqual(m.calls, [])
                self.assertEqual(m.ticket()["status"], 6)

    def test_reload_epoch_clears_terminal_ticket_and_rechecks_ready(self):
        m = ColdMachine(ready_at=1, ids=False)
        m.frame()
        m.put32(OWNER + 0x1C, 1)
        m.frame()
        self.assertEqual(m.ticket()["epoch"], 1)
        m.put32(OWNER + 0x1C, 0)
        m.roots()
        before, after = m.frame()
        self.check_abi(m, before, after)
        self.assertEqual(m.ticket()["status"], 7)
        self.assertEqual(m.totals["preload"], 1)

    def test_existing_actor_and_nonboss_selector_skip_all_native_resource_calls(self):
        for actor, selected in ((OWNER + 0x1000, 0x58E5E), (0, 0x64)):
            with self.subTest(actor=actor, selected=hex(selected)):
                m = ColdMachine(selected=selected, ready_at=1)
                m.put64(m.module + m.plan["targets"]["player_slot"], actor)
                before, after = m.frame()
                self.check_abi(m, before, after)
                self.assertEqual(m.exit, "continue")
                self.assertEqual(m.calls, [])
                self.assertEqual(m.ticket()["status"], 0)


CANDIDATE = candidate_source.apply_menu_preview(builder.source_plan_beta52(FROZEN))
assert CANDIDATE['hooks'] == FROZEN['hooks'] and CANDIDATE['targets'] == FROZEN['targets']


class CandidateColdStartTests(PublishedColdStartTests):
    """Positive behavior checks; published failures above remain separate."""
    # Inherit the reusable ABI checker only. unittest otherwise repeats the
    # baseline tests unchanged; disable those inherited method references.
    test_ready_after_real_request_preserves_abi_12layouts_two_templates = None
    test_previously_tracked_resources_wait_without_duplicate_preload = None
    test_actual480_timeout_is_terminal_even_when_assets_later_ready = None
    test_missing_manager_latches_fallback_without_wait_or_later_retry = None
    test_reload_epoch_clears_terminal_ticket_and_rechecks_ready = None
    test_existing_actor_and_nonboss_selector_skip_all_native_resource_calls = None

    def fresh(self, **kwargs):
        return ColdMachine(plan=CANDIDATE, **kwargs)

    def execute(self, m, expected):
        before, after = m.frame()
        self.check_abi(m, before, after)
        self.assertEqual(m.exit, expected)

    def test_only_ready_changes_and_all71_launcher_relocations_12layouts(self):
        self.assertEqual(len(PLAN["hooks"]), 71)
        self.assertEqual(CANDIDATE["allocation_size"], PLAN["allocation_size"])
        changed = [old["name"] for old, new in zip(PLAN["hooks"], CANDIDATE["hooks"]) if old != new]
        self.assertEqual(changed, ["HE_MapVisualReadyPrivate"])
        for name, value in PLAN["targets"].items():
            self.assertEqual(CANDIDATE["targets"][name], value)
        specs = builder.relocation_specs(CANDIDATE)
        for module, allocation in LAYOUTS:
            old_hooks = builder.assemble(PLAN, module, allocation)
            hooks = builder.assemble(CANDIDATE, module, allocation)
            for i, (old, hook, item) in enumerate(zip(old_hooks, hooks, specs)):
                self.assertLessEqual(len(hook["payload"]), hook["code_capacity"])
                if i != 60:
                    self.assertEqual(old["payload"], hook["payload"])
                    self.assertEqual(old["patched"], hook["patched"])
                payload = bytearray(base64.b64decode(item["template"]))
                for fixup in item["fixups"]:
                    if fixup["kind"] == 0:
                        struct.pack_into("<Q", payload, fixup["offset"], allocation + 0xF000)
                    elif fixup["kind"] == 2:
                        struct.pack_into("<Q", payload, fixup["offset"], module + fixup["target"])
                    elif fixup["kind"] == 1:
                        struct.pack_into("<i", payload, fixup["offset"], module + fixup["target"] -
                            (hook["target"] + fixup["next"]))
                    else:
                        self.fail("New unsupported launcher relocation kind")
                self.assertEqual(bytes(payload), hook["payload"])

    def test_two_loading_gates_can_exceed_old_timeout_without_asset_budget(self):
        m = self.fresh(gate1_ready_at=None)
        for _ in range(600):
            self.execute(m, "wait")
        self.assertEqual(m.ticket()["waited"], 0)
        self.assertEqual(m.get32(m.visual + 0x34), 600)
        self.assertEqual(m.get32(m.visual + 0x3C), 1)
        self.assertEqual(m.totals["native_gate_2"], 0)
        m.gate1_ready_at, m.gate2_ready_at = 1, None
        for _ in range(600):
            self.execute(m, "wait")
        self.assertEqual(m.ticket()["waited"], 0)
        self.assertEqual(m.get32(m.visual + 0x34), 1200)
        self.assertEqual(m.get32(m.visual + 0x3C), 2)
        m.gate2_ready_at = 1
        m.ready_at = m.totals["character_ready"] + 3
        self.execute(m, "wait")
        self.execute(m, "wait")
        self.execute(m, "continue")
        self.assertEqual((m.ticket()["status"], m.ticket()["waited"]), (7, 2))
        self.assertEqual((m.ticket()["requests"], m.totals["preload"]), (1, 1))
        self.assertEqual(m.ticket()["fallbacks"], 0)

    def test_transient_roots_retry_without_resetting_wait_or_duplicate_request(self):
        for ids, world, status, package in ((False, True, 5, 0xFFFF), (True, False, 4, 232)):
            with self.subTest(ids=ids, world=world):
                m = self.fresh(ids=ids, world=world)
                for frame in range(1, 11):
                    self.execute(m, "wait")
                    self.assertEqual((m.ticket()["status"], m.ticket()["waited"], m.ticket()["package"]),
                                     (status, frame, package))
                    self.assertEqual(m.totals["character_ready"], 0)
                m.roots()
                self.execute(m, "wait")
                self.assertEqual(m.ticket()["waited"], 11)
                self.assertEqual(m.ticket()["status"], 1)
                m.ready_at = m.totals["character_ready"] + 1
                self.execute(m, "continue")
                self.assertEqual(m.ticket()["status"], 7)
                self.assertEqual((m.ticket()["requests"], m.totals["preload"]), (1, 1))

    def test_inner_id_and_world_root_guards_are_retryable(self):
        for at, restored, expected in ((IDS + 0x10, IDNODE, 5), (IDNODE + 8, IDVT, 5),
                                     (WORLD + 0x568, TREE1, 4), (TREE2 + 8, SENTINEL2, 4)):
            with self.subTest(at=hex(at)):
                m = self.fresh()
                m.put64(at, 0)
                self.execute(m, "wait")
                self.assertEqual(m.ticket()["status"], expected)
                self.assertEqual(m.totals["preload"], 0)
                m.put64(at, restored)
                m.ready_at = 1
                self.execute(m, "continue")
                self.assertEqual(m.ticket()["status"], 7)
                self.assertEqual(m.totals["preload"], 1)

    def test_unexpected_package_remains_terminal_and_never_requested(self):
        m = self.fresh(package=234, ready_at=1)
        self.execute(m, "continue")
        self.assertEqual((m.ticket()["status"], m.ticket()["waited"], m.ticket()["fallbacks"]), (6, 0, 1))
        self.assertEqual(m.calls, [("package_get", (IDS, 0x58E5E, 0))])
        m.package = 232
        self.execute(m, "continue")
        self.assertEqual(m.calls, [])

    def test_asset_false_1800_frames_is_bounded_single_fallback(self):
        m = self.fresh()
        for frame in range(1, 1801):
            self.execute(m, "wait" if frame < 1800 else "continue")
            self.assertEqual(m.ticket()["waited"], frame)
        self.assertEqual((m.ticket()["status"], m.ticket()["fallbacks"], m.ticket()["requests"]), (6, 1, 1))
        self.assertEqual(m.get32(m.visual + 0x34), 0)
        self.execute(m, "continue")
        self.assertEqual(m.calls, [])
        self.assertEqual(m.ticket()["fallbacks"], 1)

    def test_gate_false_7200_frames_total_limit(self):
        m = self.fresh(gate1_ready_at=None)
        for frame in range(1, 7201):
            self.execute(m, "wait" if frame < 7200 else "continue")
        self.assertEqual((m.ticket()["status"], m.ticket()["waited"], m.ticket()["fallbacks"]), (6, 0, 1))
        self.assertEqual(m.get32(m.visual + 0x34), 7200)
        self.execute(m, "continue")
        self.assertEqual(m.calls, [])

    def test_mixed_gate_and_asset_wait_share_total7200_limit(self):
        m = self.fresh(gate1_ready_at=None)
        # Reach a near-limit synthetic private counter via repeated genuine
        # gate closures; open gates for the final ten asset-readiness frames.
        for _ in range(7190):
            self.execute(m, "wait")
        m.gate1_ready_at = 1
        for frame in range(1, 11):
            self.execute(m, "wait" if frame < 10 else "continue")
        self.assertEqual((m.ticket()["status"], m.ticket()["waited"]), (6, 10))
        self.assertEqual(m.get32(m.visual + 0x34), 7190)

    def test_gate_root_range_guards_skip_native_calls_and_retry(self):
        for rva, restored, unexpected in ((0x189F430, GATE1, "native_gate_1"),
                                           (0x189F400, GATE2, "native_gate_2")):
            for value in (0, 0xFFFF, 0x800000000000):
                with self.subTest(rva=hex(rva), value=hex(value)):
                    m = self.fresh()
                    m.put64(m.module + rva, value)
                    self.execute(m, "wait")
                    self.assertNotIn(unexpected, [name for name, _ in m.calls])
                    self.assertEqual((m.ticket()["waited"], m.get32(m.visual + 0x34)), (0, 1))
                    m.put64(m.module + rva, restored)
                    self.execute(m, "wait")
                    self.assertEqual((m.ticket()["waited"], m.get32(m.visual + 0x34)), (1, 1))

    def test_new_reload_epoch_resets_budgets_after_terminal_fallback(self):
        m = self.fresh()
        for _ in range(1800):
            self.execute(m, "wait" if m.ticket()["waited"] < 1799 else "continue")
        m.put32(OWNER + 0x1C, 1)
        self.execute(m, "continue")
        self.assertEqual(m.ticket()["epoch"], 1)
        m.put32(OWNER + 0x1C, 0)
        self.execute(m, "wait")
        self.assertEqual((m.ticket()["status"], m.ticket()["waited"], m.ticket()["epoch"]), (1, 1, 0))
        self.assertEqual(m.get32(m.visual + 0x34), 0)
        self.assertEqual(m.ticket()["requests"], 2)
        m.ready_at = m.totals["character_ready"] + 1
        self.execute(m, "continue")
        self.assertEqual(m.ticket()["status"], 7)

    def test_candidate_wait_and_ready_abi_all12layouts_two_templates(self):
        for layout in LAYOUTS:
            for selected in (0x58E5E, 0x51BE1):
                with self.subTest(layout=layout, selected=hex(selected)):
                    m = self.fresh(layout=layout, selected=selected, ready_at=3)
                    self.execute(m, "wait")
                    self.execute(m, "wait")
                    self.execute(m, "continue")
                    self.assertEqual((m.ticket()["status"], m.ticket()["requests"]), (7, 1))

    def test_candidate_slot_and_selector_guards_skip_calls(self):
        for actor, selected in ((OWNER + 0x1000, 0x58E5E), (0, 0x64)):
            with self.subTest(actor=actor, selected=hex(selected)):
                m = self.fresh(selected=selected, ready_at=1)
                m.put64(m.module + m.plan["targets"]["player_slot"], actor)
                self.execute(m, "continue")
                self.assertEqual(m.calls, [])
                self.assertEqual(m.ticket()["status"], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
