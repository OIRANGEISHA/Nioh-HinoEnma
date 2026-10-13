"""Build a three-spell trial without replacing published release artifacts."""
from pathlib import Path
import argparse,hashlib,json
from build_profile import load_beta6_plan as load_plan,assemble
from hinoenma_wind_weakness_dragon import apply_wind_weakness_dragon,CHANGED_HOOKS

def build(output):
    previous=load_plan();candidate=apply_wind_weakness_dragon(previous)
    if candidate.get('wind_weakness_dragon_auxiliary_timing_guard_pending'):
        raise ValueError('Auxiliary timing validation is unfinished')
    for layout in ((0x140000000,0x144000000),(0x7FF600000000,0x7FF604000000),(0x180000000,0x176000000)):
        old,new=assemble(previous,*layout),assemble(candidate,*layout)
        if tuple(a['name'] for a,b in zip(old,new) if a['payload']!=b['payload'])!=CHANGED_HOOKS:
            raise ValueError('Unexpected trial payload changes')
        if any(a['patched']!=b['patched'] for a,b in zip(old,new)):
            raise ValueError('Native patch entries changed')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return dict(path=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                changed_hooks=CHANGED_HOOKS,hook_count=82,release_artifacts_unchanged=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(build(parser.parse_args().output)))
