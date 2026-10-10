"""Portable offline CPU and EXE/CT relocation checks; no game or process access.

Synthetic records test the published assembly ABI and private scope lifetime.
Native resource getters are explicit RET stubs. They do not establish real
native animation/resource execution; that remains the separately tested game
behavior. This file runs both in the private workspace and extracted source.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'publish/Nioh-HinoEnma' if (ROOT/'publish/Nioh-HinoEnma').is_dir() else ROOT
sys.path[:0]=[str(ROOT/'tools'),str(PUBLIC/'src'),str(ROOT/'.devdeps')]
import menu_preview_portable_integration as integrated
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from keystone import Ks,KS_ARCH_X86,KS_MODE_64
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
import unicorn.x86_const as reg

spec=importlib.util.spec_from_file_location('_portable_preview_builder',PUBLIC/'tools/build_profile.py')
portable=importlib.util.module_from_spec(spec);spec.loader.exec_module(portable)
PROFILE=PUBLIC/'profiles/steam-1.24.8.json'
LAYOUTS=((0x140000000,0x144000000),(0x140000000,0x138000000),
 (0x240000000,0x242700000),(0x240000000,0x22F100000),
 (0x450000000,0x46FA00000),(0x450000000,0x434C00000),
 (0x7FF709EB0000,0x7FF70DEF0000),(0x7FF709EB0000,0x7FF700000000),
 (0x7FF650000000,0x7FF663210000),(0x7FF650000000,0x7FF638FA0000),
 (0x7FE120000000,0x7FE12AFE0000),(0x7FE120000000,0x7FE103000000))
OWNER,ACTOR,CAMERA,WRAPPER,BODY,STATS,HINO,WILLIAM=(
 0x31000000,0x31001000,0x31004000,0x31005000,0x31006000,0x31007000,0x3100D000,0x3100E000)
IDS,IDNODE,IDVT,HANDLES,HANDLENODE,HANDLEVT=(
 0x31010000,0x31011000,0x31012000,0x31013000,0x31014000,0x31015000)
STACK_BOTTOM,STACK_TOP=0x20000000,0x20010000
GPRS=tuple(getattr(reg,'UC_X86_REG_'+n.upper()) for n in
 ('rax','rbx','rcx','rdx','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15','rsp'))
XMMS=tuple(getattr(reg,'UC_X86_REG_XMM'+str(i)) for i in range(16))
REGISTERS=GPRS+XMMS+(reg.UC_X86_REG_EFLAGS,reg.UC_X86_REG_MXCSR)
AA_NUMBER=re.compile(r'(?<![\w])(?:0x[0-9A-Fa-f]+|[0-9A-Fa-f]+)(?![\w])')
MODULE_ADDRESS=re.compile(r'nioh\.exe\+([0-9A-Fa-f]+)')
# Audited native ABI fixture, including its mode dispatcher and tail. The
# fixture is bounded and self-contained; source tests never open nioh.exe.
HEIGHT_NATIVE=bytes.fromhex(
 '4883ec388b815c010000ffc80f297424200f57f683f8090f878f000000488d15bcf57aff48988b8c82dc0a85004803caffe1'
 'f30f10354682d3000f28c60f287424204883c438c3e8c441080084c0745cf30f10356c7fd3000f28c60f287424204883c438c3'
 'f30f103517db99000f28c60f287424204883c438c3f30f10351e80d3000f28c60f287424204883c438c3'
 'f30f1035615f95000f28c60f287424204883c438c3f30f1035ccda99000f28c60f287424204883c438c3'
 '0f1f00520a8500c40a8500670a8500850a8500850a8500520a85009a0a8500af0a8500850a8500c40a8500')
HEIGHT_CALLER=bytes.fromhex('488bcfe8c5a5ffff')


def baseline():
    raw=json.loads(PROFILE.read_text('utf-8'))
    # The packaged profile is70; regenerate its frozen60 source basis using
    # the staged builder's explicit compatibility entry, not raw new ASM.
    make=getattr(portable,'source_plan_beta52',portable.source_plan)
    return make(raw)


def exe_payload(item,base,allocation):
    result=bytearray(base64.b64decode(item['template']));target=allocation+item['code_offset']
    for f in item['fixups']:
        if f['kind']==0:struct.pack_into('<Q',result,f['offset'],allocation+0xF000)
        elif f['kind']==2:struct.pack_into('<Q',result,f['offset'],base+f['target'])
        elif f['kind']==1:struct.pack_into('<i',result,f['offset'],base+f['target']-(target+f['next']))
        else:raise AssertionError('Unsupported launcher fixup kind')
    return bytes(result)


def aa_hook_sources(source,plan):
    result={}
    for i,h in enumerate(plan['hooks']):
        begin=f"HE_Prototype_Code+{h['code_offset']:X}:\n{h['name']}:\n"
        if source.count(begin)!=1:raise AssertionError('One emitted hook body required')
        start=source.index(begin)+len(begin)
        end=(f"HE_Prototype_Code+{plan['hooks'][i+1]['code_offset']:X}:\n" if i+1<len(plan['hooks'])
            else 'HE_Prototype_Data:\n')
        result[h['name']]=source[start:source.index(end,start)].strip()
    return result


def aa_payload(source,base,allocation,target):
    def number(match):
        token=match.group(0);return token.lower() if token.lower().startswith('0x') else '0x'+token.lower()
    lines=[]
    for line in source.splitlines():
        if line.startswith('db '):
            lines.append('.byte '+','.join(str(int(b,16)) for b in line[3:].split()));continue
        line=MODULE_ADDRESS.sub(lambda m:hex(base+int(m.group(1),16)),line)
        line=line.replace('HE_Prototype_Data',hex(allocation+0xF000))
        if not line.endswith(':') and ' ' in line:
            mnemonic,operands=line.split(' ',1);line=mnemonic+' '+AA_NUMBER.sub(number,operands)
        lines.append(line)
    return bytes(Ks(KS_ARCH_X86,KS_MODE_64).asm('\n'.join(lines),target)[0])


class Machine:
    """Execute final public-assembler payloads against synthetic owned records."""
    def __init__(self,plan,*,selected=0x58E5E,layout=LAYOUTS[0]):
        self.plan=plan;self.module,self.code=layout
        self.production=self.code+0xF000;self.visual=self.code+0x24000
        self.appearance=self.code+0x29000;self.scope=self.code+0x2C000
        self.cpu=Uc(UC_ARCH_X86,UC_MODE_64)
        for at,size in ((self.module,0x1A00000),(self.code,integrated.ALLOCATION_SIZE),
                (OWNER,0x20000),(STACK_BOTTOM,0x20000)):
            self.cpu.mem_map(at,size)
        self.hooks=portable.assemble(plan,self.module,self.code)[-10:]
        for h in self.hooks:self.cpu.mem_write(h['target'],h['payload'])
        self.put32(self.module+plan['targets']['native_distance'],bits(580.0))
        self.put32(self.module+plan['targets']['native_height'],bits(-55.0))
        for target in ('package_get','package_handle','gear_binder','character_ready'):
            self.cpu.mem_write(self.module+plan['targets'][target],b'\xC3')
        self.put64(self.module+plan['targets']['package_ids'],IDS)
        self.put64(IDS+0x10,IDNODE);self.put64(IDNODE+8,IDVT)
        self.put64(self.module+plan['targets']['package_handles'],HANDLES)
        self.put64(HANDLES,HANDLENODE);self.put64(HANDLENODE+8,HANDLEVT)
        self.put64(HINO+8,BODY);self.cpu.mem_write(HINO+0x160,b'\x01')
        self.selected=selected
        self.configure(selected=selected)
        self.writes=[];self.calls=[];self.injection=None;self.injection_at=None
        self.stop=0;self.reached=False

    def configure(self,*,selected=None,owner=OWNER,actor=ACTOR,wrapper=WRAPPER,body=BODY,completed=True):
        if selected is not None:self.selected=selected
        self.owner,self.actor,self.wrapper,self.body=owner,actor,wrapper,body
        self.put32(self.production,self.selected)
        self.put64(self.visual,owner);self.put32(self.visual+8,self.selected)
        self.put32(self.visual+0x14,7);self.put32(self.visual+0x18,232 if self.selected==0x58E5E else 233)
        for off in (0x28,0x2C,0x30):self.put32(self.visual+off,1)
        self.put32(self.visual+0x20,0);self.put32(self.visual+0x38,int(completed))
        self.put64(owner,self.module+self.plan['targets']['base_mode_vtable']);self.put32(owner+0x1C,int(completed))
        self.put64(self.module+self.plan['targets']['player_slot'],actor)
        self.put32(actor,100);self.put32(actor+4,0x10000)
        self.cpu.mem_write(actor+0x434,b'\0\0')
        self.put64(actor+0x18,wrapper);self.put64(wrapper,actor);self.put64(wrapper+0x188,body)
        self.put64(actor+0x240,STATS);self.put64(STATS,actor)
        self.put64(HINO+8,body)
        self.put64(CAMERA,self.module+self.plan['targets']['camera_vtable'])
        self.put32(CAMERA+0x158,4);self.put32(CAMERA+0x15C,4)
        self.put32(CAMERA+0x160,bits(1.0));self.put64(CAMERA+0x208,actor)

    def reset(self):
        for i,r in enumerate(GPRS):self.cpu.reg_write(r,0xBA00000000000000+i)
        for i,r in enumerate(XMMS):self.cpu.reg_write(r,0xABCDEF01234567899876543210ABCDEF+i)
        self.cpu.reg_write(reg.UC_X86_REG_RSP,STACK_TOP);self.cpu.reg_write(reg.UC_X86_REG_RDI,CAMERA)
        self.cpu.reg_write(reg.UC_X86_REG_EFLAGS,0xAD7);self.cpu.reg_write(reg.UC_X86_REG_MXCSR,0x1F80)

    def put32(self,at,value):self.cpu.mem_write(at,struct.pack('<I',value&0xFFFFFFFF))
    def put64(self,at,value):self.cpu.mem_write(at,struct.pack('<Q',value))
    def get32(self,at):return struct.unpack('<I',self.cpu.mem_read(at,4))[0]
    def get64(self,at):return struct.unpack('<Q',self.cpu.mem_read(at,8))[0]
    def registers(self):return {r:self.cpu.reg_read(r) for r in REGISTERS}
    def protected(self):
        return {at:bytes(self.cpu.mem_read(at,n)) for at,n in
            ((OWNER,0x20000),(self.production,0x1000),(self.visual,0x1000),
             (self.module+self.plan['targets']['player_slot'],8))}

    def trace(self,cpu,address,size,_):
        if address==self.injection_at and self.injection:
            fn,self.injection=self.injection,None;fn(self)
        if address==self.stop:self.reached=True;cpu.emu_stop();return
        targets=self.plan['targets']
        if address==self.module+targets['package_get']:
            self.calls.append('package_get');cpu.reg_write(reg.UC_X86_REG_EAX,232 if self.selected==0x58E5E else 233)
        elif address==self.module+targets['package_handle']:
            self.calls.append('package_handle');cpu.reg_write(reg.UC_X86_REG_RAX,HINO)
        elif address==self.module+targets['character_ready']:
            self.calls.append('character_ready');cpu.reg_write(reg.UC_X86_REG_EAX,1)
        elif address==self.module+targets['gear_binder']:self.calls.append('gear_binder')

    def execute(self,index):
        self.writes=[];self.calls=[];self.reached=False
        hook=self.hooks[index];self.stop=hook['site']+hook['length']
        before=self.registers()
        code=self.cpu.hook_add(UC_HOOK_CODE,self.trace)
        write=self.cpu.hook_add(UC_HOOK_MEM_WRITE,
            lambda cpu,a,at,n,v,u:self.writes.append((at,n)))
        try:self.cpu.emu_start(hook['target'],0,count=10000)
        finally:self.cpu.hook_del(code);self.cpu.hook_del(write)
        if not self.reached:raise AssertionError('Payload did not reach exact native continuation')
        return before,self.registers()

    def constructor(self,*,registered=False):
        self.reset();self.put32(self.owner+0x1C,int(registered));self.put32(self.visual+0x38,int(registered))
        self.cpu.reg_write(reg.UC_X86_REG_RSI,STATS);self.cpu.reg_write(reg.UC_X86_REG_R14,self.actor)
        self.cpu.reg_write(reg.UC_X86_REG_RDX,self.actor);self.cpu.reg_write(reg.UC_X86_REG_RCX,STATS+0x128)
        if registered:
            self.put64(STACK_TOP+0x148,self.module+self.plan['targets']['initial_stats_return'])
        else:
            frame=STACK_TOP+0x330
            for off,target in ((0x148,'initial_parameter_return'),(0x178,'reset_parameter_return'),
                    (0x1E8,'actor_reset_return'),(0x2B8,'ctor_return')):
                self.put64(STACK_TOP+off,self.module+self.plan['targets'][target])
            self.put64(STACK_TOP+0x328,self.code+self.plan['menu_visual_wrapper_continuation_offset'])
            self.put64(STACK_TOP+0x1E0,frame-0xCF)
            self.put32(frame+0x20,3);self.put64(frame+0x28,self.owner);self.put64(frame+0x30,HINO)
            self.put64(frame+0x38,self.actor);self.put64(frame+0x40,WILLIAM);self.put32(frame+0x48,self.selected)

    def complete(self):
        self.put32(self.owner+0x1C,1)
        self.reset();self.cpu.reg_write(reg.UC_X86_REG_RSI,self.owner)
        self.execute(0) # Actual frozen state1 path records completed epoch1.

    def invalidate(self):
        self.put32(self.owner+0x1C,0);self.put64(self.module+self.plan['targets']['player_slot'],0)
        self.reset();self.cpu.reg_write(reg.UC_X86_REG_RSI,self.owner)
        # Force native-fallback selection after exact state0/slot-null invalidation.
        # This avoids synthetic preload-manager setup and makes no resource claim.
        selected=self.get32(self.production);self.put32(self.production,0)
        result=self.execute(0);self.put32(self.production,selected);return result

    def camera(self,raised=False):
        self.reset()
        self.put64(STACK_TOP+0x38,self.module+self.plan['targets']['native_caller_return'])
        return self.execute(9 if raised else 8)

    def inject_second_guard(self,index,fn):
        decoded=list(Cs(CS_ARCH_X86,CS_MODE_64).disasm(self.hooks[index]['payload'],self.hooks[index]['target']))
        points=[i.address for i in decoded if i.mnemonic=='cmp' and i.op_str=='rdi, 0x10000']
        if len(points)!=2:raise AssertionError('Require two complete owned camera passes')
        self.injection_at,self.injection=points[1],fn


def bits(value):return struct.unpack('<I',struct.pack('<f',value))[0]


class PortableTests(unittest.TestCase):
    comparisons=0;cpu_comparisons=0
    @classmethod
    def setUpClass(cls):
        cls.baseline=baseline();cls.plan=integrated.apply_menu_preview(cls.baseline)
        cls.items=portable.relocation_specs(cls.plan)
        cls.ct=portable.aa_source(integrated.ct_compatible_plan(cls.plan))
        cls.ct_bodies=aa_hook_sources(cls.ct,cls.plan)

    def eq(self,a,b):self.assertEqual(a,b);type(self).comparisons+=1
    def cpu_eq(self,a,b):self.assertEqual(a,b);type(self).cpu_comparisons+=1
    def fresh(self,**options):return Machine(self.plan,**options)
    def captured(self,**options):
        m=self.fresh(**options);m.constructor();before,after=m.execute(4)
        for r in REGISTERS:self.cpu_eq(after[r],before[r])
        self.cpu_eq(m.calls,['package_get','package_handle'])
        self.cpu_eq((m.get32(m.scope+0x34),m.get32(m.scope+0x38),m.get32(m.scope+0x3C)),(1,2,0))
        m.complete();return m

    def check_camera(self,m,expected,*,raised=False,protected=True,setup=None):
        m.reset();m.put64(STACK_TOP+0x38,m.module+self.plan['targets']['native_caller_return'])
        if setup:setup(m)
        saved=m.protected() if protected else {}
        counter=0x40 if raised else 0
        old_overrides,old_fallbacks=m.get32(m.scope+counter+4),m.get32(m.scope+counter+8)
        before,after=m.execute(9 if raised else 8)
        output=reg.UC_X86_REG_XMM6 if raised else reg.UC_X86_REG_XMM2
        value=bits((-45.0 if expected else -55.0) if raised else (740.0 if expected else 580.0))
        for r in REGISTERS:self.cpu_eq(after[r],value if r==output else before[r])
        for at,raw in saved.items():self.cpu_eq(bytes(m.cpu.mem_read(at,len(raw))),raw)
        self.cpu_eq(m.calls,[])
        self.cpu_eq(m.get32(m.scope+counter+4)-old_overrides,int(expected))
        self.cpu_eq(m.get32(m.scope+counter+8)-old_fallbacks,int(not expected))
        for at,n in m.writes:
            self.assertTrue(STACK_TOP-0x70<=at and at+n<=STACK_TOP or
                m.scope+counter<=at and at+n<=m.scope+counter+0xC,f'Unexpected write {at:x}+{n:x}')
        self.cpu_eq(bytes(m.cpu.mem_read(m.scope+0xC,4)),b'\0'*4)
        self.cpu_eq(bytes(m.cpu.mem_read(m.scope+0x30,4)),b'\0'*4)

    def test_exact70_layout_and_zero_initialized_scope(self):
        self.eq(len(self.plan['hooks']),70);self.eq(self.plan['allocation_size'],0x2D000)
        self.eq(self.plan['menu_camera_scope_offset'],0x2C000)
        self.eq(self.plan['menu_camera_scope_size'],0x54)
        self.eq(len(self.plan['protected_data_pages']),6)
        self.eq(self.plan['menu_camera_scalar_initializers_required'],False)
        m=self.fresh();self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x1000)),bytes(0x1000))

    def test_first60_sources_targets_templates_and_fixups_unchanged(self):
        original=deepcopy(self.baseline);plan=integrated.apply_menu_preview(self.baseline)
        self.eq(self.baseline,original);self.eq(plan['hooks'][:60],original['hooks'])
        self.eq(portable.relocation_specs(plan)[:60],portable.relocation_specs(original))
        for k,v in original['targets'].items():self.eq(plan['targets'][k],v)

    def test12_aslr_exe_fixups_and_actual_emitted_ct_bytes_match_all70(self):
        baseline_items=portable.relocation_specs(self.baseline)
        for base,allocation in LAYOUTS:
            hooks=portable.assemble(self.plan,base,allocation)
            for i,(h,item) in enumerate(zip(hooks,self.items)):
                self.eq(h['payload'],exe_payload(item,base,allocation))
                self.eq(h['payload'],aa_payload(self.ct_bodies[h['name']],base,allocation,h['target']))
                self.assertLessEqual(len(h['payload']),h['code_capacity'])
                if i<60:self.eq(h['payload'],exe_payload(baseline_items[i],base,allocation))

    def test_no_new_fixup_kind_rip_constant_or_heap_pin(self):
        for item in self.items:
            self.assertTrue(all(f['kind'] in (0,1,2) for f in item['fixups']))
        for h in self.plan['hooks'][-2:]:
            self.assertNotIn('rip',h['asm']);self.assertNotIn('call ',h['asm'])
            self.assertIn('movss ',h['asm']);self.assertNotIn('3100',h['asm'])
        for target in ('native_distance','native_height'):
            self.assertTrue(any(f['kind']==2 and f['target']==self.plan['targets'][target]
                for item in self.items[-2:] for f in item['fixups']))

    def test_mutated_layout_source_and_scope_rejected(self):
        for field,value in (('allocation_size',0x2C000),('menu_camera_scope_offset',0x29000),
                ('menu_camera_scope_size',0x50),('menu_camera_dynamic_binding',False),('menu_camera_distance',900.0),
                ('menu_camera_height',-70.0)):
            p=deepcopy(self.plan);p[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):integrated.validate_layout(p)
        for field,value in (('rva',0x856566),('code_offset',0x2C000),('original','90 90 90 90 90'),
                ('asm',self.plan['hooks'][-1]['asm']+'\ninc rax')):
            p=deepcopy(self.plan);p['hooks'][-1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):integrated.validate_layout(p)

    def test_exact_constructor_capture_then_native_completion_all12layouts_two_variants(self):
        for layout in LAYOUTS:
            for selected in (0x58E5E,0x51BE1):
                m=self.captured(layout=layout,selected=selected)
                self.cpu_eq(tuple(m.get64(m.scope+off) for off in (0x18,0x20,0x28)),(OWNER,ACTOR,BODY))
                self.cpu_eq((m.get32(m.scope+0x10),m.get32(m.scope+0x14)),(selected,1))
                self.check_camera(m,True);self.check_camera(m,True,raised=True)

    def test_constructor_time_epoch0_rejects_camera_until_state1(self):
        for raised in (False,True):
            m=self.fresh();m.constructor();m.execute(4)
            self.cpu_eq(m.get32(m.visual+0x38),0)
            self.check_camera(m,False,raised=raised)

    def test_registered_refresh_does_not_publish_a_constructor_stamp(self):
        m=self.fresh();m.constructor(registered=True);before,after=m.execute(4)
        self.cpu_eq(m.get32(m.appearance+4),1)
        self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x54)),bytes(0x54))
        for r in REGISTERS:self.cpu_eq(before[r],after[r])
        self.check_camera(m,False)

    def test_constructor_wrong_ancestry_or_phase_cannot_stamp(self):
        for offset in (0x148,0x178,0x1E8,0x2B8,0x328,0x1E0):
            m=self.fresh();m.constructor();m.put64(STACK_TOP+offset,0)
            m.execute(4);self.cpu_eq(m.get32(m.scope+0x34),0)
        for offset,value in ((0x20,2),(0x48,0x51BE1)):
            m=self.fresh();m.constructor();m.put32(STACK_TOP+0x330+offset,value)
            m.execute(4);self.cpu_eq(m.get32(m.scope+0x34),0)

    def test_constructor_scope_publish_write_order_and_game_data_unchanged(self):
        m=self.fresh();m.constructor();saved=m.protected();m.execute(4)
        for at,raw in saved.items():self.cpu_eq(bytes(m.cpu.mem_read(at,len(raw))),raw)
        writes=[at-m.scope for at,n in m.writes if m.scope<=at<m.scope+0x54]
        self.cpu_eq(writes,[0x3C,0x34,0x38,0x10,0x14,0x18,0x20,0x28,0x4C,0x50,0x38,0x34,0x3C])
        self.cpu_eq((m.get32(m.scope+0x4C),m.get32(m.scope+0x50)),(1,1))

    def test_busy_capture_lock_leaves_existing_scope_unchanged_and_skips_no_native_binder(self):
        m=self.fresh();m.put32(m.scope+0x3C,1);saved=bytes(m.cpu.mem_read(m.scope,0x54))
        m.constructor();m.execute(4)
        self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x54)),saved)
        self.cpu_eq(m.calls,['package_get','package_handle'])

    def test_state0_slot_null_invalidation_is_once_and_releases_lock(self):
        m=self.captured();m.invalidate()
        self.cpu_eq((m.get32(m.scope+0x34),m.get32(m.scope+0x38),m.get32(m.scope+0x3C)),(0,4,0))
        m.invalidate();self.cpu_eq(m.get32(m.scope+0x38),4)

    def test_busy_invalidation_lock_falls_back_until_next_verified_invalidation(self):
        m=self.captured();m.put32(m.scope+0x3C,1);stamp=bytes(m.cpu.mem_read(m.scope,0x54))
        m.invalidate();self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x54)),stamp)
        self.check_camera(m,False)
        m.put32(m.scope+0x3C,0);m.invalidate()
        self.cpu_eq((m.get32(m.scope+0x34),m.get32(m.scope+0x3C)),(0,0))

    def test_invalidation_requires_exact_mode_state0_and_null_native_slot(self):
        for variant in ('state1','nonnull','foreignvt'):
            m=self.captured();stamp=bytes(m.cpu.mem_read(m.scope,0x54))
            m.reset();m.cpu.reg_write(reg.UC_X86_REG_RSI,OWNER)
            if variant=='nonnull':m.put32(OWNER+0x1C,0)
            if variant=='foreignvt':
                m.put64(OWNER,m.module+self.plan['targets']['base_mode_vtable']+8)
                m.put32(OWNER+0x1C,0);m.put64(m.module+self.plan['targets']['player_slot'],0)
            m.execute(0);self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x54)),stamp)

    def test_same_address_reload_invalidates_then_recaptures_new_even_generation(self):
        m=self.captured();m.invalidate();m.configure(completed=False)
        m.constructor();m.execute(4);self.cpu_eq(m.get32(m.scope+0x38),6)
        m.complete();self.check_camera(m,True);self.check_camera(m,True,raised=True)

    def test_same_address_completed_ticket_without_new_capture_remains_invalid(self):
        m=self.captured();m.invalidate();m.configure(completed=True)
        self.check_camera(m,False);self.check_camera(m,False,raised=True)

    def test_new_owner_actor_body_and_variant_refresh_requires_fresh_constructor(self):
        m=self.captured();m.invalidate()
        m.configure(selected=0x51BE1,owner=0x31008000,actor=0x31009000,wrapper=0x3100A000,body=0x3100B000,completed=False)
        m.constructor();m.execute(4);m.complete()
        self.cpu_eq(tuple(m.get64(m.scope+o) for o in (0x18,0x20,0x28)),(m.owner,m.actor,m.body))
        self.check_camera(m,True);self.check_camera(m,True,raised=True)

    def test_generation_wrap_to_zero_fails_closed_then_recovers_on_next_capture(self):
        m=self.fresh();m.put32(m.scope+0x38,0xFFFFFFFE);m.constructor();m.execute(4);m.complete()
        self.cpu_eq(m.get32(m.scope+0x38),0);self.check_camera(m,False)
        m.constructor();m.execute(4);m.complete();self.cpu_eq(m.get32(m.scope+0x38),2)
        self.check_camera(m,True)

    def test_william_unknown_and_gameplay_template_fall_back(self):
        for raised in (False,True):
            for value in (0,100,0x58E5D,0x51BE0,0xFFFFFFFF):
                m=self.captured();m.put32(m.production,value);self.check_camera(m,False,raised=raised)
            m=self.captured();m.put32(ACTOR,0x58E5E);self.check_camera(m,False,raised=raised)

    def test_foreign_camera_mode_owner_actor_and_body_fall_back(self):
        changes=((CAMERA,8,0),(CAMERA+0x158,4,0),(CAMERA+0x15C,4,3),(CAMERA+0x208,8,0x31009000),
            (OWNER+0x1C,4,0),(ACTOR+4,4,0x10001),(WRAPPER+0x188,8,0x3100B000),
            (ACTOR+0x434,1,1),(ACTOR+0x435,1,1))
        for raised in (False,True):
            for at,n,v in changes:
                m=self.captured();m.cpu.mem_write(at,v.to_bytes(n,'little'));self.check_camera(m,False,raised=raised)

    def test_invalid_inflight_or_generation_stamp_fall_back(self):
        for off,value in ((0x34,0),(0x38,0),(0x38,3),(0x3C,1),(0x14,0),(0x4C,2),(0x50,2)):
            for raised in (False,True):
                m=self.captured();m.put32(m.scope+off,value);self.check_camera(m,False,raised=raised)

    def test_second_pass_rejects_scope_receipt_or_native_identity_interleavings(self):
        changes=(lambda m:m.put32(m.scope+0x34,0),lambda m:m.put32(m.scope+0x38,4),
            lambda m:m.put32(m.scope+0x38,3),lambda m:m.put32(m.scope+0x3C,1),
            lambda m:m.put32(m.visual+0x2C,2),lambda m:m.put32(m.visual+0x30,2),
            lambda m:m.put32(m.production,0),lambda m:m.put32(OWNER+0x1C,0),
            lambda m:m.put64(WRAPPER+0x188,0x3100B000))
        for raised in (False,True):
            for fn in changes:
                m=self.captured();m.inject_second_guard(9 if raised else 8,fn)
                self.check_camera(m,False,raised=raised,protected=False)

    def test_height_exact_caller_and_positive_finite_native_scale(self):
        for bad in (0,self.plan['targets']['native_caller_return']-1,self.plan['targets']['native_caller_return']+1):
            m=self.captured();self.check_camera(m,False,raised=True,
                setup=lambda m,v=bad:m.put64(STACK_TOP+0x38,m.module+v if v else 0))
        for value in (0,0x80000000,0xBF800000,0x7F800000,0xFF800000,0x7FC00000):
            m=self.captured();m.put32(CAMERA+0x160,value);self.check_camera(m,False,raised=True)
        for value in (1,0x3F000000,0x3F800000,0x7F7FFFFF):
            m=self.captured();m.put32(CAMERA+0x160,value);self.check_camera(m,True,raised=True)

    def test_actual_height_native_caller_dispatcher_tail_returns_xmm0_restores_xmm6(self):
        for selected in (0x58E5E,0x51BE1):
            results=[]
            for altered in (False,True):
                m=self.captured(selected=selected);m.reset();before=m.registers()
                m.cpu.mem_write(m.module+0x850A20,HEIGHT_NATIVE)
                m.cpu.mem_write(m.module+0x856453,HEIGHT_CALLER)
                m.stop=m.module+0x85645B;m.reached=False
                saved_xmm6=[]
                def enter(cpu,at,size,_):
                    if at==m.module+0x850A85:
                        saved_xmm6.append(bytes(cpu.mem_read(cpu.reg_read(reg.UC_X86_REG_RSP)+0x20,16)))
                        if altered:cpu.reg_write(reg.UC_X86_REG_RIP,m.hooks[9]['target'])
                    m.trace(cpu,at,size,_)
                token=m.cpu.hook_add(UC_HOOK_CODE,enter)
                try:m.cpu.emu_start(m.module+0x856453,0,count=10000)
                finally:m.cpu.hook_del(token)
                self.assertTrue(m.reached)
                after=m.registers();results.append(after)
                self.cpu_eq(saved_xmm6,[before[reg.UC_X86_REG_XMM6].to_bytes(16,'little')])
                self.cpu_eq(after[reg.UC_X86_REG_XMM6],before[reg.UC_X86_REG_XMM6])
                self.cpu_eq(after[reg.UC_X86_REG_RSP],STACK_TOP)
                self.cpu_eq(after[reg.UC_X86_REG_XMM0],bits(-45.0 if altered else -55.0))
            for r in REGISTERS:
                if r!=reg.UC_X86_REG_XMM0:self.cpu_eq(results[1][r],results[0][r])

    def test_readonly_registered_refresh_keeps_existing_dynamic_scope(self):
        m=self.captured();stamp=bytes(m.cpu.mem_read(m.scope,0x54));m.constructor(registered=True);m.execute(4)
        self.cpu_eq(bytes(m.cpu.mem_read(m.scope,0x54)),stamp)
        self.check_camera(m,True)


def source_files():
    paths={Path(__file__).resolve(),Path(integrated.__file__).resolve(),PROFILE,PUBLIC/'tools/build_profile.py'}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if not file:continue
        path=Path(file).resolve()
        if path.suffix=='.py' and (path.is_relative_to(ROOT/'tools') or path.is_relative_to(PUBLIC/'src')):
            paths.add(path)
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def main():
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(PortableTests))
    if not result.wasSuccessful():return 1
    if '--proof' in sys.argv:
        proof=ROOT/'research/menu-preview-portable-integration-proof.json';proof.parent.mkdir(parents=True,exist_ok=True)
        paths=source_files();source=Path(integrated.__file__).resolve();test=Path(__file__).resolve()
        plan=PortableTests.plan;hooks=portable.assemble(plan,*LAYOUTS[0])[-10:]
        receipt=dict(success=True,process_access=False,game_memory_writes=False,installed=False,
            tests_run=result.testsRun,comparisons=PortableTests.comparisons,cpu_comparisons=PortableTests.cpu_comparisons,
            aslr_layouts=len(LAYOUTS),source=str(source),source_sha256=paths[str(source)],
            test_source=str(test),test_sha256=paths[str(test)],source_files=paths,
            allocation_size=integrated.ALLOCATION_SIZE,data_offset=integrated.CORE_DATA_OFFSET,
            camera_scope_offset=integrated.CAMERA_SCRATCH_OFFSET,camera_scope_size=integrated.CAMERA_SCRATCH_SIZE,
            protected_data_pages=plan['protected_data_pages'],hook_count=70,unchanged_public_hook_count=60,
            portable_fixup_kinds=[0,1,2],distance=740.0,height=-45.0,
            dynamic_exact_constructor_binding=True,zero_initialized_rw_scope=True,
            constructor_epoch0_then_native_completion1=True,generation_wrap_fails_closed=True,
            both_hino_variants=True,same_address_reload=True,readonly_game_properties=True,
            camera_memory_movss_upper96_zero=True,all_other_camera_registers_flags_mxcsr_preserved=True,
            payloads=[dict(name=h['name'],rva=h['rva'],size=len(h['payload']),
                sha256=hashlib.sha256(h['payload']).hexdigest()) for h in hooks],
            limits=['Synthetic native getters do not prove game resource execution or native object lifetime',
                'Completed current BaseMode map preview only; every in-mission menu is not claimed',
                'Two scope passes reduce transition races; they do not lock the native actor lifetime',
                'Fresh packaged EXE enable/reload remains a final user verification step'])
        proof.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:receipt[k] for k in ('tests_run','comparisons','cpu_comparisons','aslr_layouts','source_sha256','test_sha256')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
