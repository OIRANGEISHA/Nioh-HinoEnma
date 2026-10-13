"""Build the four-throwable trial, preserving the prior Harakiri/dung/fan fixes."""
from pathlib import Path
import argparse,hashlib,json
from build_profile import load_beta563_plan as load_plan,assemble
from hinoenma_harakiri import apply_harakiri
from hinoenma_dung_fan import apply_dung_fan
from hinoenma_four_throwables import apply_four_throwables,CHANGED_HOOKS

def build(output):
    previous=apply_dung_fan(apply_harakiri(load_plan()));plan=apply_four_throwables(previous)
    for layout in ((0x140000000,0x144000000),(0x7FF600000000,0x7FF604000000),(0x180000000,0x176000000)):
        old,new=assemble(previous,*layout),assemble(plan,*layout)
        if tuple(a['name'] for a,b in zip(old,new) if a['payload']!=b['payload'])!=CHANGED_HOOKS:
            raise ValueError('Unexpected trial payload changes')
        if any(a['patched']!=b['patched'] for a,b in zip(old,new)):
            raise ValueError('Native patch entries changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return dict(path=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                changed_hooks=CHANGED_HOOKS,hook_count=82,release_artifacts_unchanged=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(p.parse_args().output)))
