"""Dual-boss CPU proofs with synthetic owners and an ABI-clobbering input stub.

No game process, native game code, assets, input injection or scene addresses
are used. These tests prove dynamic discovery, borrowed views and rejection
boundaries; in-game death and story continuation are recorded separately.
"""
from copy import deepcopy
import struct
import unittest

import orochi_fixture as frozen
from orochi_fixture import *
from hinoenma_manual_purification import menu_guard
from hinoenma_ninetails_runtime import (
    apply_ninetails_execution, validate_layout, DATA_OFFSET, CODE_SLOTS,
    CHANGED_INDICES, ALLOCATION_SIZE,
)
from hinoenma_orochi_binding import HEAD_IDENTITIES
from hinoenma_orochi_weapon_guard import PRIVATE_COUNTER_OFFSET
from unicorn import UC_HOOK_MEM_WRITE

PLAN = apply_ninetails_execution(frozen.PLAN, menu_guard())
ALL = assemble(PLAN, MODULE, ALLOCATION)
HOOKS = ALL[71:]
EXTRA = (UC_X86_REG_RBP,) + tuple(globals()['UC_X86_REG_XMM'+str(n)] for n in range(6,16))


class CPU(frozen.CPU):
    def __init__(self, index=0, pressed=True, nine=True, placement=14997):
        super().__init__(0, pressed)
        self.nine = nine
        self.od = self.d
        self.nd = ALLOCATION + DATA_OFFSET
        self.put(self.nd, bytes(0x1000))
        for hook in HOOKS:
            self.put(hook['target'], hook['payload'])
        if nine:
            self.d = self.nd
            self.put(self.target, struct.pack('<IHH', 0xC9AAF, 0, placement))
            self.u(self.metadata, 0xC9AAF)
            self.u(self.ready, 3174)
            self.u(self.params(self.ready)+0x20, 31001)
            self.ofinish, self.opaired, self.oenemy = self.finish, self.paired, self.enemy
            self.finish = self.record(4026, self.bank, 1210)
            self.paired = self.record(1273, self.bank, 1211)
            self.enemy = self.record(1274, self.enemy_bank, 31010)
            self.u(self.params(self.finish)+0x18, 0x194C0000)
            self.u(self.params(self.paired)+0x18, 1<<29)
            self.u(self.params(self.enemy)+0x18, 1<<29)
            self.nwindup = self.transition(self.dispatch, 474, 381, 4026, blend=3)
            array = self.alloc()
            self.q(array, self.nwindup); self.q(array+8, self.windup_transition)
            self.q(self.dispatch+0x78, array)
            self.put(self.dispatch+0x80, struct.pack('<HH', 0, 2))
            self.npaired = self.transition(self.finish, 208, -1, 1273)
            self.nterminal = self.transition(self.paired, -1, -1, 3000)
            self.put(self.nterminal+0xA, b'\x01')
            self.records(self.bank, [self.dispatch, self.ofinish, self.opaired, self.finish, self.paired])
            self.records(self.enemy_bank, [self.ready, self.oenemy, self.enemy])
            for resource in (self.main, self.aux):
                self.extend_motion(resource)
            self.primary = self.extend_events(self.primary, 56)
            self.secondary = self.extend_events(self.secondary, 48)
            # Nine Tails must not depend on Orochi's mission-local death count.
            self.q(MODULE+0x189F408, 0)
        self.writes = []
        self.uc.hook_add(UC_HOOK_MEM_WRITE,
            lambda uc,access,at,size,value,user:self.writes.append((at,size)))
        self.prepare(0)
        if index:
            self.pressed = False
            self.run()
            if self.value(0) != 0x4643524F:
                raise AssertionError('Synthetic dynamic bootstrap rejected')
            self.pressed = pressed
            self.prepare(index)
            self.writes.clear()

    def extend_motion(self, resource):
        array = self.qvalue(resource+0x468)
        self.q(resource+0x470, array+32)
        mapping = self.qvalue(resource+0x480)
        pairs = self.alloc()
        self.u(mapping+8, 6); self.q(mapping+0x10, pairs)
        self.put(pairs, b'\xff'*48)
        for n, (motion, frames) in enumerate(((1200,95),(1201,409),(1210,114),(1211,569))):
            self.put(pairs+(n+1)*8, struct.pack('<Ii', motion, n))
            if n >= 2:
                clip = self.alloc(); self.q(array+n*8, clip)
                self.put(clip+0x18, struct.pack('<fH',60.0,frames))

    def extend_events(self, old, paired_count):
        bank, mapping, pairs = self.alloc(0x2000), self.alloc(), self.alloc()
        self.q(old['owner'], bank); self.q(old['owner']+8, mapping)
        self.put(bank, b'TMG_PACK')
        self.u(bank+0x10, 0x2000); self.u(bank+0x14, 4); self.u(bank+0x20, 0x30)
        self.u(mapping+8, 6); self.q(mapping+0x10, pairs); self.put(pairs,b'\xff'*48)
        descs=[]
        for n, (motion,count) in enumerate(((1200,19),(1201,42),(1210,38),(1211,paired_count))):
            offset=0x100+n*0x400
            self.u(bank+0x30+n*4,offset)
            desc=bank+offset; descs.append(desc)
            self.u(desc+4,count); self.u(desc+8,0x24)
            for row in range(count):
                self.put(desc+0x24+row*12,struct.pack('<3I',row,40,row))
            self.put(pairs+(n+1)*8,struct.pack('<Ii',motion,n))
        return dict(wrapper=old['wrapper'],owner=old['owner'],bank=bank,
                    map=mapping,pairs=pairs,descriptors=descs)

    def prepare(self, index, motion_id=1210, auxiliary=False):
        if not getattr(self,'nine',False):
            super().prepare(index, motion_id if motion_id in (1200,1201) else 1200, auxiliary)
        else:
            super().prepare(index, 1201 if motion_id==1211 else 1200, auxiliary)
            if index in (2,3,4): self.uc.reg_write(UC_X86_REG_RDX,motion_id)
            if index in (5,6): self.uc.reg_write(UC_X86_REG_RSI,motion_id)
        if hasattr(self,'nd'):
            self.hook=HOOKS[index]
        for n,reg in enumerate(EXTRA):
            self.uc.reg_write(reg,0xF00D1234 if reg==UC_X86_REG_RBP else (1<<110)+n)

    def run(self):
        extra_before={reg:self.uc.reg_read(reg) for reg in EXTRA}
        before,after=super().run()
        before.update(extra_before)
        after.update({reg:self.uc.reg_read(reg) for reg in EXTRA})
        return before,after


class Tests(unittest.TestCase):
    aslr_layouts = 0
    previous_payload_comparisons = 0
    previous_patch_comparisons = 0
    unchanged_payload_comparisons = 0
    orochi_body_comparisons = 0

    def abi(self,c,before,after,changed=(),flags=None,heavy=False):
        for reg in GPRS+XMM+EXTRA:
            if reg not in changed:self.assertEqual(before[reg],after[reg],reg)
        self.assertEqual(c.uc.reg_read(UC_X86_REG_RSP),c.rsp+(8 if heavy else 0))
        if flags is not None:self.assertEqual(c.uc.reg_read(UC_X86_REG_EFLAGS),flags)
        for at,size in c.writes:
            self.assertTrue(STACK<=at and at+size<=STACK+0x5000 or
                c.od<=at and at+size<=c.od+0x200 or c.nd<=at and at+size<=c.nd+0x200,
                (hex(at),size))

    def reject_heavy(self,change):
        c=CPU();change(c);flags=c.uc.reg_read(UC_X86_REG_EFLAGS)
        before,after=c.run()
        self.abi(c,before,after,flags=flags)
        self.assertFalse(c.calls);self.assertEqual(c.value(0),0)
        self.assertEqual(c.stopped,c.hook['site']+c.hook['length'])

    def check_q86(self,c,accepted):
        flags=c.uc.reg_read(UC_X86_REG_EFLAGS);before,after=c.run()
        self.abi(c,before,after,() if accepted else (UC_X86_REG_RAX,UC_X86_REG_RCX),flags)
        if not accepted:
            self.assertEqual(after[UC_X86_REG_RAX],c.qvalue(before[UC_X86_REG_RCX]+0x58))
            self.assertEqual(after[UC_X86_REG_RCX],c.params(after[UC_X86_REG_RAX]))
        self.assertEqual(c.value(PRIVATE_COUNTER_OFFSET),int(accepted))
        self.assertEqual(c.stopped,MODULE+PLAN['targets']['native_query_false_epilogue']
                         if accepted else c.hook['site']+c.hook['length'])

    def test_73_previous_payloads_and_patches_preserved_at_12_aslr_layouts(self):
        unchanged=sorted(set(range(81))-set(CHANGED_INDICES))
        self.assertEqual(len(unchanged),73)
        for module in (MODULE,0x7FF600000000,0x180000000):
            for slot in (0,1,37,511):
                allocation=module+0x4000000+slot*0x10000
                current=assemble(PLAN,module,allocation)
                old=assemble(frozen.PLAN,module,allocation)
                type(self).aslr_layouts+=1
                for index in unchanged:
                    self.assertEqual(current[index]['payload'],old[index]['payload'])
                    self.assertEqual(current[index]['patched'],old[index]['patched'])
                    type(self).previous_payload_comparisons+=1
                    type(self).previous_patch_comparisons+=1
                    type(self).unchanged_payload_comparisons+=1
                for hook in current:self.assertLessEqual(len(hook['payload']),hook['code_capacity'])

    def test_old_eight_orochi_bodies_remain_exact_once(self):
        for index in CHANGED_INDICES:
            self.assertEqual(PLAN['hooks'][index]['asm'].count(frozen.PLAN['hooks'][index]['asm']),1)
            type(self).orochi_body_comparisons+=1
        self.assertEqual(PLAN['hooks'][78:80],frozen.PLAN['hooks'][78:80])
        self.assertFalse(PLAN['ninetails_execution_validated'])
        self.assertFalse(PLAN['ninetails_bootstrap_instance_addresses'])

    def test_layout_rejects_overlap_and_changed_data_reservations(self):
        self.assertEqual(tuple((PLAN['hooks'][i]['code_offset'],PLAN['hooks'][i]['code_capacity'])
                               for i in CHANGED_INDICES),CODE_SLOTS)
        self.assertEqual(PLAN['allocation_size'],ALLOCATION_SIZE)
        for change in (lambda p:p.update(ninetails_binding_data_offset=0x42000),
                       lambda p:p['hooks'][72].update(code_offset=0x44000),
                       lambda p:p.update(allocation_size=0x50000)):
            p=deepcopy(PLAN);change(p)
            with self.assertRaises(ValueError):validate_layout(p)

    def test_dynamic_heavy_discovers_both_layers_and_preserves_abi(self):
        c=CPU();flags=c.uc.reg_read(UC_X86_REG_EFLAGS)
        before,after=c.run()
        self.assertEqual(after[UC_X86_REG_RAX],c.heavy)
        self.assertEqual(c.value(0),0x4643524F);self.assertEqual(c.value(0x74),1)
        self.assertEqual(len(c.calls),1)
        self.abi(c,before,after,(UC_X86_REG_RAX,),flags,True)
        for off,value in ((8,c.actor),(0x10,c.ctl),(0x18,c.target),(0x38,c.bank),
                (0x58,c.idle),(0x1F0,c.common_idle),(0x68,c.finish),(0x1A8,c.paired),
                (0xF8,c.primary['descriptors'][2]),(0x100,c.secondary['descriptors'][2]),
                (0x1B0,c.primary['descriptors'][3]),(0x1B8,c.secondary['descriptors'][3])):
            self.assertEqual(c.qvalue(c.d+off),value)
        self.assertEqual(c.qvalue(c.od),0)

    def test_released_input_discovers_without_entering_execution(self):
        c=CPU(pressed=False);flags=c.uc.reg_read(UC_X86_REG_EFLAGS)
        before,after=c.run();self.abi(c,before,after,flags=flags)
        self.assertEqual(c.value(0),0x4643524F)
        self.assertEqual(c.value(0x74),0);self.assertEqual(c.value(0x78),0)

    def test_current_target_header_is_bound_without_fixed_placement(self):
        for placement in (14997,7,32001):
            c=CPU(placement=placement);c.run()
            self.assertEqual(c.value(0x74),1)
            self.assertEqual(c.qvalue(c.d+0x20),c.qvalue(c.target))

    def test_orochi_heavy_still_accepts_all_eight_verified_heads(self):
        for template,placement in HEAD_IDENTITIES:
            ready=3204 if template==0xA09C8 else 3205 if template==0x8F795 else 3203
            c=CPU(nine=False);c.set_head(template,placement,ready,4)
            flags=c.uc.reg_read(UC_X86_REG_EFLAGS);before,after=c.run()
            self.assertEqual(after[UC_X86_REG_RAX],c.heavy)
            self.assertEqual(c.value(0x74),1);self.assertEqual(c.qvalue(c.nd),0)
            self.abi(c,before,after,(UC_X86_REG_RAX,),flags,True)

    def test_orochi_views_and_pending_guard_keep_their_previous_behavior(self):
        for index in (1,2,3,4,5,6,9):
            c=CPU(index,nine=False);before,after=c.run()
            if index==1:self.assertEqual(after[UC_X86_REG_RCX],c.bank)
            if index in (2,6):self.assertEqual(after[UC_X86_REG_RBX],c.main)
            if index==4:self.assertEqual(after[UC_X86_REG_RCX],c.primary['owner'])
            if index==9:self.assertEqual(c.stopped,MODULE+PLAN['targets']['native_query_false_epilogue'])
            self.assertEqual(c.qvalue(c.nd),0)
            self.abi(c,before,after,(UC_X86_REG_RCX,) if index in (1,4) else
                     (UC_X86_REG_RBX,) if index in (2,6) else ())

    def test_player_controller_and_target_ownership_rejections(self):
        changes=(lambda c:c.u(c.actor,0),lambda c:c.u(c.actor+0xEF0,1),
            lambda c:c.q(c.stats+0x20,0),lambda c:c.q(c.proxy,0),
            lambda c:c.q(c.proxy+8,c.tc),lambda c:c.q(c.ctl+0x50,c.target),
            lambda c:c.q(c.ctl+0x5B0,c.target),lambda c:c.q(c.ctl+0x5D8,c.target),
            lambda c:c.q(c.ctl+0x510,c.heavy),lambda c:c.q(c.ctl+0x640,0),
            lambda c:c.q(c.tp,0),lambda c:c.q(c.tp+8,c.ctl),
            lambda c:c.q(c.tc+0x50,c.actor),lambda c:c.q(c.tc+0x5B0,c.actor),
            lambda c:c.q(c.tc+0x5D8,c.actor),lambda c:c.q(c.ts+0x20,2),
            lambda c:c.q(c.ts,c.actor),lambda c:c.u(c.metadata,0x99999),
            lambda c:c.u(c.metadata+0xC,0),lambda c:c.u(c.core+0x1C,0),
            lambda c:c.put(c.core+0x28,b'\x01'),lambda c:c.q(c.target+0xE90,0x800000000000))
        for change in changes:self.reject_heavy(change)

    def test_ready_and_target_paired_actions_require_native_owned_bank(self):
        for change in (lambda c:c.u(c.ready,3173),lambda c:c.put(c.ready+0x40,b'\x00'),
            lambda c:c.q(c.ready+0x38,c.bank),lambda c:c.u(c.params(c.ready)+0x20,31002),
            lambda c:c.u(c.params(c.ready)+0x18,0),lambda c:c.u(c.enemy,1275),
            lambda c:c.put(c.enemy+0x40,b'\x00'),lambda c:c.q(c.enemy+0x38,c.bank),
            lambda c:c.u(c.params(c.enemy)+0x20,31011)):
            self.reject_heavy(change)

    def test_duplicate_or_foreign_weapon_action_records_are_rejected(self):
        for change in (lambda c:c.records(c.bank,[c.dispatch,c.finish,c.paired,c.paired]),
            lambda c:c.u(c.bank+0x130,4097),lambda c:c.q(c.finish+0x38,c.common),
            lambda c:c.put(c.finish+0x40,b'\x00'),lambda c:c.u(c.params(c.finish)+0x20,1211),
            lambda c:c.u(c.params(c.paired)+0x34,1),lambda c:c.q(c.wrapper+0x468,c.native_bank)):
            self.reject_heavy(change)

    def test_native_dispatch_order_blend_pairing_and_terminal_are_required(self):
        for change in (lambda c:c.put(c.nwindup+0x17,b'\x02'),
            lambda c:c.put(c.nwindup,struct.pack('<h',380)),
            lambda c:c.put(c.npaired,struct.pack('<h',207)),
            lambda c:c.put(c.nterminal+0xA,b'\x00'),
            lambda c:c.put(c.nterminal+0x14,struct.pack('<h',3001)),
            lambda c:c.put(c.dispatch+0x80,struct.pack('<HH',1,1))):
            self.reject_heavy(change)

    def test_both_motion_layers_require_exact_unique_maps_and_frame_lengths(self):
        for auxiliary in (False,True):
            for kind in ('frames','duplicate','index','capacity'):
                def change(c,aux=auxiliary,kind=kind):
                    resource=c.aux if aux else c.main
                    array=c.qvalue(resource+0x468);mapping=c.qvalue(resource+0x480)
                    pairs=c.qvalue(mapping+0x10)
                    if kind=='frames':c.put(c.qvalue(array+24)+0x1C,struct.pack('<H',568))
                    if kind=='duplicate':c.put(pairs+40,struct.pack('<Ii',1211,3))
                    if kind=='index':c.put(pairs+32+4,struct.pack('<i',4))
                    if kind=='capacity':c.u(mapping+8,65537)
                self.reject_heavy(change)

    def test_primary_and_aux_event_counts_and_descriptor_bounds_are_required(self):
        for auxiliary in (False,True):
            for kind in ('count','span','time','mapping'):
                def change(c,aux=auxiliary,kind=kind):
                    row=c.secondary if aux else c.primary
                    desc=row['descriptors'][3]
                    if kind=='count':c.u(desc+4,56 if aux else 48)
                    if kind=='span':c.u(desc+8,0x2000)
                    if kind=='time':c.u(desc+0x24,569)
                    if kind=='mapping':c.put(row['pairs']+40,struct.pack('<Ii',1211,3))
                self.reject_heavy(change)

    def test_late_windup_schedule_is_valid_but_16bit_overflow_is_rejected(self):
        for auxiliary in (False,True):
            c=CPU();row=c.secondary if auxiliary else c.primary
            c.u(row['descriptors'][2]+0x24,453);c.run()
            self.assertEqual(c.value(0x74),1)
            def invalid(c,aux=auxiliary):
                row=c.secondary if aux else c.primary;c.u(row['descriptors'][2]+0x24,65536)
            self.reject_heavy(invalid)

    def test_packet_offset_table_cannot_wrap_32bit_bounds(self):
        for row_name in ('primary','secondary'):
            self.reject_heavy(lambda c,name=row_name:c.u(getattr(c,name)['bank']+0x20,0xFFFFFFFC))

    def test_bootstrap_generation_invalidation_and_next_attempt_rediscovery(self):
        c=CPU(pressed=False);c.run()
        self.assertEqual(c.value(0),0x4643524F)
        c.u(c.core+0x1C,4);c.prepare(0);c.run()
        self.assertEqual(c.value(0),0);self.assertEqual(c.value(0x74),0)
        c.prepare(0);c.run()
        self.assertEqual(c.value(0),0x4643524F);self.assertEqual(c.value(4),4)

    def test_idle_binding_rediscovers_loaded_resource_owners(self):
        c=CPU(pressed=False);c.run()
        old=c.primary['owner']
        owner=c.alloc();c.q(owner,c.primary['bank']);c.q(owner+8,c.primary['map'])
        c.q(c.primary['wrapper']+0x468,owner)
        c.prepare(0);c.run()
        self.assertNotEqual(old,owner);self.assertEqual(c.qvalue(c.d+0xC8),owner)

    def test_both_stages_layers_and_current_previous_blend_use_owned_views(self):
        for ident,record in ((1210,'finish'),(1211,'paired')):
            for auxiliary in (False,True):
                for index in (2,3,4,5,6):
                    for previous in (False,True):
                        c=CPU(index);c.prepare(index,ident,auxiliary)
                        if previous:c.q(c.ctl+0x60,getattr(c,record));c.q(c.ctl+0x58,c.idle)
                        before,after=c.run()
                        changed=()
                        if index in (2,6):
                            self.assertEqual(after[UC_X86_REG_RBX],c.aux if auxiliary else c.main)
                            changed=(UC_X86_REG_RBX,)
                        if index==4:
                            self.assertEqual(after[UC_X86_REG_RCX],(c.secondary if auxiliary else c.primary)['owner'])
                            changed=(UC_X86_REG_RCX,)
                        if index in (3,5):self.assertFalse(c.uc.reg_read(UC_X86_REG_EFLAGS)&0x40)
                        self.abi(c,before,after,changed,0x206 if index in (3,5) else 0x246)

    def test_chain_bank_requests_require_owned_pair_query_state(self):
        for ident in (3008,4026):
            c=CPU(1);c.uc.reg_write(UC_X86_REG_R10,ident);c.run()
            self.assertEqual(c.uc.reg_read(UC_X86_REG_RCX),c.bank)
        for active in (False,True):
            c=CPU(1);c.uc.reg_write(UC_X86_REG_R10,1273)
            c.u(c.ctl+0x40,0x400000 if active else 0);c.q(c.ctl+0x5B0,c.target if active else 0)
            c.run();self.assertEqual(c.uc.reg_read(UC_X86_REG_RCX),c.bank if active else c.native_bank)
        for ident in (38,3491,4000,4027,1275):
            c=CPU(1);c.uc.reg_write(UC_X86_REG_R10,ident);c.run()
            self.assertEqual(c.uc.reg_read(UC_X86_REG_RCX),c.native_bank)

    def test_terminal_returns_hino_idle_and_clears_only_private_phase(self):
        c=CPU(1);c.pair(dead=True);c.uc.reg_write(UC_X86_REG_R10,3000)
        before,after=c.run()
        self.assertEqual(after[UC_X86_REG_R10],0);self.assertEqual(c.value(0x74),0)
        self.assertEqual(c.value(0x84),1)
        self.abi(c,before,after,(UC_X86_REG_RCX,UC_X86_REG_R10))

    def test_pending_query86_false_keeps_abi_and_game_state_untouched(self):
        for pending in (0,'target'):
            c=CPU(9);c.q(c.ctl+0x5D8,c.target if pending else 0)
            self.check_q86(c,True)
            self.assertEqual(c.qvalue(c.ts+0x20),1)
            self.assertEqual(c.qvalue(c.ctl+0x5D8),c.target if pending else 0)

    def test_pending_query86_foreign_or_stale_context_keeps_native_result(self):
        for change in (lambda c:c.q(c.ctl+0x58,c.paired),lambda c:c.u(c.core+0x1C,4),
            lambda c:c.q(c.ctl+0x5B0,c.target),lambda c:c.q(c.ctl+0x5D8,c.actor),
            lambda c:c.q(c.ctl+0x640,0),lambda c:c.u(c.ready,3173),
            lambda c:c.q(c.ts+0x20,0),lambda c:c.q(c.tp+8,c.ctl),
            lambda c:c.u(c.params(c.ready)+0x18,0),lambda c:c.u(c.d+0x74,0),
            lambda c:c.uc.reg_write(UC_X86_REG_RSI,1),lambda c:c.uc.reg_write(UC_X86_REG_RDI,c.tc)):
            c=CPU(9);change(c);c.writes.clear();self.check_q86(c,False)

    def test_stale_same_generation_nine_phase_does_not_mask_new_orochi_scope(self):
        c=CPU(1,nine=False)
        phantom=c.alloc(0x2000)
        c.u(phantom,0xC9AAF)
        for off,value in ((8,c.actor),(0x10,c.ctl),(0x18,phantom),(0xA0,c.qvalue(c.actor))):
            c.q(c.nd+off,value)
        c.u(c.nd,0x4643524F);c.u(c.nd+4,3);c.u(c.nd+0x74,1)
        c.run();self.assertEqual(c.uc.reg_read(UC_X86_REG_RCX),c.bank)
        c.prepare(9,1200);c.run()
        self.assertEqual(c.stopped,MODULE+PLAN['targets']['native_query_false_epilogue'])


if __name__=='__main__':unittest.main()
