"""명확한 관측에서 유한 관계 문제를 전수 비교하는 개발 calibration.

길이 1~4의 경로와 두 갈래 topology의 모든 boolean 환경을 독립 reference와
비교한다. 표면 이름·edge 입력 순서가 달라도 실제 회로가 현재 값을 계산하는지
점검한다. 모든 값은 합성이고 LLM/실제 감각/범용 일반화 실험은 아니다.
"""
from pathlib import Path
from itertools import product
from dataclasses import replace
from copy import deepcopy
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from hcr.model import Mode,Feedback,Config
from hcr.runtime import Engine
from hcr.tasks.toy_world import chain,diamond
from hcr.evaluation.reference import assess
from hcr import codec


def calibration():
    counts={'chain_cases':0,'branch_cases':0,'checks':0,'failures':0,'trained_circuits':0}
    errors=[]
    for size in (1,2,3,4,'diamond'):
        n=4 if size=='diamond' else size
        make=lambda eid,values,prefix:diamond(eid,values,prefix=prefix) if size=='diamond' else chain(eid,values,prefix=prefix)
        training=Engine()
        for i in range(3):
            w=make(f'train-{size}-{i}',(True,)*n,'train-'+str(i));d=training.infer(w.observation,Mode.TRAIN);a=assess(d,w.observation,dict(w.hidden))
            training.feedback(Feedback('f-'+d.id,d.id,d.observation_digest,a.correct,a.proof_valid and a.assumption_correct is True))
        counts['trained_circuits']+=len(training.memory.circuits)
        for mask,values in enumerate(product((False,True),repeat=n)):
            counts['branch_cases' if size=='diamond' else 'chain_cases']+=1
            for kind in ('cold','warm'):
                for reverse in (False,True):
                    w=make(f'{size}-{mask}-{kind}-{reverse}',values,'새이름-'+str(mask))
                    obs=replace(w.observation,edges=tuple(reversed(w.observation.edges))) if reverse else w.observation
                    engine=Engine(memory=deepcopy(training.memory)) if kind=='warm' else Engine()
                    d=engine.infer(obs);a=assess(d,obs,dict(w.hidden));counts['checks']+=1
                    if not(a.correct is True and a.proof_valid and a.assumption_correct is True):
                        errors.append({'size':size,'values':values,'kind':kind,'reverse':reverse,'decision':d.value,'assessment':codec.plain(a)})
    counts['failures']=len(errors)
    return {'schema':'hcr-engine-calibration-r01',**counts,'errors':errors,'actual_network_calls':0,'actual_llm_calls':0,
            'scope':'46 synthetic boolean worlds × cold/warm × edge-order variants; not independent research samples'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);args=p.parse_args();result=calibration()
    if args.out:codec.save(args.out,result)
    print(codec.dumps(result));raise SystemExit(0 if result['failures']==0 else 2)
