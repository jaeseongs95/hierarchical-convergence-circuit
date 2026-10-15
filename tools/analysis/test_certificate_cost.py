"""독립 analytic 경계와 봉인 후 원본 predicate/full7 비교. 궤적 재생 주장은 하지 않는다."""
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys
import time
import unittest
import termination_compare_core as core
import termination_compare_runner as runner
import termination_certificate_cost as cost


def sources():return {n:(Path(__file__).parent/n).read_text(encoding='utf-8') for n in core.LIB_PINS}
def zero_model():return {'b':['0']*7,'G':[['0']*7 for _ in range(7)],'d':'1/2'}
def point(value):return core.encode_box([(Q(value),Q(value))]+[(Q(0),Q(0))]*6)
def arithmetic():
    m=core.Meter();m.counts.update(certificate_attempts=0,prefilter_rejections=0)
    return core.Arithmetic(sources(),m)


class CertificateCostTests(unittest.TestCase):
    def test_zero_success_exact_certificate(self):
        a=arithmetic();b=point(0);expected=a.certificate(zero_model(),b)
        self.assertEqual(cost.screened_certificate(arithmetic(),zero_model(),b),expected)
        self.assertEqual(expected['bounds']['component_vector'][0]['status'],'CERTIFIED_WITHIN_EPS')

    def test_equality_must_not_screen(self):
        a=arithmetic();b=point(2*core.EPSILON);expected=a.certificate(zero_model(),b)
        self.assertEqual(expected['bounds']['component_vector'][0]['status'],'CERTIFIED_WITHIN_EPS')
        actual=cost.screened_certificate(arithmetic(),zero_model(),b)
        self.assertEqual(actual,expected)

    def test_strict_negative_screen_has_no_distance_claim(self):
        a=arithmetic();b=point(3*core.EPSILON)
        self.assertEqual(a.certificate(zero_model(),b)['bounds']['component_vector'][0]['status'],'NOT_CERTIFIED')
        optimized=arithmetic();actual=cost.screened_certificate(optimized,zero_model(),b)
        self.assertEqual(actual['screen'],'SCREENED_NOT_CERTIFIABLE')
        self.assertEqual(actual['proof'],'NOT_EVALUATED')
        self.assertEqual(optimized.meter.counts['region_proofs'],0)
        self.assertEqual(optimized.meter.counts['residual_calls'],1)
        self.assertNotIn('distance',actual)

    def test_geometry_error_not_hidden(self):
        a=arithmetic()
        with self.assertRaisesRegex(ValueError,'region geometry/grid31'):
            cost.screened_certificate(a,zero_model(),point(1))

    def test_source_pin_and_budget(self):
        bad=sources();bad[next(iter(bad))]+='\n'
        with self.assertRaisesRegex(ValueError,'arithmetic source pin'):core.Arithmetic(bad,core.Meter())
        a=arithmetic();a.meter.deadline=0
        with self.assertRaises(core.BudgetStop):cost.screened_certificate(a,zero_model(),point(0))


def verify_study(out):
    release=core.decode(sys.stdin.buffer.readline());deadline=release['deadline'];start=time.monotonic()
    def guard():
        if time.monotonic()>=deadline:raise core.BudgetStop('verification deadline')
    out=Path(out);request=core.decode((out/'cells-sealed.json').read_bytes())
    data=core.decode((out/'setup/public-input.json').read_bytes());model=runner.validate_input(data)
    import check_termination_comparison as evaluator
    assert evaluator.independent_model(data['public'])==model
    rows=request['rows'];by={r['variant']:r for r in rows}
    states={};gates={};summaries=[]
    for variant in ('F','C0','C1'):
        guard();child=out/variant;row=by[variant]
        seal=core.decode((child/'sealed-cell.json').read_bytes())
        assert seal['supervision']==row['policy_supervision']
        assert seal['supervision']['active_processes']==0
        last=runner.last_snapshot(child,seal['supervision'])
        assert last==seal['last_complete']
        states[variant]={}
        if last:
            for tick in range(last['snapshot']['tick']+1):
                guard();s=core.decode((child/f'state-{tick:06d}.json').read_bytes())
                assert s['tick']==tick and s['model_digest']==core.digest(model)
                assert s['diagnostic']==core.diagnostic(s['current_x_box'])
                states[variant][tick]=s['current_x_box']
        timings=core.decode((child/'timings.json').read_bytes()) if (child/'timings.json').exists() else None
        gates[variant]=timings['gate_attempts'] if timings else []
        final=seal['final'];evaluation=row.get('evaluation')
        if final and row['status']=='COMPLETE':
            assert timings and final['counters']==timings['counts']
            if variant!='F':
                assert len(gates[variant])==final['counters']['certificate_attempts']
                assert len(gates[variant])==last['snapshot']['tick']//core.CADENCE
                assert [g['attempt'] for g in gates[variant]]==list(range(1,len(gates[variant])+1))
                successes=[g['attempt']*core.CADENCE for g in gates[variant] if g['status']=='CERTIFIED_WITHIN_EPS']
                if final['stop_reason']=='CERTIFIED':assert successes==[last['snapshot']['tick']]
                else:assert not successes
                assert sum(g['screen'] is not None for g in gates[variant])==final['counters']['prefilter_rejections']
            else:assert not gates[variant] and final['stop_reason']=='TICK_CAP' and last['snapshot']['tick']==6144
        phase=timings['phases'] if timings else None
        wall=seal['supervision']['wall_seconds_after_report']
        known=sum(v['wall_seconds'] for v in phase.values()) if phase else None
        cpu=sum(v['cpu_seconds'] for v in phase.values()) if phase else None
        summaries.append({'variant':variant,'status':row['status'],'tick':last['snapshot']['tick'] if last else None,
            'stop_reason':final['stop_reason'] if final else row['status'],'candidate':evaluation.get('candidate') if evaluation else None,
            'candidate_correct':evaluation.get('candidate_correct') if evaluation else None,
            'distance':evaluation.get('distance') if evaluation else None,'wall_seconds':wall,
            'tree_cpu_seconds':seal['supervision'].get('tree_cpu_seconds'),'peak_job_committed_bytes':seal['supervision'].get('peak_job_committed_bytes'),
            'phases':phase,'unattributed_wall_seconds':wall-known if known is not None else None,
            'unattributed_tree_cpu_seconds':seal['supervision']['tree_cpu_seconds']-cpu if cpu is not None else None,
            'counters':final['counters'] if final else (last['snapshot']['counters'] if last else None),
            'counters_scope':'full completed' if final else 'last committed lower bound; uncommitted unknown'})
    equality=0
    for a,b in [('C0','C1'),('F','C0'),('F','C1')]:
        for tick in sorted(states[a].keys() & states[b].keys()):
            guard();assert states[a][tick]==states[b][tick],(a,b,tick);equality+=1
    numerical=core.Arithmetic(data['math_sources'],core.Meter(deadline));checks=[]
    for g in gates['C1']:
        guard();tick=g['attempt']*core.CADENCE;b=states['C1'][tick]
        assert core.digest(b)==g['state_digest']
        original=numerical.certificate(model,b);expected=original['bounds']['component_vector'][0]['status']
        assert g['status']==expected,(tick,g['status'],expected)
        if tick//16<=len(gates['C0']):
            baseline=gates['C0'][tick//16-1]
            assert baseline['state_digest']==g['state_digest'] and baseline['status']==expected
        checks.append({'tick':tick,'original_status':expected,'screen':g['screen']})
        if expected=='CERTIFIED_WITHIN_EPS':
            final=core.decode((out/'C1/final.json').read_bytes())
            assert core.canonical(final['certificate'])==core.canonical(original)
    c0=core.decode((out/'C0/sealed-cell.json').read_bytes())['final']
    c1=core.decode((out/'C1/sealed-cell.json').read_bytes())['final']
    if c0 and c1 and c0['stop_reason']=='CERTIFIED' and c1['stop_reason']=='CERTIFIED':
        assert c0['last_complete']['tick']==c1['last_complete']['tick']
        assert core.canonical(c0['certificate'])==core.canonical(c1['certificate'])
    eligible=[s for s in summaries if s['status'] in ('COMPLETE','BUDGET_INCOMPLETE') and s['candidate'] is not None]
    complete_predicates=(by['C1']['status']=='COMPLETE' and len(checks)==len(states['C1'])//core.CADENCE)
    result={'schema':'HCCCertificateCostVerification.v1','status':'PASS' if complete_predicates else 'PASS_INTEGRITY_ONLY',
            'predicate_coverage':'ALL_COMPLETED_C1_CADENCES' if complete_predicates else 'PARTIAL_OR_NOT_AVAILABLE',
            'source_model_digest':core.digest(model),
            'cells':summaries,'planned_denominator':3,'evaluable_answered':len(eligible),'correct':sum(s['candidate_correct'] is True for s in eligible),
            'full7_pairwise_state_equalities':equality,'original_C1_predicate_checks':checks,
            'original_C0_C1_success_bytes_exact':bool(c0 and c1 and c0['stop_reason']=='CERTIFIED' and c1['stop_reason']=='CERTIFIED'),
            'verification_wall_seconds':time.monotonic()-start,'no_nonlinear_prefix_replay':True,
            'independent_discovery_samples':0,'shared_numeric_helpers_trusted':True,
            'repeat_count_per_variant':1,'uncontrolled_host_load':True,'rss_and_energy':None}
    guard();runner.write_new(Path(release['out'])/'result.json',result);guard()
    print(json.dumps({'status':'PASS','state_equalities':equality,'predicate_checks':len(checks)}),flush=True)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--verify-study':verify_study(sys.argv[2])
    else:unittest.main()
