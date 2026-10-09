"""Portable synthetic CPU tests for Beta5.1 post-defeat visual pairing.

No game binaries, process access or private snapshots are used. Resource
records are constructed from the public assembly contract. Native pairing
and recovery functions are Win64 RET stubs; the tests exercise qualification,
machine-state preservation and scoped replay, not rendered game behavior.
"""
import struct
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from build_profile import assemble
from hinoenma_postdefeat_grab import addon,STATE_OFFSET,LAYOUT
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE
from unicorn.x86_const import *

LAYOUTS=((0x140000000,0x144000000),(0x7FF600000000,0x7FF604000000),
         (0x180000000,0x176000000))
S,T,SC,TC,SS,TS,SP,TP,SM,TM,SA,SAP,R,RP,O,OP,MC,RES,CLIP,G0,G1,G2,V0,V1,V2,HASH,VCLIP=(
    0x30000000+i*0x2000 for i in range(27))
STACK=0x20008000
GP=tuple(globals()['UC_X86_REG_'+x] for x in
         ('RAX','RBX','RCX','RDX','RBP','RSI','RDI','R8','R9','R10','R11',
          'R12','R13','R14','R15','RSP','EFLAGS','MXCSR'))
XMMS=tuple(globals()['UC_X86_REG_XMM'+str(i)] for i in range(16))
REGS=GP+XMMS
VOL=tuple(globals()['UC_X86_REG_'+x] for x in ('RAX','RCX','RDX','R8','R9','R10','R11'))


def plan():
    previous=dict(tool_version='0.58-experimental',allocation_size=0x14000,
                  data_offset=0xF000,targets={},hooks=[{} for _ in range(50)])
    result=addon(previous)
    result['hooks']=result['hooks'][50:]
    return result


class Machine:
    def __init__(self,kind='candidate',layout=LAYOUTS[0],stack_offset=0,native_success=True):
        self.kind=kind;self.module,self.code=layout;self.plan=plan()
        self.data=self.code+0xF000;self.state=self.data+STATE_OFFSET
        self.hook=assemble(self.plan,*layout)[('candidate','damage','restore','heal','script').index(kind)]
        self.cpu=Uc(UC_ARCH_X86,UC_MODE_64)
        for at,size in ((self.module,0x2000000),(self.code,0x19000),
                        (S,0x80000),(0x20000000,0x10000)):
            self.cpu.mem_map(at,size)
        self.cpu.mem_write(self.hook['target'],self.hook['payload'])
        for rva in (0x741F30,0x731180,0x7B4AB0):
            self.cpu.mem_write(self.module+rva,b'\xC3')
        self.put32(self.data+4,0x58E5E);self.put64(self.data+0x10,S)
        self.put32(self.data+0x1C,7);self.put64(self.module+0x18A0490,S)
        for actor,ctl,stats,proxy,meta,ident in (
            (S,SC,SS,SP,SM,0x1000000058E5E),(T,TC,TS,TP,TM,0x2854000000028EEC)):
            self.put64(actor,ident);self.put64(actor+0x230,proxy)
            self.put64(proxy,actor);self.put64(proxy+8,ctl);self.put64(ctl+0x50,actor)
            self.put64(actor+0x240,stats);self.put64(stats,actor)
            self.put64(stats+0x108,actor);self.put64(actor+0xE90,meta)
            self.put32(meta+0xC,1)
        self.put64(SS+0x20,12345);self.put32(TS+0x10,1)
        self.put64(SC+0x58,SA);self.put64(TC+0x58,R if kind=='restore' else O)
        self.action(SA,SAP,62 if kind=='candidate' else 857,1100 if kind=='candidate' else 1101)
        self.action(R,RP,858,44000);self.action(O,OP,3158,100)
        self.put64(SC+0x670,T);self.put64(T+0x38,MC)
        self.put32(MC+0x50,1);self.put64(MC+0x38,RES)
        for index,(g,v) in enumerate(((G0,V0),(G1,V1),(G2,V2))):
            self.put64(TC+0x70+index*8,g);self.put64(g+0x128,v)
        self.records(2,[O,R]);self.put64(RES+0x480,HASH)
        self.put32(HASH+8,5);self.put64(HASH+0x10,VCLIP)
        self.put64(RES+0x468,VCLIP+0x100)
        self.cpu.mem_write(VCLIP,b'\xFF'*40)
        index=0x5168A21%5
        self.put32(VCLIP+index*8,44000);self.put32(VCLIP+index*8+4,2)
        self.put64(VCLIP+0x100+2*8,CLIP);self.put32(CLIP+0x1C,90)
        self.position(T,(100,0,0));self.put32(SC+0x40,0x135)
        for i,reg in enumerate(REGS):
            self.cpu.reg_write(reg,(1<<105)+i if reg in XMMS else 0xAABB0000+i)
        self.cpu.reg_write(UC_X86_REG_RSP,STACK+stack_offset)
        self.cpu.reg_write(UC_X86_REG_EFLAGS,0x247);self.cpu.reg_write(UC_X86_REG_MXCSR,0x3F80)
        self.cpu.reg_write(UC_X86_REG_RCX,TC if kind=='restore' else SP if kind=='heal' else SS+0x10 if kind=='script' else SC)
        self.cpu.reg_write(UC_X86_REG_RSI,SC if kind!='script' else 123456)
        self.cpu.reg_write(UC_X86_REG_RDX,100 if kind in ('heal','script') else 0)
        if kind!='candidate':
            self.bind();self.put64(SC+0x5B0,T)
        self.cpu.mem_write(STACK,b'\xCC'*0x100)
        self.calls=[];self.stop=None;self.native_success=native_success
        self.cpu.hook_add(UC_HOOK_CODE,self.trace)

    def put32(self,at,val):self.cpu.mem_write(at,struct.pack('<I',val&0xFFFFFFFF))
    def put64(self,at,val):self.cpu.mem_write(at,struct.pack('<Q',val&0xFFFFFFFFFFFFFFFF))
    def get32(self,at):return struct.unpack('<I',self.cpu.mem_read(at,4))[0]
    def get64(self,at):return struct.unpack('<Q',self.cpu.mem_read(at,8))[0]
    def position(self,actor,xyz):self.cpu.mem_write(actor+0xF0,struct.pack('<3f',*xyz))
    def action(self,record,params,action,motion):
        self.put32(record,action);self.cpu.mem_write(record+0x40,b'\1')
        self.put64(record+0x20,params);self.put32(params+0x20,motion)
    def records(self,index,records):
        g,v=((G0,V0),(G1,V1),(G2,V2))[index]
        self.put32(g+0x130,len(records))
        for i,r in enumerate(records):self.put64(v+i*8,r)
    def bind(self):
        values=dict(epoch=7,source=S,source_identity=self.get64(S),source_controller=SC,
            source_stats=SS,target=T,target_identity=self.get64(T),target_controller=TC,
            target_stats=TS,reaction=R,reaction_parameters=RP,clip=CLIP,
            original_action=O,original_parameters=OP,active=1)
        for key,value in values.items():
            (self.put32 if key in ('epoch','active') else self.put64)(self.state+LAYOUT[key],value)
    def registers(self):return {reg:self.cpu.reg_read(reg) for reg in REGS}
    def trace(self,cpu,address,size,unused):
        if address in (self.hook['site']+self.hook['length'],self.module+0x717C40):
            self.stop=address;cpu.emu_stop()
        elif address in (self.module+0x741F30,self.module+0x731180,self.module+0x7B4AB0):
            args=tuple(cpu.reg_read(r) for r in (UC_X86_REG_RCX,UC_X86_REG_RDX,UC_X86_REG_R8))
            rsp=cpu.reg_read(UC_X86_REG_RSP)
            self.calls.append((address-self.module,args,rsp))
            cpu.mem_write(rsp+8,b'\xA5'*32)
            if address==self.module+0x741F30 and self.native_success:
                self.put64(args[0]+0x5B0,args[1]);self.put32(S+0x488,1);self.put32(T+0x488,2)
            for reg in VOL:cpu.reg_write(reg,0xFEED1234)
            for reg in XMMS[:6]:cpu.reg_write(reg,(1<<110)+0xBAD)
            cpu.reg_write(UC_X86_REG_MXCSR,0x1F80);cpu.reg_write(UC_X86_REG_EFLAGS,0x202)
            cpu.reg_write(UC_X86_REG_RAX,int(self.native_success))
    def expected(self,candidate=False,restore=False,skip=False):
        before=self.registers()
        if skip:return before
        old=self.get64(SC+0x40)
        if candidate:self.put64(SC+0x40,old|0x400000)
        if restore:
            self.cpu.reg_write(UC_X86_REG_RDX,3158);self.cpu.reg_write(UC_X86_REG_R8,0)
        self.cpu.mem_write(self.hook['site'],bytes.fromhex(self.hook['original']))
        self.cpu.emu_start(self.hook['site'],self.hook['site']+self.hook['length'],count=20)
        result=self.registers()
        for reg,val in before.items():self.cpu.reg_write(reg,val)
        self.put64(SC+0x40,old);self.calls.clear();self.stop=None
        return result
    def run(self):
        self.cpu.emu_start(self.hook['target'],0,count=15000)
        if self.stop is None:raise AssertionError('No bounded continuation')


class PostDefeatPortableTests(unittest.TestCase):
    def check(self,m,*,candidate=False,restore=False,skip=False):
        expected=m.expected(candidate,restore,skip)
        actor=bytes(m.cpu.mem_read(S,0x80000));data=bytes(m.cpu.mem_read(m.data,STATE_OFFSET))
        m.run();self.assertEqual(m.registers(),expected)
        self.assertEqual(bytes(m.cpu.mem_read(m.data,STATE_OFFSET)),data)
        actual=bytes(m.cpu.mem_read(S,0x80000))
        if not candidate:self.assertEqual(actual,actor)
        else:
            allowed=bytearray(actor)
            for at,width in ((SC+0x5B0,8),(SC+0x40,8),(S+0x488,4),(T+0x488,4)):
                allowed[at-S:at-S+width]=actual[at-S:at-S+width]
            self.assertEqual(actual,bytes(allowed))
        return m
    def test_complete_spans_capacity_disjoint_slots_and_zero_initial_state(self):
        for layout in LAYOUTS:
            hooks=assemble(plan(),*layout)
            self.assertEqual([h['length'] for h in hooks],[7,7,6,5,5])
            self.assertEqual([h['code_offset'] for h in hooks],[0x14000,0x15000,0x16000,0x17000,0x18000])
            self.assertTrue(all(len(h['payload'])<0x1000 for h in hooks))
        m=Machine();self.assertEqual(m.get32(m.state+LAYOUT['active']),0)
    def test_dynamic_binding_and_native_registration_preserve_volatile_machine_state(self):
        for layout in LAYOUTS:
            for offset in (0,8,3,15):
                m=self.check(Machine(layout=layout,stack_offset=offset),candidate=True)
                self.assertEqual(m.calls[0][1],(SC,T,0));self.assertEqual(m.calls[0][2]%16,8)
                self.assertEqual(m.get32(m.state+LAYOUT['active']),1)
                self.assertEqual(m.get64(m.state+LAYOUT['target']),T)
                self.assertEqual(m.get64(m.state+LAYOUT['clip']),CLIP)
                self.assertEqual(m.get64(TS+0x20),0)
    def test_distance_rejects_nan_far_or_vertical_and_accepts_boundary(self):
        for xyz,ok in (((150,0,0),True),((150.01,0,0),False),((0,151,0),False),
                       ((float('nan'),0,0),False),((100,100,100),False),((0,0,150),True)):
            m=Machine();m.position(T,xyz);self.check(m,candidate=ok);self.assertEqual(bool(m.calls),ok)
    def test_namespace_source_liveness_ownership_and_action_are_scoped(self):
        for at,value,width in ((S,0x64,4),(S+6,2,2),(S+0xEF0,1,4),
                (SS+0x20,0,8),(SS+0x108,T,8),(SC+0x50,T,8),(SP+8,TC,8),
                (SA,0,4),(SAP+0x20,0,4),(SA+0x40,0,1)):
            m=Machine();m.cpu.mem_write(at,value.to_bytes(width,'little'))
            self.check(m);self.assertFalse(m.calls)
        for key in ('captured','native','resolved'):
            m=Machine()
            (m.put32 if key=='resolved' else m.put64)(
                m.data+4 if key=='resolved' else m.data+0x10 if key=='captured' else m.module+0x18A0490,
                0 if key=='resolved' else T)
            self.check(m);self.assertFalse(m.calls)
    def test_target_is_defeated_nouhime_owned_and_has_current_native_reference(self):
        for at,val,width in ((T,0x3ECF4,4),(T+4,1,2),(T+6,1,2),(TS+0x20,1,8),
                (TS+0x10,0,4),(TS+0x108,S,8),(TP+8,SC,8),(TC+0x50,S,8),
                (TM+0xC,0,4),(SC+0x670,S,8),(TC+0x58,R,8),(O+0x40,0,1)):
            m=Machine();m.cpu.mem_write(at,val.to_bytes(width,'little'));self.check(m)
            self.assertFalse(m.calls)
    def test_enabled_effective_reaction_must_come_from_common_group_two(self):
        for group,enabled,ok in ((0,1,False),(1,1,False),(0,0,True),(1,0,True)):
            m=Machine();alt=R+0x100;m.action(alt,RP+0x100,858,44000)
            m.cpu.mem_write(alt+0x40,bytes([enabled]));m.records(group,[alt])
            self.check(m,candidate=ok);self.assertEqual(bool(m.calls),ok)
        m=Machine();m.put32(RP+0x20,30);self.check(m);self.assertFalse(m.calls)
    def test_first_enabled_common_reaction_is_qualified_before_later_duplicate(self):
        for enabled,ok in ((1,False),(0,True)):
            m=Machine();alt=R+0x100;m.action(alt,RP+0x100,858,30)
            m.cpu.mem_write(alt+0x40,bytes([enabled]));m.records(2,[O,alt,R])
            self.check(m,candidate=ok);self.assertEqual(bool(m.calls),ok)
    def test_original_action_must_match_default_first_enabled_record_and_cleanup_flags(self):
        for altered in ('precedence','missing','pairflag'):
            m=Machine()
            if altered=='precedence':
                alt=O+0x100;m.action(alt,OP+0x100,3158,100);m.records(0,[alt])
            elif altered=='missing':m.records(2,[R])
            else:m.put64(OP+0x18,0x20000000)
            self.check(m);self.assertFalse(m.calls)
    def test_lookup_vector_counts_are_bounded_and_nulls_fail_closed(self):
        for at,val in ((G0+0x130,4097),(G2+0x130,4097),(G2+0x128,0),
                       (MC+0x50,2),(MC+0x38,0),(RES+0x480,0),
                       (HASH+8,0),(HASH+8,65537),(HASH+0x10,0),(RES+0x468,0),(CLIP+0x1C,0)):
            m=Machine();(m.put64 if at in (G2+0x128,MC+0x38,RES+0x480,HASH+0x10,RES+0x468) else m.put32)(at,val)
            self.check(m);self.assertFalse(m.calls)
    def test_selected_bank_and_non_power_two_hash_wrap_and_collision(self):
        m=Machine();m.put32(MC+0x50,0);m.put64(MC+0x18,RES)
        cap=5;start=0x5168A21%cap
        m.put32(VCLIP+start*8,123);m.put32(VCLIP+((start+1)%cap)*8,44000)
        m.put32(VCLIP+((start+1)%cap)*8+4,2)
        self.check(m,candidate=True);self.assertEqual(m.get32(m.state+LAYOUT['bank']),0)
    def test_hash_missing_full_table_and_bad_index_and_zero_clip_reject(self):
        start=0x5168A21%5
        for mode in ('missing','full','bad_index','null_clip','negative_frames'):
            m=Machine()
            if mode=='missing':m.put32(VCLIP+start*8,0xFFFFFFFF)
            elif mode=='full':
                for i in range(5):m.put32(VCLIP+i*8,1)
            elif mode=='bad_index':m.put32(VCLIP+start*8+4,5)
            elif mode=='null_clip':m.put64(VCLIP+0x110,0)
            else:m.put32(CLIP+0x1C,0xFFFFFFFF)
            self.check(m);self.assertFalse(m.calls)
    def test_existing_native_candidate_and_active_receipt_do_not_reenter(self):
        for mode in ('source','target','active','unknown'):
            m=Machine();m.bind()
            if mode=='source':m.put64(SC+0x5B0,T)
            elif mode=='target':m.put64(TC+0x5B0,S);m.put32(m.state+LAYOUT['active'],2)
            elif mode=='unknown':m.put32(m.state+LAYOUT['active'],3)
            self.check(m);self.assertFalse(m.calls)
    def test_completed_receipt_can_repeat_after_native_pair_release(self):
        m=Machine();m.bind();m.put32(m.state+LAYOUT['active'],2)
        self.check(m,candidate=True);self.assertEqual(m.get32(m.state+LAYOUT['active']),1)
    def test_new_spawn_rebinds_without_dereferencing_stale_old_target(self):
        m=Machine();m.bind();m.put64(m.state+LAYOUT['target'],0xDEAD000000)
        m.put32(m.data+0x1C,8);self.check(m,candidate=True)
        self.assertEqual(m.get32(m.state+LAYOUT['epoch']),8)
        self.assertEqual(m.get64(m.state+LAYOUT['target']),T)
    def test_new_current_source_identity_invalidates_old_active_receipt_before_rebinding(self):
        m=Machine();m.bind();m.put64(m.state+LAYOUT['source_identity'],0x1111111111111111)
        m.put64(m.state+LAYOUT['target'],0xDEAD000000)
        self.check(m,candidate=True)
        self.assertEqual(m.get64(m.state+LAYOUT['source_identity']),m.get64(S))
    def test_native_registration_rejection_does_not_publish_acceptance_token(self):
        m=Machine(native_success=False);self.check(m)
        self.assertEqual(len(m.calls),1);self.assertEqual(m.get32(m.state+LAYOUT['active']),0)
        self.assertEqual(m.get32(m.state+LAYOUT['candidate_successes']),0)
    def test_damage_suppresses_only_zero_hp_bound_native_candidate(self):
        for token in (1,2):
            m=Machine('damage');m.put32(m.state+LAYOUT['active'],token)
            self.check(m,skip=True);self.assertEqual(m.stop,m.module+0x717C40)
            self.assertEqual(m.get32(m.state+LAYOUT['damage_skips']),1)
    def test_live_target_or_foreign_source_damage_remains_native(self):
        for at,val in ((TS+0x20,1),(S,0x64),(SA,62),(SAP+0x20,1100),(SC+0x5B0,S)):
            m=Machine('damage');m.put64(at,val);self.check(m)
            self.assertEqual(m.get32(m.state+LAYOUT['damage_skips']),0)
    def test_stale_target_without_current_candidate_never_gets_dereferenced(self):
        for kind in ('damage','heal','script'):
            m=Machine(kind);m.put64(m.state+LAYOUT['target'],0xDEAD000000)
            m.put64(SC+0x5B0,0);self.check(m)
        m=Machine('restore');m.put64(m.state+LAYOUT['target_controller'],0xDEAD000000)
        m.put64(m.state+LAYOUT['target'],0xDEAD002000);self.check(m)
    def test_same_spawn_native_candidate_replacement_rejects_stale_saved_identity(self):
        for kind in ('damage','heal','script'):
            m=Machine(kind);m.put64(m.state+LAYOUT['target'],0xDEAD000000)
            m.put64(SC+0x5B0,S);self.check(m)
        m=Machine('restore');m.put64(TC+0x50,S)
        m.put64(m.state+LAYOUT['target'],0xDEAD000000);self.check(m)
    def test_restore_after_released_source_candidate_rewrites_only_target_request(self):
        m=Machine('restore');m.put64(SC+0x5B0,0);m.put32(SA,0)
        m.cpu.reg_write(UC_X86_REG_R8,0xFADE1234);self.check(m,restore=True)
        self.assertEqual(m.cpu.reg_read(UC_X86_REG_RDX),3158)
        self.assertEqual(m.cpu.reg_read(UC_X86_REG_R8),0)
        self.assertEqual(m.get32(m.state+LAYOUT['active']),2)
    def test_restore_incoming_858_ordinary_controller_or_unloaded_pose_stays_native(self):
        for mode in ('858','source','owner','original','live','token'):
            m=Machine('restore')
            if mode=='858':m.cpu.reg_write(UC_X86_REG_RDX,858)
            elif mode=='source':m.cpu.reg_write(UC_X86_REG_RCX,SC)
            elif mode=='owner':m.put64(TC+0x50,S)
            elif mode=='original':m.cpu.mem_write(O+0x40,b'\0')
            elif mode=='live':m.put64(TS+0x20,1)
            else:m.put32(m.state+LAYOUT['active'],2)
            self.check(m);self.assertEqual(m.get32(m.state+LAYOUT['restores']),0)
    def test_both_scoped_healing_call_paths_are_suppressed_without_changing_arguments(self):
        for kind in ('heal','script'):
            for token in (1,2):
                m=Machine(kind);m.put32(m.state+LAYOUT['active'],token)
                self.check(m,skip=True);self.assertFalse(m.calls)
                self.assertEqual(m.get32(m.state+LAYOUT['heal_skips']),1)
                self.assertEqual(m.get64(SS+0x20),12345)
    def test_heal_other_source_component_live_target_and_wrong_action_replay_native_call(self):
        for kind in ('heal','script'):
            for mode in ('argument','live','action','epoch','receipt'):
                m=Machine(kind)
                if mode=='argument':m.cpu.reg_write(UC_X86_REG_RCX,TP if kind=='heal' else TS+0x10)
                elif mode=='live':m.put64(TS+0x20,1)
                elif mode=='action':m.put32(SA,62)
                elif mode=='epoch':m.put32(m.data+0x1C,8)
                else:m.put32(m.state+LAYOUT['active'],0)
                self.check(m);self.assertEqual(len(m.calls),1)
                self.assertEqual(m.get32(m.state+LAYOUT['heal_skips']),0)
    def test_script_site_does_not_assume_rsi_is_the_controller(self):
        m=Machine('script');m.cpu.reg_write(UC_X86_REG_RSI,0xDEAD000000)
        self.check(m,skip=True);self.assertFalse(m.calls)
    def test_spawn_change_refuses_saved_binding_before_target_access_in_all_later_hooks(self):
        for kind in ('damage','restore','heal','script'):
            m=Machine(kind);m.put32(m.data+0x1C,8)
            m.put64(m.state+LAYOUT['target'],0xDEAD000000);self.check(m)


if __name__=='__main__':unittest.main()
