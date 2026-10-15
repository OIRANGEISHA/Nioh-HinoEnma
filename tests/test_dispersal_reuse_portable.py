"""Released native objects may coexist; held or unrelated objects still reject."""
from copy import deepcopy
from pathlib import Path
import sys,struct,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from build_profile import load_beta612_plan as load_plan,assemble,relocation_specs
import hinoenma_sticky_dispersal_items as first
import hinoenma_dispersal_reuse as h
import test_sticky_dispersal_items_portable as old
from portable_machine import b

def released(cpu,ctl,actor,area,count=1):
    put=lambda a,v:cpu.mem_write(a,struct.pack('<Q',v))
    d=lambda a,v:cpu.mem_write(a,struct.pack('<I',v))
    sent=area;nodes=[area+0x100+i*0x600 for i in range(count)]
    put(ctl+0x720,sent);put(ctl+0x728,count)
    put(sent,nodes[0] if nodes else sent);put(sent+8,nodes[-1] if nodes else sent)
    result=[]
    for i,node in enumerate(nodes):
        att,obj=node+0x30,node+0x100
        put(node,nodes[i+1] if i+1<count else sent);put(node+8,nodes[i-1] if i else sent);put(node+0x10,att)
        put(att+8,actor);put(att+0x20,obj);put(att+0x38,0);put(att+0x40,0);d(att+0x48,1)
        d(obj,998485);d(obj+4,4|(i<<16));put(obj+0x200,actor);d(obj+0x400,22722);cpu.mem_write(obj+0x1AD,b'\1')
        result.append((node,att,obj))
    return sent,result

BaseGapFixture=old.gap.Fixture
class GapFixture(BaseGapFixture):
    def trace(self,u,at,size,user):
        raw=bytes(u.mem_read(at,size))
        if raw[:1]==b'\xe8' and at+5+struct.unpack_from('<i',raw,1)[0]==old.gap.ALLOC+h.GUARD_OFFSET:return
        super().trace(u,at,size,user)

class DispersalReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=load_plan();cls.parent=first.apply_sticky_dispersal_items(cls.base)
        cls.plan=h.apply_dispersal_reuse(cls.parent)
    def fixture(self,plan=None,cls=old.SpellLookup,count=1,layout=b.LAYOUTS[0]):
        m=cls(plan or self.plan,layout=layout)
        sent,rows=released(m.cpu,b.CONTROLLER,b.ACTOR,b.ACTOR+0x180000,count)
        return m,sent,rows
    def entry(self,m,expected):old.StickyDispersalTests().entry(m,expected)

    def test_old_rejects_released_object_new_dispatches_without_writing_it(self):
        m,_,_=self.fixture(self.parent);self.entry(m,False)
        for layout in b.LAYOUTS:
            for count in (0,1,2,16):
                m,_,_=self.fixture(count=count,layout=layout);self.entry(m,True)

    def test_live_pending_request_and_lookup_phases(self):
        for phase,pending in (('idle',1),('entry',0),('entry',1),('cast',0)):
            m,_,_=self.fixture();m.phase(phase,pending);old.StickyDispersalTests().lookup(m,True)
        for phase,pending in (('idle',0),('boss',0),('boss',1)):
            m,_,_=self.fixture();m.phase(phase,pending);old.StickyDispersalTests().lookup(m,False)
        m,_,_=self.fixture(cls=old.SpellRecast);old.recast.ItemRecastLookupTests().checked(m,True)

    def test_held_foreign_malformed_or_overfull_lists_reject(self):
        for kind in ('held','allocator','attachment_owner','attachment_state','spawn_owner','template','item','kind',
                     'uncommitted','backlink','head_cycle','tail','null_spawn','null_attachment','early_end','count','aux'):
            m,sent,rows=self.fixture();node,att,obj=rows[0]
            edits={'held':(att+0x38,obj,8),'allocator':(att+0x40,obj,8),
                'attachment_owner':(att+8,b.ACTOR+8,8),'attachment_state':(att+0x48,0,4),
                'spawn_owner':(obj+0x200,b.ACTOR+8,8),'template':(obj,1,4),'item':(obj+0x400,44930,4),
                'kind':(obj+4,0x10005,4),'uncommitted':(obj+0x1AD,0,1),
                'backlink':(node+8,node,8),'head_cycle':(node,node,8),'tail':(sent+8,sent,8),
                'null_spawn':(att+0x20,0,8),'null_attachment':(node+0x10,0,8),
                'early_end':(sent,sent,8),'count':(b.CONTROLLER+0x728,17,8),'aux':(b.CONTROLLER+0x558,obj,8)}
            at,value,width=edits[kind];m.cpu.mem_write(at,value.to_bytes(width,'little'));self.entry(m,False)

    def test_resource_callback_rechecks_existing_released_objects(self):
        for kind in ('held','owner','item','tail','count'):
            m,sent,rows=self.fixture(cls=old.SpellMachine);node,att,obj=rows[0]
            def mutate(m,name):
                if name!='clip' or m.events[-1][1]!=6:return
                if kind=='held':m.put64(att+0x38,obj)
                elif kind=='owner':m.put64(obj+0x200,b.ACTOR+8)
                elif kind=='item':m.put32(obj+0x400,44930)
                elif kind=='tail':m.put64(sent+8,sent)
                else:m.put64(b.CONTROLLER+0x728,2)
            m.mutate_on_call=mutate;m.invoke(m.code+old.spells.HELPER_OFFSET)
            self.assertFalse(any(e[0]=='dispatch' for e in m.events),kind)

    def test_released_instance_one_and_later_ids_do_not_block_the_next_cast(self):
        # Live second projectile: <IHH>=(998485, 4, 1), still the same owner/item.
        for layout in b.LAYOUTS:
            for instance in (1,2,15,65535):
                m,_,rows=self.fixture(layout=layout)
                m.put32(rows[0][2]+4,4|(instance<<16));self.entry(m,True)
                m.phase('idle',1);old.StickyDispersalTests().lookup(m,True)

    def test_other_items_keep_the_original_empty_list_requirement(self):
        for ident in (44930,64367,4998,26116):
            m=old.SpellMachine(self.plan,ident)
            released(m.cpu,b.CONTROLLER,b.ACTOR,b.ACTOR+0x180000)
            self.entry(m,False)
        m=old.JarMachine(self.plan);released(m.cpu,b.CONTROLLER,b.ACTOR,b.ACTOR+0x180000)
        self.entry(m,False)

    def test_startup_event_catchup_with_released_objects_once_only(self):
        g=old.gap
        with patch.object(g,'NEW_H',assemble(self.plan,g.BASE,g.ALLOC)):
            for count in (0,1,2,16):
                f=GapFixture(42);f.d(g.CTL+0x548,22722)
                sent,rows=released(f.u,g.CTL,g.ACT,g.ACT+0x10000,count)
                before=bytes(f.u.mem_read(g.ACT,0x20000))
                self.assertEqual(f.run(0,1),1);self.assertEqual(f.marker(),2)
                self.assertEqual(f.run(77,0),1);self.assertEqual(f.marker(),0)
                self.assertEqual(f.run(78,0),0)
                self.assertEqual(before,bytes(f.u.mem_read(g.ACT,0x20000)))
            f=GapFixture(42);f.d(g.CTL+0x548,22722)
            _,rows=released(f.u,g.CTL,g.ACT,g.ACT+0x10000)
            f.run(0,1);f.q(rows[0][1]+0x38,rows[0][2]);self.assertEqual(f.run(77,0),0)
            self.assertEqual(f.marker(),0)

    def test_prior_two_items_and_injury_regressions_remain_intact(self):
        case=old.StickyDispersalTests();case.parent=self.base;case.plan=self.plan
        with patch.object(old.gap,'Fixture',GapFixture):
            for name in ('test_observed_requests_before_reject_after_use_native172_with_abi',
                         'test_exact_definition_and_owned_request_required',
                         'test_schedule_resources_and_callback_rechecks',
                         'test_spell_lookup_and_moving_recast_never_choose_boss42',
                         'test_native_injury_routes_work_for_both_item_actions',
                         'test_dispersal_catchup_once_then_native_progress_and_interrupt_reset',
                         'test_existing_items_and_resistance_remain_accepted'):
                getattr(case,name)()

    def test_layout_parent_and_unrelated_payloads(self):
        frozen=deepcopy(self.parent);self.assertEqual(h.apply_dispersal_reuse(self.parent),self.plan);self.assertEqual(self.parent,frozen)
        for layout in b.LAYOUTS:
            changes=[]
            for old_hook,new_hook in zip(assemble(self.parent,*layout),assemble(self.plan,*layout)):
                for field in ('patched','original','site','target','code_offset','code_capacity'):self.assertEqual(old_hook[field],new_hook[field])
                if old_hook['payload']!=new_hook['payload']:changes.append(old_hook['name'])
                self.assertLessEqual(len(new_hook['payload']),new_hook['code_capacity'])
            self.assertEqual(tuple(changes),h.CHANGED)
        self.assertEqual(len(relocation_specs(self.plan)),82)

if __name__=='__main__':unittest.main()
