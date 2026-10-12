"""Actual x64 CPU regression for the isolated guide-to-shore candidate."""
from pathlib import Path
from copy import deepcopy
import json,struct,sys,unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'tests')]
import hinoenma_abyss_guide as candidate
import test_abyss_runtime as fixture

BASELINE=json.loads((ROOT/'profiles/guide-baseline-beta5.5.json').read_text('utf-8'))
PLAN=candidate.candidate_plan(BASELINE)
fixture.PLAN=PLAN


class CPU(fixture.CPU):
    def __init__(self,dispatch=46):
        super().__init__()
        self.u(fixture.INFO+0x48,dispatch&0xFFFFFFFF)
        self.u(fixture.BANK+0x130,7)
        self.c.mem_write(fixture.BANK+0x58,struct.pack('<HH',16384,16384))
        self.boat_params={};self.boat_descriptors={}
        descriptor=fixture.A+0x71000
        for n,ident in enumerate((1155,1156,1157),4):
            row=candidate.ROWS[str(ident)]
            record=fixture.RECS+n*0x100;param=fixture.PARAM+n*0x100
            self.records[ident]=record;self.boat_params[ident]=param
            self.q(fixture.TABLE+n*8,record);self.u(record,ident)
            self.q(record+0x20,param);self.q(record+0x38,fixture.BANK);self.b(record+0x40,1)
            self.c.mem_write(param,bytes.fromhex(row['parameter_raw_00_a0']))
            self.c.mem_write(record+0x78,struct.pack('<QHH',fixture.TRANS,row['transition_first'],row['transition_count']))
            for t in row['transitions']:
                self.q(fixture.TRANS+t['index']*8,descriptor)
                self.c.mem_write(descriptor,bytes.fromhex(t['raw']))
                self.boat_descriptors[t['index']]=descriptor;descriptor+=0x40
        self.c.mem_write(fixture.BANK+0x88,struct.pack('<H',183))
        self.event120=fixture.A+0x73000
        event=next(e for e in candidate.ROWS['1155']['references'] if e['index']==120)
        self.q(fixture.EVENTS+120*8,self.event120)
        self.c.mem_write(self.event120,bytes.fromhex(event['raw_00_80']))
        self.clip_banks=[]
        for n in range(2):
            bank=fixture.A+0x50000+n*0x4000;keys=bank+0x1100;clips=bank+0x1200
            self.clip_banks.append(bank)
            self.q(bank+0x470,clips+40)
            for i,ident in enumerate((8,0),3):
                self.c.mem_write(keys+i*8,struct.pack('<Ii',ident,i))
                self.q(clips+i*8,bank+0x1300+i*0x40)

    def generic(self):
        self.c.reg_write(fixture.UC_X86_REG_RDI,fixture.CTL)
        self.c.reg_write(fixture.UC_X86_REG_RAX,fixture.INFO)
        self.c.reg_write(fixture.UC_X86_REG_R8,fixture.OBJ)
        self.call(0x2F000)
        return bool(self.c.reg_read(fixture.UC_X86_REG_EFLAGS)&1)

    def queued(self):
        self.c.reg_write(fixture.UC_X86_REG_RDI,fixture.CTL)
        self.call(0x2F040)
        return self.action_calls

    def continuation(self,current):
        self.q(fixture.CTL+0x58,self.records[current])
        self.b(fixture.INFO+9,0)
        self.c.reg_write(fixture.UC_X86_REG_RDI,fixture.CTL)
        self.c.reg_write(fixture.UC_X86_REG_RDX,170)
        self.call(0x2F400,2)
        return bool(self.c.reg_read(fixture.UC_X86_REG_EFLAGS)&1)


class BoatGuideTests(unittest.TestCase):
    def test_46_generic_uses_native_queue_without_early_start_or_actor_write(self):
        m=CPU();before=m.regs()
        self.assertTrue(m.generic())
        for reg,value in before.items():
            if reg==fixture.UC_X86_REG_EFLAGS:value|=1
            self.assertEqual(m.c.reg_read(reg),value,reg)
        self.assertEqual(m.value(fixture.INFO+0xA,1),0)
        self.assertEqual(m.value(fixture.OBJ+0x320),0)
        self.assertEqual(m.calls,[]);self.assertEqual(m.action_calls,[])

    def test_46_queued_preserves_full_abi_and_retains_once_before_common170(self):
        m=CPU();before=m.regs();self.assertEqual(m.queued(),[(fixture.CTL,170)])
        for reg,value in before.items():self.assertEqual(m.c.reg_read(reg),value,reg)
        self.assertEqual(m.calls,[(1,0x58E5E)])
        self.assertEqual(m.value(fixture.INFO+0xA,1),0)
        for _ in range(3):
            m.q(fixture.CTL+0x58,fixture.IDLE);m.queued()
        self.assertEqual(m.header()['acquires'],1);self.assertEqual(m.header()['duplicates'],3)
        m.cleanup();self.assertEqual(m.header()['releases'],1)
        self.assertEqual(m.header()['outstanding'],0)

    def test_10_scope_and_resource_behavior_still_passes(self):
        m=CPU(10);self.assertTrue(m.generic());self.assertEqual(m.queued(),[(fixture.CTL,170)])
        self.assertEqual(m.header()['acquires'],1)

    def test_other_dispatches_objects_kinds_and_instances_do_not_take_new_path(self):
        for dispatch in (-1,0,9,11,15,36,39,45,47):
            m=CPU(dispatch)
            self.assertFalse(m.generic(),dispatch);m.queued()
            self.assertEqual(m.action_calls,[],dispatch);self.assertEqual(m.calls,[],dispatch)
        for at,value in ((fixture.OBJ,0xEA6F),(fixture.OBJ+4,0),(fixture.OBJ+4,0x10002)):
            m=CPU();m.u(at,value);self.assertFalse(m.generic())
            m.queued();self.assertEqual(m.action_calls,[]);self.assertEqual(m.calls,[])

    def test_owner_pair_pending_completion_and_flags_refuse_new_start(self):
        mutations=[lambda m:m.q(fixture.D+0x10,fixture.A+16),
            lambda m:m.q(fixture.M+0x18A0490,fixture.A+16),
            lambda m:m.q(fixture.OBJ+0x320,fixture.A+16),
            lambda m:m.q(fixture.CTL+0x5B0,fixture.A),
            lambda m:m.q(fixture.CTL+0x5D8,fixture.A),
            lambda m:m.q(fixture.INFO,fixture.OBJ+16),
            lambda m:m.b(fixture.INFO+8,0),lambda m:m.b(fixture.INFO+9,0),
            lambda m:m.b(fixture.INFO+0xA,1),lambda m:m.u(fixture.INFO+0x4C,1)]
        for mutate in mutations:
            m=CPU();mutate(m);self.assertFalse(m.generic());m.queued()
            self.assertEqual(m.action_calls,[]);self.assertEqual(m.calls,[])
        m=CPU();m.b(fixture.CTL+0x4E9,0)
        self.assertFalse(m.generic());self.assertEqual(m.calls,[])

    def test_lower_group_enabled_family_collision_refuses_start(self):
        for group in (0x70,0x78):
            for ident in (170,1155,1156,1157):
                m=CPU();bank=fixture.A+0x79000;table=bank+0x1000;record=bank+0x2000
                m.q(fixture.CTL+group,bank);m.q(bank+0x128,table);m.u(bank+0x130,1)
                m.q(table,record);m.u(record,ident);m.b(record+0x40,1)
                self.assertFalse(m.generic(),(group,ident));m.queued()
                self.assertEqual(m.action_calls,[]);self.assertEqual(m.calls,[])
        m=CPU();bank=fixture.A+0x79000;table=bank+0x1000;record=bank+0x2000
        m.q(fixture.CTL+0x78,bank);m.q(bank+0x128,table);m.u(bank+0x130,1)
        m.q(table,record);m.u(record,1155);m.b(record+0x40,0)
        self.assertTrue(m.generic())
        for enabled in (2, 0xFF):
            m=CPU();bank=fixture.A+0x79000;table=bank+0x1000;record=bank+0x2000
            m.q(fixture.CTL+0x78,bank);m.q(bank+0x128,table);m.u(bank+0x130,1)
            m.q(table,record);m.u(record,1155);m.b(record+0x40,enabled)
            self.assertFalse(m.generic(), enabled)
            m.queued();self.assertEqual(m.action_calls,[]);self.assertEqual(m.calls,[])

    def test_10_route_does_not_require_the_new46_resources(self):
        m=CPU(10)
        m.b(m.records[1155]+0x40,0)
        m.q(fixture.EVENTS+120*8,0)
        for bank in m.clip_banks:
            for index in (3,4):m.q(bank+0x1200+index*8,0)
        self.assertTrue(m.generic())
        self.assertEqual(m.queued(),[(fixture.CTL,170)])

    def test_full_family_parameters_transitions_events_and_clip_checks(self):
        mutations=[]
        for ident in (1155,1156,1157):
            mutations.extend([lambda m,i=ident:m.b(m.records[i]+0x40,0),
                lambda m,i=ident:m.q(m.records[i]+0x38,fixture.BANK+16),
                lambda m,i=ident:m.b(m.boat_params[i]+0x9F,0),
                lambda m,i=ident:m.q(m.records[i]+0x78,fixture.TRANS+8),
                lambda m,i=ident:m.c.mem_write(m.records[i]+0x80,b'\0\0')])
        for index in (8281,8303,8325):
            mutations.append(lambda m,i=index:m.b(m.boat_descriptors[i]+47,0))
        mutations.extend([lambda m:m.b(m.event120+0x7F,0),
            lambda m:m.c.mem_write(fixture.BANK+0x88,struct.pack('<H',120)),
            lambda m:m.q(fixture.EVENTS+120*8,0)])
        for n in range(2):
            for index in (3,4):
                mutations.append(lambda m,n=n,i=index:m.q(m.clip_banks[n]+0x1200+i*8,0))
        for mutate in mutations:
            m=CPU();mutate(m);self.assertFalse(m.generic());m.queued()
            self.assertEqual(m.action_calls,[]);self.assertEqual(m.calls,[])

    def test_duplicate_common_record_is_refused(self):
        m=CPU();m.u(fixture.BANK+0x130,8);m.q(fixture.TABLE+7*8,m.records[1155])
        self.assertFalse(m.generic());m.queued();self.assertEqual(m.calls,[])

    def test_available_zero_only_allows_owned_enabled46_family_continuation(self):
        for current in (1155,1156,1157):
            m=CPU();self.assertTrue(m.continuation(current));self.assertEqual(m.calls,[])
            self.assertEqual(m.action_calls,[])
        for current in (170,73,74,75):
            m=CPU();self.assertFalse(m.continuation(current));self.assertEqual(m.calls,[])
        m=CPU();m.b(fixture.INFO+9,0);self.assertFalse(m.generic());m.queued()
        self.assertEqual(m.calls,[]);self.assertEqual(m.action_calls,[])
        m=CPU();m.q(m.records[1156]+0x38,fixture.BANK+16)
        self.assertFalse(m.continuation(1156))
        m=CPU();m.b(m.records[1156]+0x40,0)
        self.assertFalse(m.continuation(1156))

    def test_native1155_family_lookup_is_unchanged_and_170_is_scoped(self):
        m=CPU();m.c.reg_write(fixture.UC_X86_REG_RCX,fixture.CTL+0x70)
        m.c.reg_write(fixture.UC_X86_REG_RDX,170);m.c.reg_write(fixture.UC_X86_REG_R8,0)
        self.assertEqual(m.call(0x2F080),fixture.END)
        self.assertEqual(m.c.reg_read(fixture.UC_X86_REG_RAX),m.records[170])
        for wanted in (1155,1156,1157):
            m=CPU();m.c.reg_write(fixture.UC_X86_REG_RCX,fixture.CTL+0x70)
            m.c.reg_write(fixture.UC_X86_REG_RDX,wanted);m.c.reg_write(fixture.UC_X86_REG_R8,0)
            self.assertEqual(m.call(0x2F080),fixture.C+0xE806)
        for wanted in (73,74,75):
            m=CPU();m.c.reg_write(fixture.UC_X86_REG_RCX,fixture.CTL+0x70)
            m.c.reg_write(fixture.UC_X86_REG_RDX,wanted);m.c.reg_write(fixture.UC_X86_REG_R8,0)
            self.assertEqual(m.call(0x2F080),fixture.C+0xE806)

    def test_82_native_entries_81_other_payloads_menu_prefix_and_fixed_tables_9_aslr(self):
        for module in (fixture.M,0x7FF709EB0000,0x7FFA01000000):
            for delta in (0x4000000,0x5110000,0x7FD0000):
                allocation=module+delta
                old=fixture.build.assemble(BASELINE,module,allocation)
                new=fixture.build.assemble(PLAN,module,allocation)
                self.assertEqual([i for i,(a,b) in enumerate(zip(old,new)) if a['payload']!=b['payload']],[70])
                self.assertEqual([h['patched'] for h in old],[h['patched'] for h in new])
                self.assertEqual(old[70]['payload'][:5421],new[70]['payload'][:5421])
                self.assertEqual(old[70]['payload'][0x5500:0x6AB0],new[70]['payload'][0x5500:0x6AB0])
                for h in new:self.assertLessEqual(len(h['payload']),h['code_capacity'])


if __name__=='__main__':unittest.main()
