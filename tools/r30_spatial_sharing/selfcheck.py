"""Structural preparation checks only; no native tick/settle or timing run."""
from copy import deepcopy
from dataclasses import replace
from hcr.codec import plain
from hcr.model import Config
from tools.r19_cross_level.probe import programs,require
from tools.r29_research_direction.selfcheck import check as prior_check
from tools.r30_spatial_sharing.runtime import prepare,ROOT
from tools.r19_cross_level.probe import sha
def check():
    before=prior_check();cfg=Config();program,_=programs(cfg)
    entry=dict(program=plain(program),drives=dict(f0=4.,f1=4.,goal=0.),initial={g.id:.5 for g in program.groups},top_down=True,config=plain(cfg),native_source_sha256=sha(ROOT/'src/hcr/dynamics.py'))
    plan,checked,reps,alias,edges=prepare(entry,program,cfg)
    require(checked['nontrivial_classes']==1 and len(reps)==2 and len(edges)==3 and alias['f0']==alias['f1'],'fixture preparation')
    rejected={}
    for name in ['actual_program','actual_config','native_source']:
        e=deepcopy(entry);pr,c=program,cfg
        if name=='actual_program':pr=replace(program,groups=(replace(program.groups[0],bias=.1),*program.groups[1:]))
        elif name=='actual_config':c=replace(cfg,damping=.4)
        else:e['native_source_sha256']='0'*64
        try:prepare(e,pr,c)
        except ValueError as exc:rejected[name]=str(exc)
        else:raise ValueError('preparation accepted '+name)
    return dict(status='R30_STRUCTURAL_PREPARATION_PASS',prior_r29_checks=before,actual_binding_rejections=rejected,native_tick_calls=0,native_settle_calls=0,training_calls=0,world_measure_calls=0,census_pairs_executed=0,new_timing_runs=0)
