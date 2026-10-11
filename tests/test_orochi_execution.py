"""Portable CPU proof with synthetic native owners and explicit call stubs."""
from copy import deepcopy
import struct
import unittest

from orochi_fixture import *
from build_profile import legacy_plans, source_plan_beta532
from hinoenma_orochi_runtime import CODE_SLOTS, NATIVE_SPANS
from hinoenma_orochi_binding import HEAD_IDENTITIES
from hinoenma_orochi_weapon_guard import NATIVE_QUERY_FRAME, PRIVATE_COUNTER_OFFSET
from unicorn import UC_HOOK_MEM_WRITE


class Tests(unittest.TestCase):
    previous_payload_comparisons = 0
    previous_patch_comparisons = 0
    aslr_layouts = 0
    def preserved(self, c, before, after, changed=()):
        for reg in GPRS+XMM:
            if reg not in changed:self.assertEqual(before[reg],after[reg],reg)

    def check_weapon_guard(self, c, accepted):
        # Query86 does not make calls. Its hook must also leave every Win64
        # nonvolatile register and all untouched SIMD registers exact.
        extra = (UC_X86_REG_RBP,) + tuple(globals()['UC_X86_REG_XMM'+str(n)] for n in range(6,16))
        for n,reg in enumerate(extra):c.uc.reg_write(reg, (1<<100)+n if reg!=UC_X86_REG_RBP else 0xFEEDBEEF)
        saved={reg:c.uc.reg_read(reg) for reg in extra}
        flags=c.uc.reg_read(UC_X86_REG_EFLAGS)
        before,after=c.run();expected=dict(before)
        if not accepted:
            expected[UC_X86_REG_RAX]=c.qvalue(before[UC_X86_REG_RCX]+0x58)
            expected[UC_X86_REG_RCX]=c.qvalue(expected[UC_X86_REG_RAX]+0x20)
        self.assertEqual(after,expected)
        self.assertEqual(saved,{reg:c.uc.reg_read(reg) for reg in extra})
        self.assertEqual(c.uc.reg_read(UC_X86_REG_EFLAGS),flags)
        self.assertEqual(c.uc.reg_read(UC_X86_REG_RSP),c.rsp)
        self.assertEqual(c.value(PRIVATE_COUNTER_OFFSET),int(accepted))
        self.assertEqual(c.stopped, MODULE+PLAN['targets']['native_query_false_epilogue']
                         if accepted else c.hook['site']+c.hook['length'])

    def test_bootstrap_heavy_accepts_real_input_and_preserves_abi(self):
        c=CPU();before,after=c.run()
        self.assertEqual(c.value(0),0x4643524F);self.assertEqual(c.value(0x74),1)
        self.assertEqual(after[UC_X86_REG_RAX],c.heavy);self.assertEqual(len(c.calls),1)
        self.assertEqual(c.uc.reg_read(UC_X86_REG_RSP),c.rsp+8)
        self.preserved(c,before,after,(UC_X86_REG_RAX,))
        for off,value in ((8,c.actor),(0x10,c.ctl),(0x18,c.target),(0x38,c.bank),(0x1A8,c.paired),
                          (0x58,c.idle),(0x1F0,c.common_idle),(0x50,c.heavy),
                          (0xC8,c.primary['owner']),(0xD0,c.secondary['owner']),
                          (0x1B0,c.primary['descriptors'][1]),(0x1B8,c.secondary['descriptors'][1])):
            self.assertEqual(c.qvalue(c.d+off),value)

    def test_distinct_hino_and_common_idle_keep_their_owned_transitions(self):
        c=CPU()
        self.assertNotEqual(c.idle,c.common_idle)
        self.assertEqual(c.qvalue(c.idle+0x38),c.native_bank)
        self.assertEqual(c.qvalue(c.common_idle+0x38),c.common)
        original_hino=bytes(c.uc.mem_read(c.idle,0x90))
        original_common=bytes(c.uc.mem_read(c.common_idle,0x90))
        original_rotation=bytes(c.uc.mem_read(c.rotation,0x30))
        original_heavy=bytes(c.uc.mem_read(c.heavy,0x30))
        c.run()
        self.assertEqual(c.uc.reg_read(UC_X86_REG_RAX),c.heavy)
        self.assertEqual(c.qvalue(c.d+0x58),c.idle)
        self.assertEqual(c.qvalue(c.d+0x1F0),c.common_idle)
        self.assertEqual(bytes(c.uc.mem_read(c.idle,0x90)),original_hino)
        self.assertEqual(bytes(c.uc.mem_read(c.common_idle,0x90)),original_common)
        self.assertEqual(bytes(c.uc.mem_read(c.rotation,0x30)),original_rotation)
        self.assertEqual(bytes(c.uc.mem_read(c.heavy,0x30)),original_heavy)

    def test_common_idle_requires_unique_enabled_owned_heavy_source(self):
        for change in (lambda c:c.u(c.common_idle,1),
                       lambda c:c.put(c.common_idle+0x40,b'\x00'),
                       lambda c:c.q(c.common_idle+0x38,c.native_bank),
                       lambda c:c.records(c.common,[c.common_idle,c.common_idle]),
                       lambda c:c.put(c.heavy+0x14,struct.pack('<h',38)),
                       lambda c:c.q(c.common_idle+0x78,0)):
            c=CPU();change(c);before,after=c.run()
            self.assertEqual(c.value(0),0);self.assertFalse(c.calls)
            self.preserved(c,before,after)

    def test_released_input_keeps_original_transition(self):
        c=CPU(pressed=False);before,after=c.run()
        self.assertEqual(c.value(0x74),0);self.assertEqual(c.value(0x78),0)
        self.preserved(c,before,after)

    def test_all_verified_head_identities_and_ready_states_are_discovered(self):
        self.assertEqual(HEAD_IDENTITIES,((0x9D1CC,10515),(0x9D1CC,12344),
            (0xA09C8,16981),(0x1DC1C,19569),(0xD16C1,11671),
            (0xD294C,17648),(0x8F795,17249),(0x9D1CC,12714)))
        for template,instance in HEAD_IDENTITIES:
            ready=3204 if template==0xA09C8 else 3205 if template==0x8F795 else 3203
            with self.subTest(template=template,instance=instance,ready=ready):
                c=CPU();c.set_head(template,instance,ready,4);before,after=c.run()
                self.assertEqual(c.value(0x74),1);self.assertEqual(c.value(0x118),ready)
                self.assertEqual(c.qvalue(c.d+0x20),c.qvalue(c.target))
                self.assertEqual(after[UC_X86_REG_RAX],c.heavy)
                self.preserved(c,before,after,(UC_X86_REG_RAX,))

    def test_head_whitelist_rejects_foreign_instances_and_cross_template_pairs(self):
        templates=tuple(dict.fromkeys(template for template,instance in HEAD_IDENTITIES))
        instances=tuple(instance for template,instance in HEAD_IDENTITIES)+(99,)
        for template in templates+(0x99999,):
            for instance in instances:
                if (template,instance) in HEAD_IDENTITIES:continue
                with self.subTest(template=template,instance=instance):
                    c=CPU();c.set_head(template,instance);before,after=c.run()
                    self.assertEqual(c.value(0),0);self.assertFalse(c.calls)
                    self.preserved(c,before,after)

    def test_head_metadata_requires_dword_alignment_and_matching_template(self):
        for offset in (0,4):
            c=CPU();c.set_head(0xA09C8,16981,3204,offset);c.run()
            self.assertEqual(c.value(0x74),1)
        for offset in (1,2,3,5,6,7):
            c=CPU();c.set_head(0xA09C8,16981,3204,offset);before,after=c.run()
            self.assertEqual(c.value(0),0);self.assertFalse(c.calls)
            self.preserved(c,before,after)
        for change in (lambda c:c.u(c.metadata,0x8F795),
                       lambda c:c.q(c.target+0xE90,0),
                       lambda c:c.q(c.target+0xE90,0x800000000000)):
            c=CPU();c.set_head(0xA09C8,16981,3204,4);change(c);before,after=c.run()
            self.assertEqual(c.value(0),0);self.assertFalse(c.calls)
            self.preserved(c,before,after)

    def test_cheap_scope_and_ownership_failures_keep_native_input(self):
        for change in (lambda c:c.u(c.actor,0),lambda c:c.u(c.actor+0xEF0,1),
                       lambda c:c.q(c.stats+0x20,0),lambda c:c.q(c.proxy,0),
                       lambda c:c.q(c.ctl+0x5B0,c.target),lambda c:c.q(c.ctl+0x640,0),
                       lambda c:c.u(c.target,0x99999),lambda c:c.q(c.tp,0),
                       lambda c:c.u(c.ready,3206),lambda c:c.u(c.params(c.ready)+0x18,0),
                       lambda c:c.u(c.metadata+0xC,0),lambda c:c.q(c.ts+0x20,2),
                       lambda c:c.put(c.temp,b'\x06'),lambda c:c.u(c.temp+4,0)):
            c=CPU();change(c);before,after=c.run();self.assertEqual(c.value(0),0)
            self.assertFalse(c.calls);self.preserved(c,before,after)

    def test_missing_or_duplicate_action_is_rejected(self):
        for change in (lambda c:c.u(c.paired,4002),lambda c:c.put(c.finish+0x40,b'\x00'),
                       lambda c:c.q(c.dispatch+0x38,c.common),
                       lambda c:c.records(c.bank,[c.dispatch,c.finish,c.paired,c.paired]),
                       lambda c:c.u(c.bank+0x130,4097)):
            c=CPU();change(c);c.run();self.assertEqual(c.value(0),0);self.assertFalse(c.calls)

    def test_native_transition_and_blend_conditions_are_required(self):
        for change in (lambda c:c.put(c.windup_transition+0x17,b'\x02'),
                       lambda c:c.put(c.paired_transition,struct.pack('<h',207)),
                       lambda c:c.put(c.terminal+0x14,struct.pack('<h',3001)),
                       lambda c:c.u(c.params(c.paired)+0x20,1200),
                       lambda c:c.u(c.params(c.paired)+0x34,5100)):
            c=CPU();change(c);c.run();self.assertEqual(c.value(0),0)

    def test_motion_pair_maps_and_both_frame_lengths_are_required(self):
        for auxiliary in (False,True):
            for kind in ('absent','index','frames','capacity'):
                c=CPU();resource=c.aux if auxiliary else c.main
                mapping=c.qvalue(resource+0x480);pairs=c.qvalue(mapping+0x10)
                if kind=='absent':c.u(pairs+16,1202)
                elif kind=='index':c.u(pairs+20,2)
                elif kind=='frames':c.put(c.qvalue(c.qvalue(resource+0x468)+8)+0x1C,struct.pack('<H',408))
                else:c.u(mapping+8,65537)
                c.run();self.assertEqual(c.value(0),0)

    def test_both_tmg_banks_and_both_ids_are_mandatory(self):
        for auxiliary in (False,True):
            for kind in ('owner','signature','missing','duplicate','badindex'):
                c=CPU();row=c.secondary if auxiliary else c.primary
                if kind=='owner':c.q(row['wrapper']+0x468,0)
                elif kind=='signature':c.put(row['bank'],b'BAD_PACK')
                elif kind=='missing':c.u(row['pairs']+16,1202)
                elif kind=='duplicate':c.put(row['pairs'],struct.pack('<Ii',1201,1))
                else:c.u(row['pairs']+20,2)
                c.run();self.assertEqual(c.value(0),0)

    def test_descriptor_schedule_span_and_frame_bounds(self):
        for change in (lambda c:c.u(c.primary['descriptors'][0]+4,18),
                       lambda c:c.u(c.primary['descriptors'][1]+8,0xFFF),
                       lambda c:c.u(c.secondary['descriptors'][1]+0x24,409),
                       lambda c:c.u(c.secondary['bank']+0x20,0xFFC),
                       lambda c:c.u(c.primary['bank']+0x30,0xFFFF)):
            c=CPU();change(c);c.run();self.assertEqual(c.value(0),0)

    def test_tree_cycles_and_outside_process_pointers_are_bounded(self):
        for change in (lambda c:c.u(c.node+0x20,2),
                       lambda c:(c.u(c.node+0x20,2),c.q(c.node,c.node)),
                       lambda c:c.q(c.package+0x190,0x800000000000),
                       lambda c:c.q(c.package+0x198,0xFFFF)):
            c=CPU();change(c);c.run();self.assertEqual(c.value(0),0)

    def test_epoch_change_and_reused_instance_rebind(self):
        for change in (lambda c:c.u(c.core+0x1C,4),
                       lambda c:c.put(c.actor+6,struct.pack('<H',2))):
            c=CPU(pressed=False);c.run();c.u(c.d+0x74,1);change(c)
            c.prepare(0);c.pressed=True;c.run();self.assertEqual(c.value(0x74),1)
            self.assertEqual(c.qvalue(c.d+0xA0),c.qvalue(c.actor))
            self.assertEqual(c.value(4),struct.unpack('<I',c.uc.mem_read(c.core+0x1C,4))[0])

    def test_active_stage_does_not_rebind_or_accept_second_input(self):
        c=CPU();c.run();c.pair();c.prepare(0);count=len(c.calls);c.run()
        self.assertEqual(len(c.calls),count);self.assertEqual(c.value(0x78),1)

    def test_action_bank_borrows_only_native_execution_chain(self):
        for ident in (3008,3491,4000):
            c=CPU(1);c.pair();c.uc.reg_write(UC_X86_REG_R10,ident)
            before,after=c.run();self.assertEqual(after[UC_X86_REG_RCX],c.bank)
            self.preserved(c,before,after,(UC_X86_REG_RCX,))
        c=CPU(1);c.uc.reg_write(UC_X86_REG_R10,38);c.run()
        self.assertEqual(c.uc.reg_read(UC_X86_REG_RCX),c.native_bank)

    def test_terminal_restores_hino_idle_and_clears_phase(self):
        c=CPU(1);c.pair(dead=True);c.uc.reg_write(UC_X86_REG_R10,3000);c.run()
        self.assertEqual(c.uc.reg_read(UC_X86_REG_R10),0)
        self.assertEqual(c.value(0x74),0);self.assertEqual(c.value(0x84),1)

    def test_both_stages_and_layers_receive_owned_motion_views(self):
        for ident in (1200,1201):
            for auxiliary in (False,True):
                for index in (2,6):
                    c=CPU(index);c.prepare(index,ident,auxiliary);before,after=c.run()
                    self.assertEqual(after[UC_X86_REG_RBX],c.aux if auxiliary else c.main)
                    self.preserved(c,before,after,(UC_X86_REG_RBX,))

    def test_null_motion_slots_keep_native_nonnull_predicate(self):
        for index in (3,5):
            c=CPU(index);c.run();self.assertFalse(c.uc.reg_read(UC_X86_REG_EFLAGS)&0x40)
            self.assertEqual(c.qvalue(c.motion+16),0)

    def test_main_and_aux_event_views_for_both_stages(self):
        for ident in (1200,1201):
            for auxiliary in (False,True):
                c=CPU(4);c.prepare(4,ident,auxiliary);before,after=c.run()
                self.assertEqual(after[UC_X86_REG_RCX],(c.secondary if auxiliary else c.primary)['owner'])
                self.preserved(c,before,after,(UC_X86_REG_RCX,))
                self.assertEqual(c.qvalue(c.manager+(0x30 if auxiliary else 0x18)),0)

    def test_zero_and_nonfinite_rays_before_and_after_native_kill(self):
        for dead in (False,True):
            for value in (1.0,float('nan'),float('inf')):
                c=CPU(7);c.pair(dead);c.put(c.end,struct.pack('<f',value));before,after=c.run()
                self.assertEqual(after[UC_X86_REG_RAX],0xFFFFFFFF);self.assertEqual(c.value(0x1D0),1)
                self.preserved(c,before,after,(UC_X86_REG_RAX,))

    def test_nonzero_finite_rays_keep_original_query(self):
        c=CPU(7);c.put(c.end,struct.pack('<f',2.0));before,after=c.run()
        self.assertEqual(c.value(0x1D0),0);self.preserved(c,before,after)

    def test_stalled_query_resumes_live_and_cleared_dead_pair(self):
        for dead in (False,True):
            c=CPU(8);c.pair(dead);raw=bytes(c.uc.mem_read(c.query,0x70));before,after=c.run()
            self.assertEqual(c.value(0x1D4),1);self.assertEqual(c.stopped,MODULE+0x216ADD)
            self.assertEqual(bytes(c.uc.mem_read(c.query,0x70)),raw);self.preserved(c,before,after)
            self.assertEqual(c.qvalue(c.d+0x1D8),c.query)

    def test_stalled_hit_foreign_caller_and_finite_query_keep_native_branch(self):
        for change in (lambda c:c.uc.reg_write(UC_X86_REG_R8,1),lambda c:c.q(c.query+0x48,c.target),
                       lambda c:c.q(c.rsp+0x238,STOP),lambda c:c.q(c.rsp+0x200,c.actor+8),
                       lambda c:c.put(c.query+0x30,struct.pack('<3f',4.0,5.0,6.0)),
                       lambda c:c.u(c.d+0x74,0)):
            c=CPU(8);change(c);c.run();self.assertEqual(c.value(0x1D4),0)

    def test_cleared_pair_requires_native_eight_deaths_and_owned_zero_hp(self):
        for change in (lambda c:c.q(c.ts+0x20,1),lambda c:c.put(c.temp,b'\x07'),
                       lambda c:c.u(c.temp+4,0),lambda c:c.q(c.tc+0x5B0,c.actor),
                       lambda c:c.q(c.enemy+0x38,c.bank)):
            c=CPU(8);c.pair(True);change(c);c.run();self.assertEqual(c.value(0x1D4),0)

    def test_pending_weapon_guard_accepts_precommit_and_bound_pair_without_bit29(self):
        for pending in ('absent','bound'):
            for template,instance in HEAD_IDENTITIES:
                ready=3204 if template==0xA09C8 else 3205 if template==0x8F795 else 3203
                with self.subTest(pending=pending,template=template,instance=instance):
                    c=CPU(9)
                    self.assertFalse(struct.unpack('<I',c.uc.mem_read(c.params(c.finish)+0x18,4))[0]&(1<<29))
                    c.set_head(template,instance,ready,4);c.q(c.d+0x20,c.qvalue(c.target))
                    c.u(c.d+0x118,ready)
                    c.q(c.ctl+0x5D8,c.target if pending=='bound' else 0)
                    c.u(c.stats+0xB0,0);c.put(c.stats+0xC0,struct.pack('<2f',700.0,700.0))
                    original_gauge=bytes(c.uc.mem_read(c.stats+0xB0,0x18))
                    self.check_weapon_guard(c,True)
                    self.assertEqual(bytes(c.uc.mem_read(c.stats+0xB0,0x18)),original_gauge)
                    self.assertEqual(c.qvalue(c.ctl+0x5D8),c.target if pending=='bound' else 0)
                    self.assertEqual(c.qvalue(c.ts+0x20),1)
                    self.assertEqual(bytes(c.uc.mem_read(c.temp,8)),b'\x07\x00\x00\x00\x01\x00\x00\x00')

    def test_pending_weapon_guard_rejects_stale_actor_and_foreign_query_callers(self):
        changes=(('phase',lambda c:c.u(c.d+0x74,0)),
                 ('magic',lambda c:c.u(c.d,0)),
                 ('epoch',lambda c:c.u(c.core+0x1C,4)),
                 ('actor_slot',lambda c:c.q(MODULE+PLAN['targets']['player_slot'],c.target)),
                 ('actor_header',lambda c:c.put(c.actor+6,struct.pack('<H',2))),
                 ('actor_not_local',lambda c:c.u(c.actor+0xEF0,1)),
                 ('actor_dead',lambda c:c.q(c.stats+0x20,0)),
                 ('proxy_owner',lambda c:c.q(c.proxy,c.target)),
                 ('controller_owner',lambda c:c.q(c.ctl+0x50,c.target)),
                 ('foreign_rdi',lambda c:c.uc.reg_write(UC_X86_REG_RDI,c.tc)),
                 ('foreign_rcx',lambda c:c.uc.reg_write(UC_X86_REG_RCX,c.tc)),
                 ('native_result_not_false',lambda c:c.uc.reg_write(UC_X86_REG_RSI,1)))
        for name,change in changes:
            with self.subTest(name=name):
                c=CPU(9);change(c);self.check_weapon_guard(c,False)

    def test_pending_weapon_guard_rejects_changed_pair_head_and_mission(self):
        changes=(('foreign_pending',lambda c:c.q(c.ctl+0x5D8,c.actor)),
                 ('active_pair',lambda c:c.q(c.ctl+0x5B0,c.target)),
                 ('lock',lambda c:c.q(c.ctl+0x640,c.actor)),
                 ('head_header',lambda c:c.put(c.target+6,struct.pack('<H',6))),
                 ('head_stats',lambda c:c.q(c.target+0x240,c.stats)),
                 ('head_stats_owner',lambda c:c.q(c.ts,c.actor)),
                 ('head_dead',lambda c:c.q(c.ts+0x20,0)),
                 ('head_hp',lambda c:c.q(c.ts+0x20,2)),
                 ('head_controller_owner',lambda c:c.q(c.tc+0x50,c.actor)),
                 ('head_not_ready',lambda c:c.q(c.tc+0x58,c.enemy)),
                 ('head_count',lambda c:c.put(c.temp,b'\x08')),
                 ('mission_uninitialized',lambda c:c.u(c.temp+4,0)),
                 ('mission_owner',lambda c:c.q(MODULE+0x189F408,c.tree)))
        for name,change in changes:
            with self.subTest(name=name):
                c=CPU(9);change(c);self.check_weapon_guard(c,False)

    def test_pending_weapon_guard_requires_exact_windup_record(self):
        for name in ('idle','paired','same_id_foreign_record'):
            with self.subTest(name=name):
                c=CPU(9)
                record=c.record(3491,c.bank,1200) if name=='same_id_foreign_record' else getattr(c,name)
                c.q(c.ctl+0x58,record);self.check_weapon_guard(c,False)

    def test_pending_weapon_guard_rejects_changed_native_weapon_resources(self):
        changes=(('finish_id',lambda c:c.u(c.finish,3492)),
                 ('finish_disabled',lambda c:c.put(c.finish+0x40,b'\x00')),
                 ('finish_owner',lambda c:c.q(c.finish+0x38,c.common)),
                 ('finish_params',lambda c:c.q(c.finish+0x20,0)),
                 ('dispatch_owner',lambda c:c.q(c.dispatch+0x38,c.common)),
                 ('package_vtable',lambda c:c.q(c.package,MODULE+0x12C5518)),
                 ('package_wrapper',lambda c:c.q(c.package+0x1B8,c.primary['wrapper'])),
                 ('wrapper_bank',lambda c:c.q(c.wrapper+0x468,c.native_bank)),
                 ('main_motion',lambda c:c.q(c.package+0x188,c.aux)),
                 ('aux_motion',lambda c:c.q(c.package+0x190,c.main)))
        for name,change in changes:
            with self.subTest(name=name):
                c=CPU(9);change(c);self.check_weapon_guard(c,False)

    def test_pending_weapon_guard_writes_only_private_counter_and_saved_stack(self):
        for pending in ('absent','bound','foreign'):
            with self.subTest(pending=pending):
                c=CPU(9);c.q(c.ctl+0x5D8,0 if pending=='absent' else c.target if pending=='bound' else c.actor)
                writes=[]
                c.uc.hook_add(UC_HOOK_MEM_WRITE,
                    lambda uc,access,at,size,value,user:writes.append((at,size)))
                self.check_weapon_guard(c,pending!='foreign')
                self.assertTrue(writes)
                for at,size in writes:
                    self.assertTrue(c.rsp-0xD8<=at and at+size<=c.rsp or
                                    c.d+PRIVATE_COUNTER_OFFSET<=at and at+size<=c.d+PRIVATE_COUNTER_OFFSET+4,
                                    (hex(at),size))

    def test_guard_layout_and_previous_beta54_execution_tail_are_preserved(self):
        self.assertEqual(len(CODE_SLOTS),10)
        self.assertEqual(CODE_SLOTS[0],(0x36000,0x2000))
        self.assertEqual(CODE_SLOTS[-1],(0x38000,0x1000))
        self.assertEqual(NATIVE_QUERY_FRAME,(0x736CB0,0x73AB00))
        self.assertEqual(NATIVE_SPANS[-1],(0x736CB0,0x3E50))
        self.assertEqual(PLAN['orochi_execution_revision'],3)
        self.assertEqual(PLAN['orochi_hook_count'],10)
        self.assertEqual(PLAN['orochi_binding_data_size'],0x200)
        self.assertFalse(PLAN['orochi_fresh_exe_gameplay_validated'])
        old=assemble(legacy_plans(PLAN)[-1],MODULE,ALLOCATION)
        current=assemble(PLAN,MODULE,ALLOCATION)
        for left,right in zip(current[72:80],old[72:80]):
            self.assertEqual(left['payload'],right['payload'])
            self.assertEqual(left['patched'],right['patched'])

    def test_all_previous71_payloads_and_sites_are_preserved_across_aslr(self):
        previous=source_plan_beta532(PLAN)
        for module in (MODULE,0x7FF600000000,0x180000000):
            for slot in (0,1,37,511):
                allocation=module+0x4000000+slot*0x10000
                current,old=assemble(PLAN,module,allocation),assemble(previous,module,allocation)
                type(self).aslr_layouts += 1
                self.assertEqual(len(current),81)
                for left,right in zip(current[:71],old):
                    self.assertEqual(left['payload'],right['payload']);self.assertEqual(left['patched'],right['patched'])
                    type(self).previous_payload_comparisons += 1
                    type(self).previous_patch_comparisons += 1
                for hook in current[71:]:self.assertLessEqual(len(hook['payload']),hook['code_capacity'])


if __name__=='__main__':unittest.main()
