"""Mandatory live native tests on the installed baseline. No skip, retry or efficacy assertion.

Four EXP25 exact-input reruns plus six separate smoke trials. None are EXP26 research trials.
"""
from copy import deepcopy
import os
from pathlib import Path
import sys
import traceback
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]


class NativeIntegrationTests(unittest.TestCase):
    def test_native_regression_and_smoke(self):
        from r045_direct_support import sources,spec,runtime,storage as io
        from r045_direct_support.trial_audit import audit_trial
        from r044_reuse_contribution.trial_audit import audit_trial as old_audit
        from r044_reuse_contribution.baseline_audit import compare
        source=os.environ.get('HCR_R045_SOURCE_RUN');output=os.environ.get('HCR_R045_NATIVE_TEST_OUT')
        self.assertIsNotNone(source,'HCR_R045_SOURCE_RUN required; native checks are not skipped')
        self.assertIsNotNone(output,'HCR_R045_NATIVE_TEST_OUT required')
        target=io.safe(output);target.mkdir(parents=True,exist_ok=False)
        completed=0;active=None;current=None
        try:
            _,parent,seed,_,documents=sources.read_parent(source)
            oldcases={c['name']:dict(deepcopy(c),worlds=deepcopy(parent['evaluation_worlds'][c['name']])) for c in parent['cases']}
            def execute_one(trial,case,conditions,mode):
                nonlocal active,current
                current=dict(trial=trial,mode=mode);active=None
                with (target/f'n{completed:04d}.events.jsonl').open('x',encoding='utf-8',newline='\n') as f:
                    def emit(event):
                        f.write(io.canonical(event).decode('utf-8')+'\n');f.flush();os.fsync(f.fileno())
                    active=runtime.worker(case['observation'],seed['config'],seed['memory'],conditions['budget'],trial['use_circuits'],emit)
                    run=active.run()
                io.put(target/f'n{completed:04d}.json',dict(mode=mode,trial=trial,run=run,included_in_research_population=False))
                return run
            for tid in sources.REGRESSION_IDS:
                old=documents['raw/'+tid+'.json'];trial=old['trial'];case=oldcases[trial['case']]
                run=execute_one(trial,case,parent['conditions'],'native_EXP25_regression_not_EXP26')
                audit=old_audit(run,trial,case,seed,parent['conditions'])
                regression=compare(run,old)
                io.put(target/f'n{completed:04d}.audit.json',dict(record=audit,regression=regression,
                    reference_experiment='EXP25',independent_new_evidence=False))
                completed+=1
            cases,worlds=spec.cases();conditions=spec.conditions(parent)
            for family in ('supported_len2','no_match_len1','conflict_len2'):
                case=deepcopy(next(c for c in cases if c['name']==family+'__identity'))
                case['worlds']=deepcopy(worlds[case['name']])
                case['observation']['episode_id']='r045-integration-smoke-not-research'
                for edge in case['observation']['edges']:edge['score']=.85 if edge['score']>0 else -.85
                for gate in (True,False):
                    trial=dict(id=f't{completed:04d}',case=case['name'],scope='route_only',arm='online_support',scheduler='input_order',use_circuits=gate)
                    run=execute_one(trial,case,conditions,'native_integration_selftest_not_EXP26')
                    record=audit_trial(run,trial,case,seed,conditions)
                    io.put(target/f'n{completed:04d}.audit.json',record)
                    # The audit checks mechanics, not whether a circuit was useful, correct or adopted.
                    self.assertFalse(record['diagnostics']['native_artifacts_modified'])
                    completed+=1
            self.assertEqual(completed,10)
            io.put(target/'selftest.json',dict(schema='hcr-r045-native-selftest-v1',verified=True,
                completed=10,parent_regression_trials=4,diagnostic_smoke_trials=6,
                included_in_research_population=False,effect_required=False,automatic_retry=False))
        except BaseException as exc:
            failure=dict(mode='native_selftest_not_EXP26',current=current,completed=completed,
                error_type=type(exc).__name__,error=str(exc),traceback=traceback.format_exc(),automatic_retry=False)
            if active is not None:
                try:
                    partial=active.partial_evidence();io.canonical(partial);failure['partial_evidence']=partial
                except BaseException as p:failure['partial_capture_error']=repr(p)
            io.put(target/'failure.json',failure)
            raise

if __name__=='__main__':unittest.main(failfast=True)
