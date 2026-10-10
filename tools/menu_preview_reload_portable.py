"""Portable Beta5.3.1: preserve 68 entries and relocate the verified reload trio."""
from copy import deepcopy
import re
import menu_preview_portable_integration as previous
import menu_preview_reload_sources as sources

VERSION='1.0.0-beta.5.3.1'
CORE_DATA_OFFSET=0xF000
RELOAD_DATA_OFFSET=0x35000
ALLOCATION_SIZE=0x36000
AURA_CODE_OFFSET,AURA_CAPACITY=0x2D000,0x7000
PROTECTED_DATA_PAGES=previous.PROTECTED_DATA_PAGES+((RELOAD_DATA_OFFSET,ALLOCATION_SIZE),)
PRIVATE=re.compile(r'(?m)^mov (r(?:ax|cx|dx|bx|bp|si|di|[89]|1[0-5])), '
    r'\{(data|height_data|aura_data|production_data|visual_data|appearance_data)\}$')
TOKEN=re.compile(r'\{(data|height_data|aura_data|production_data|visual_data|appearance_data)\}')


def bind(source):
    offsets=dict(data=RELOAD_DATA_OFFSET,height_data=RELOAD_DATA_OFFSET+0x30,
        aura_data=RELOAD_DATA_OFFSET+0x80,production_data=CORE_DATA_OFFSET,
        visual_data=previous.SCRATCH_OFFSET,appearance_data=previous.APPEARANCE_SCRATCH_OFFSET)
    if len(PRIVATE.findall(source))!=len(TOKEN.findall(source)):
        raise ValueError('Every private address must use an audited register MOV')
    def replace(match):
        register,name=match.groups();delta=offsets[name]-CORE_DATA_OFFSET
        return f'mov {register}, {{data}}'+(f'\nadd {register}, {hex(delta)}' if delta else '')
    return PRIVATE.sub(replace,source)


def new_sources():
    return tuple(bind(x) for x in (sources.camera_asm(),sources.camera_asm(raised=True),sources.aura_asm()))


def apply_menu_preview(baseline):
    p=previous.apply_menu_preview(baseline)
    raw=new_sources()
    for h,source in zip(p['hooks'][-2:],raw[:2]):h['asm']=source
    for name,rva in sources.frozen_aura.TARGET_RVAS.items():
        if name in p['targets'] and p['targets'][name]!=rva:raise ValueError('Conflicting native aura target')
        p['targets'][name]=rva
    p['hooks'].append(dict(name='HE_MapPreviewAuraCopiedHash',rva=0x8C59AF,length=5,
        original='E8 CC BB F7 FF',code_offset=AURA_CODE_OFFSET,code_capacity=AURA_CAPACITY,
        asm=raw[2],purpose='Native Hino preview aura99048 once per completed current generation'))
    p.update(tool_version=VERSION,allocation_size=ALLOCATION_SIZE,
        protected_data_pages=[list(x) for x in PROTECTED_DATA_PAGES],menu_preview_revision=2,
        menu_reload_data_offset=RELOAD_DATA_OFFSET,menu_reload_data_size=0xB0,
        menu_aura_revision=1,menu_aura_action_id=99048,menu_aura_effect_id=8040,
        menu_camera_reload_revision=1,menu_camera_generation_checked=True,
        menu_aura_copied_hash_pairs_verified=True,menu_aura_fresh_exe_validation_pending=True,
        stage='local_beta531_menu_reload')
    validate_layout(p)
    return p


def validate_layout(p):
    if (len(p.get('hooks',()))!=71 or p.get('tool_version')!=VERSION
        or p.get('allocation_size')!=ALLOCATION_SIZE or p.get('data_offset')!=CORE_DATA_OFFSET
        or p.get('menu_reload_data_offset')!=RELOAD_DATA_OFFSET or p.get('menu_reload_data_size')!=0xB0
        or p.get('menu_camera_distance')!=740.0 or p.get('menu_camera_height')!=-45.0
        or tuple(map(tuple,p.get('protected_data_pages',())))!=PROTECTED_DATA_PAGES):
        raise ValueError('Exact portable71 layout required')
    old=deepcopy(p);old['hooks']=old['hooks'][:70]
    old.update(allocation_size=previous.ALLOCATION_SIZE,
        protected_data_pages=[list(x) for x in previous.PROTECTED_DATA_PAGES])
    delta=old['menu_visual_core_relative_continuation_delta']
    for h,source in zip(old['hooks'][-2:],previous._sources(delta)[8:]):h['asm']=source
    previous.validate_layout(old)
    if tuple(h['asm'] for h in p['hooks'][-3:])!=new_sources():raise ValueError('Verified reload assembly differs')
    aura=p['hooks'][-1]
    if tuple(aura[k] for k in ('name','rva','length','original','code_offset','code_capacity'))!=(
        'HE_MapPreviewAuraCopiedHash',0x8C59AF,5,'E8 CC BB F7 FF',AURA_CODE_OFFSET,AURA_CAPACITY):
        raise ValueError('Exact aura entry required')
    for name,rva in sources.frozen_aura.TARGET_RVAS.items():
        if p['targets'].get(name)!=rva:raise ValueError('Native aura target differs')
    ranges=[]
    for h in p['hooks']:
        start,end=h['code_offset'],h['code_offset']+h['code_capacity']
        if start<0 or end>ALLOCATION_SIZE or any(max(start,a)<min(end,b) for a,b in PROTECTED_DATA_PAGES):
            raise ValueError('Code overlaps protected scratch')
        ranges.append((start,end))
    ranges.sort()
    if any(a[1]>b[0] for a,b in zip(ranges,ranges[1:])):raise ValueError('Code capacity overlap')
    sites=sorted((h['rva'],h['rva']+h['length']) for h in p['hooks'])
    if any(a[1]>b[0] for a,b in zip(sites,sites[1:])):raise ValueError('Native entry overlap')


def ct_compatible_plan(p):
    if len(p['hooks'])==70:return previous.ct_compatible_plan(p)
    validate_layout(p)
    converted=deepcopy(p)
    for h in converted['hooks']:
        h['asm']='\n'.join(line if line.lstrip().startswith('.byte ') else
            previous.frozen.SOURCE_NUMBER.sub(lambda m:hex(int(m.group(0),
                16 if m.group(0).lower().startswith('0x') else 10)),line) for line in h['asm'].split('\n'))
    return converted
