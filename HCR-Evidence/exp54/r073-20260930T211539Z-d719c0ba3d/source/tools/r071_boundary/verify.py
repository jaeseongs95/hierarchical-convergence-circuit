"""Separate summary projection check from audited packets; no analysis imports."""
import argparse
from pathlib import Path
import sys
from hcr import codec
from tools.r050_review_boundary.common import dump, load, require, files
from tools.r050_review_boundary.audit import FORBIDDEN, candidate_measures, counter_values
from tools.r063_formation.audit import verify_execution
from tools.r064_retention.audit import reference


def main(out):
    plan=load(out/'plan.json');summary=load(out/'summary.json');ids=[]
    for row in summary['rows']:
        identity=row['id'];arm,label=identity.split('-');ids.append(identity)
        memory=load(out/'arms'/arm/'memory'/f"{plan['checkpoints'][label]}.json")
        raw=load(out/'evaluation'/identity/'inference.json');e=raw['execution']
        verify_execution(dict(config=plan['configs'][arm],limits=plan['limits']),e,
            dict(observation=plan['observation']),memory,True,'adapt','r071-'+identity)
        require(row['cost']==counter_values(e) and row['measures']==candidate_measures(e,False),'Summary cost/readout')
        require(row['assessment']==reference(e,plan['observation'],load(out/'source'/plan['world_file']))['assessment'],'Summary world assessment')
        events=e['packet']['document']['events']
        selected=[x['payload']['candidate'] for x in events if x['event']=='r02_expansion']
        require(row['selection']==selected,'Summary selected path')
        if row['pool'] is not None:
            p=row['pool'];a=next(x['payload']['activations'][0] for x in events if x['event']=='r02_pool_result')
            require(p['eligible']==a['eligible'] and p['activation']==a['activation'] and p['prior']==a['prior'],'Summary eligibility/activation')
            require(p['selected_source']==selected[0]['source'] and p['selected_edges']==selected[0]['edges'],'Summary first selection')
            cfg=plan['configs'][arm]
            require(a['eligible']==(p['stable'] and a['activation']>=cfg['activation_threshold'] and a['mismatch']<=cfg['mismatch_threshold']),'Threshold rule')
    expected=[a+'-'+m for a in plan['configs'] for m in plan['checkpoints']]
    require(ids==expected and {p.name for p in (out/'evaluation').iterdir()}==set(expected),'Exact evaluation coverage')
    require(files(out/'evaluation')==load(out/'evaluation_manifest.json')['files'],'Evaluation raw coverage')
    require(summary['native_preparation_executions']==len(plan['configs'])*len(plan['recipe'])==10 and
            summary['native_evaluation_executions']==len(expected)==4 and summary['feedback_applications']==10,'Execution/feedback accounting')
    require(summary['independent_discovery_samples']==0 and summary['pure_strength_intervention'] is False,'Claim boundary')
    require(not FORBIDDEN & set(sys.modules),'Verifier producer import')
    dump(out/'verification.json',dict(verified=True,independently_audited_cells=ids,summary_projection_verified=True,
        native_producer_imports=[],new_research_executions_in_verifier=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.out)
