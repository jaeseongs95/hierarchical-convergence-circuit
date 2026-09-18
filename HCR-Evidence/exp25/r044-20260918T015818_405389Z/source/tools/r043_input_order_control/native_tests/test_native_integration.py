"""설치된 기준선에서 실제 native 4개 smoke test. EXP24 연구 결과에 합산하지 않는다."""
from copy import deepcopy
import os
from pathlib import Path
import sys
import traceback
import unittest
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]


class NativeIntegrationTests(unittest.TestCase):
    def test_four_cells_with_independent_audit(self):
        from r043_input_order_control import sources,spec,input_audit,runtime,trajectory,baseline_audit,policy_audit,storage as io
        from r041_scheduler_direction.trial_audit import audit_trial
        source=os.environ.get('HCR_R043_SOURCE_RUN')
        output=os.environ.get('HCR_R043_NATIVE_TEST_OUT')
        self.assertIsNotNone(source,'HCR_R043_SOURCE_RUN이 필요합니다. native 검사를 skip하지 않습니다.')
        self.assertIsNotNone(output,'HCR_R043_NATIVE_TEST_OUT이 필요합니다.')
        target=Path(output);target.mkdir(parents=True,exist_ok=False)
        _,parent,seed,_,documents=sources.read_parent(source)
        cases,worlds=spec.cases(parent)
        sources.read_prior(os.environ['HCR_R043_PRIOR_RUN'],parent,cases,worlds)
        conditions=spec.conditions(parent)
        plan=dict(conditions=conditions,cases=cases,evaluation_worlds=worlds,trials=spec.trials(),
            memory_sha256=parent['memory_sha256'],config_sha256=parent['config_sha256'])
        input_audit.check_plan_inputs(plan,parent,seed)
        byname={c['name']:c for c in cases}
        inherited={(t['case'],t['scheduler']):t for t in sources.parent_regression_trials(parent)}
        completed=0
        # 102/170 같은 가설의 기대 비용을 assert하지 않는다.
        for trial in plan['trials'][:4]:
            case=deepcopy(byname[trial['case']]);case['worlds']=deepcopy(worlds[case['name']])
            active=None
            try:
                with (target/(trial['id']+'.events.jsonl')).open('x',encoding='utf-8') as stream:
                    def emit(event):
                        stream.write(io.canonical(event).decode('utf-8')+'\n');stream.flush();os.fsync(stream.fileno())
                    active=runtime.worker(case['observation'],seed['config'],seed['memory'],conditions['budget'],trial['scheduler'],emit)
                    run=active.run()
                io.put(target/(trial['id']+'.json'),dict(mode='native_integration_selftest_not_EXP24',trial=trial,run=run))
                record=audit_trial(run,trial,case,seed,conditions)
                diag=trajectory.describe(run,record,case)
                policy_audit.check(run['base'])
                self.assertFalse(diag['native_artifacts_modified'])
                if case['id_variant']=='identity':
                    old=inherited[(case['parent_case'],trial['scheduler'])]
                    baseline_audit.compare(run,documents['raw/'+old['id']+'.json'])
                io.put(target/(trial['id']+'.audit.json'),dict(record=record,diagnostics=diag))
                completed+=1
            except BaseException as exc:
                failure=dict(mode='native_integration_selftest_not_EXP24',completed=completed,error=str(exc),traceback=traceback.format_exc())
                if active is not None:
                    try: failure['partial_evidence']=active.partial_evidence()
                    except BaseException as partial: failure['partial_capture_error']=repr(partial)
                io.put(target/'failure.json',failure)
                raise
        self.assertEqual(completed,4)
        io.put(target/'selftest.json',dict(mode='native_integration_selftest_not_EXP24',completed=4,
            effect_required=False,included_in_research_population=False,verified=True))

if __name__=='__main__': unittest.main()
