"""독립 합성 oracle와 실행 경계 검사. 실제 연구 셀/원 궤적을 실행하지 않는다."""
from fractions import Fraction as Q
from decimal import Decimal, localcontext
from pathlib import Path
import unittest
from unittest.mock import patch
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import termination_compare_core as core

ROOT = Path(__file__).resolve().parent


def arithmetic(meter=None):
    return core.Arithmetic({n: (ROOT/n).read_text(encoding='utf-8')
                            for n in core.LIB_PINS}, meter or core.Meter())


def zero_model(d=Q(1,2)):
    return {'b':['0']*7, 'G':[['0']*7 for _ in range(7)], 'd':str(d)}


def point(x=Q(0)):
    return core.encode_box([(x,x)]*7)


class CoreChecks(unittest.TestCase):
    def test_outward_negative_and_domain(self):
        x = Q(-1,3)
        self.assertLessEqual(Q(core.grid(x)),x)
        self.assertGreaterEqual(Q(core.grid(x,True)),x)
        self.assertEqual(core.grid(0),'0.'+'0'*30)
        with self.assertRaises(ValueError): core.parse_box(point()[:5])
        with self.assertRaises(ValueError): core.parse_box(point(Q(2)))
        with self.assertRaises(ValueError): core.decode('{"x":NaN}')
        with self.assertRaises(ValueError): core.decode('{"x":1,"x":2}')

    def test_sequential_full7_linear_golden(self):
        a=arithmetic(); box=point(Q(2,5))
        for tick in range(1,5):
            box=a.step(zero_model(),box)
            expected=Q(2,5)/2**tick
            self.assertTrue(all(lo<=expected<=hi for lo,hi in core.parse_box(box)))
        self.assertEqual(a.meter.counts['real_map_steps'],4)
        self.assertEqual(a.meter.counts['real_coordinate_updates'],28)
        self.assertEqual(a.meter.counts['interval_matrix_terms'],196)

    def test_nonlinear_signed_bounds_independent_decimal_oracle(self):
        a=arithmetic();m=zero_model(Q(1));m['G'][0][1]='-2'
        box=point();box[1]=[core.grid(Q(1,5)),core.grid(Q(3,10))]
        result=core.parse_box(a.step(m,box))
        with localcontext() as ctx:
            ctx.prec=80
            def reference(s):
                e=(2*Decimal(s)).exp();return Q((e-1)/(e+1))
            self.assertLessEqual(result[0][0],reference('-.6'))
            self.assertGreaterEqual(result[0][1],reference('-.4'))
        self.assertGreater(a.meter.counts['taylor_calls'],0)
        self.assertTrue(all(lo<=0<=hi for lo,hi in result[1:]))

    def test_source_pin_and_pure_information_barrier(self):
        sources={n:(ROOT/n).read_text(encoding='utf-8') for n in core.LIB_PINS}
        sources[next(iter(sources))]+='\n'
        with self.assertRaises(ValueError): core.Arithmetic(sources,core.Meter())
        a=arithmetic()
        self.assertNotIn('ACTUAL_FIRST',a.local.__globals__)
        self.assertNotIn('TICKS',a.local.__globals__)
        self.assertNotIn('open',a.local.__globals__['__builtins__'])
        with patch('builtins.open',side_effect=AssertionError('IO leaked')), \
             patch.object(Path,'read_bytes',side_effect=AssertionError('IO leaked')):
            r=a.certificate(zero_model(),point())
        self.assertEqual(r['bounds']['component_vector'][0]['status'],'CERTIFIED_WITHIN_EPS')
        self.assertEqual(r['bounds']['component_vector'][0]['E_p_exact'],'0')

    def test_comparison_epsilon_boundary_and_invalid_inverse(self):
        solve=arithmetic().local.__globals__['solve_comparison']
        k=[[Q(0)]*7 for _ in range(7)];k[0][0]=Q(1,2)
        v=solve(k,[Q(1,1000000)]+[Q(0)]*6)
        self.assertEqual(v[0]/2,core.EPSILON)
        for bad in (Q(1),Q(-1,2)):
            k[0][0]=bad
            with self.assertRaises(ValueError): solve(k,[Q(1)]+[Q(0)]*6)

    def test_budget_mid_coordinate_does_not_complete_step(self):
        calls=[0]
        def clock(): calls[0]+=1;return calls[0]
        m=core.Meter(deadline=5,clock=clock);a=arithmetic(m)
        model=zero_model();model['b']=['1']*7
        with self.assertRaises(core.BudgetStop): a.step(model,point())
        self.assertEqual(m.counts['real_map_steps'],0)
        self.assertGreater(m.counts['taylor_calls'],0)

    def test_legacy_small_delta_is_not_distance_proof(self):
        legacy=core.Legacy(); p=Q(1,2);older=None;prev=point()
        for tick in range(1,17):
            p=(1-Q(1,10**7))*p+Q(1,10**7)
            now=point(2*p-1);result=legacy.update(tick,prev,now,older)
            if tick<16:self.assertIsNone(result['status'])
            older,prev=prev,now
        self.assertEqual(result['status'],'stable_ambiguous')
        self.assertGreater(1-p,Q(49,100))

    def test_legacy_reset_no_latch_and_two_cycle(self):
        l=core.Legacy();old=point(Q(1,2));prev=old
        for tick in range(1,15):l.update(tick,prev,prev,old)
        jumped=point(Q(3,5));r15=l.update(15,prev,jumped,old)
        self.assertEqual(r15['residual_p_interval'],['1/20','1/20'])
        r=l.update(16,jumped,point(Q(61,100)),prev)
        self.assertEqual(l.stable,0);self.assertIsNone(r['status'])
        l=core.Legacy();l.stable=0
        r=l.update(16,point(Q(-1,2)),point(Q(1,2)),point(Q(1,2)))
        self.assertEqual(r['status'],'oscillating')
        l.stable=4
        r=l.update(16,point(Q(1,2)),point(Q(1,2)),point(Q(-1,2)))
        self.assertEqual(r['status'],'stable_decision')

    def test_strict_readout_and_partial_false(self):
        box=point();box[6]=[core.grid(Q(-1,2)),core.grid(0)]
        self.assertIsNone(core.diagnostic(box)['candidate'])
        for x,candidate in ((core.MARGIN,True),(-core.MARGIN,False)):
            box=point();box[6]=[core.grid(x),core.grid(x,True)]
            # A grid enclosing the exact margin boundary may straddle: never force confidence.
            d=core.diagnostic(box)
            self.assertIsNone(d['candidate'])
            outward_x=x+(Q(1,10**28) if x>0 else -Q(1,10**28))
            box[6]=[core.grid(outward_x),core.grid(outward_x,True)]
            self.assertEqual(core.diagnostic(box)['candidate'],candidate)
        d=core.diagnostic(point(Q(-1,2)))
        self.assertFalse(d['candidate']);self.assertTrue(d['coverage_required'])
        self.assertEqual(d['adopted_value'],'NOT_MEASURED')


class SupervisionChecks(unittest.TestCase):
    def setUp(self):
        import termination_compare_runner as runner
        import check_termination_comparison as evaluator
        self.r,self.e=runner,evaluator
        self.temp_base=Path(tempfile.gettempdir()).resolve()
        self.temp=tempfile.TemporaryDirectory(prefix='hcr-termination-check-',dir=self.temp_base)
        self.out=Path(self.temp.name).resolve()
        self.assertEqual(self.out.parent,self.temp_base)
        self.assertTrue(self.out.name.startswith('hcr-termination-check-'))

    def tearDown(self):
        self.assertEqual(self.out.parent,self.temp_base)
        self.assertTrue(self.out.name.startswith('hcr-termination-check-'))
        self.temp.cleanup()  # Only this verified, newly created test directory.

    def phase(self,body,name='phase',cap=1.0,**kwargs):
        pre='import sys,json,pathlib,time,os,subprocess\nr=json.loads(sys.stdin.readline())\np=pathlib.Path(r["out"])\n'
        return self.r.owned_phase([sys.executable,'-B','-X','utf8','-c',pre+body],
                                  self.out/name,cap,**kwargs)

    def synthetic_input(self,name='input.json'):
        ids=core.ORDER
        program={'groups':[{'id':key,'bias':0.0} for key in ids],
                 'links':[{'source':ids[i%7],'target':ids[(i+1)%7],
                           'kind':'support' if i<4 else 'top_down','weight':0.0} for i in range(8)],
                 'paths':[[0,1]]}
        obs={'start':'S','goal':'G','edges':[{'id':'e2','source':'S','target':'B','score':1.0},
             {'id':'e3','source':'B','target':'G','score':.04},
             {'id':'e0','source':'S','target':'A','score':1.0},
             {'id':'e1','source':'A','target':'G','score':.6}]}
        public={'program':program,'drives':dict.fromkeys(ids,'0'),
                'kernel':{'temperature':1.0,'damping':.45,'self_excitation':.25,'inhibition':.2},
                'observation':obs,'processed':{'complete':False,'paths':[['e2','e3']],
                                               'remaining_public_path':['e0','e1']}}
        # Keep the actual diagonal: b=0/x0=0 is still identically zero, so the known limit is exact.
        data={'schema':'HCCTerminationInput.v1','public':public,
            'model_digest':core.digest(self.r.model_from_public(public)),
            'observation_digest':core.digest(obs),'processed_digest':core.digest(public['processed']),
            'math_sources':{n:(ROOT/n).read_text(encoding='utf-8') for n in core.LIB_PINS},
            'tick_cap':6144,'cadence':16,'radius_x_exact':str(core.RADIUS),
            'epsilon_p_exact':str(core.EPSILON)}
        path=self.out/name;self.r.write_new(path,data)
        return data,path,hashlib.sha256(path.read_bytes()).hexdigest()

    def policy_phase(self,arm,name,cap=3.0):
        data,path,sha=self.synthetic_input(name+'-input.json')
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'termination_compare_runner.py'),
                 '--worker','policy','--input',str(path),'--input-sha',sha,'--arm',arm]
        result=self.r.owned_phase(command,self.out/name,cap)
        return data,path,sha,result

    def test_actual_tree_timeout_and_accounting(self):
        grand='import pathlib,time,sys\np=pathlib.Path(sys.argv[1])\nwhile True:\n p.write_text(str(time.monotonic()));time.sleep(.01)'
        body='g=subprocess.Popen([sys.executable,"-c",'+repr(grand)+',str(p/"heartbeat")],creationflags=subprocess.CREATE_NO_WINDOW)\n(p/"grandchild.pid").write_text(str(g.pid))\ntime.sleep(30)'
        s=self.phase(body,cap=1.0)
        self.assertEqual(s['status'],'BUDGET_INCOMPLETE')
        self.assertTrue(s['released']);self.assertEqual(s['active_processes'],0)
        self.assertGreaterEqual(s['total_processes'],2)
        self.assertEqual(s['job_memory_limit_bytes'],512*1024*1024)
        self.assertEqual(s['job_limit_flags']&(0x800|0x1000),0)
        heartbeat=self.out/'phase/heartbeat';self.assertTrue(heartbeat.exists())
        old=heartbeat.read_bytes();time.sleep(.06);self.assertEqual(old,heartbeat.read_bytes())

    def test_uncooperative_cpu_loop_killed(self):
        s=self.phase('while True: pass',cap=.6)
        self.assertEqual(s['status'],'BUDGET_INCOMPLETE');self.assertEqual(s['active_processes'],0)
        self.assertGreater(s['tree_cpu_seconds'],0)

    def test_assignment_failure_no_workload_release(self):
        class Fail(self.r.Job):
            def assign(self,process):raise OSError('synthetic assignment failure')
        s=self.phase('(p/"workload").write_text("BAD")',job_factory=Fail)
        self.assertFalse(s['released']);self.assertEqual(s['status'],'MEASUREMENT_FAILURE')
        self.assertFalse((self.out/'phase/workload').exists())

    def test_global_expired_prevents_launch_and_output_is_exclusive(self):
        s=self.phase('(p/"workload").write_text("BAD")',global_deadline=time.monotonic()-1)
        self.assertFalse(s['released']);self.assertIsNone(s['exit_code'])
        with self.assertRaises(FileExistsError):self.phase('pass')
        for bad in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):self.phase('pass',name='bad',cap=bad)

    def test_global_expiry_prevents_next_workload(self):
        end=time.monotonic()+.5
        first=self.phase('while True:pass',name='global-first',cap=2,global_deadline=end)
        self.assertIsNotNone(first['termination_requested_monotonic'])
        second=self.phase('(p/"must-not-run").write_text("BAD")',name='global-next',cap=2,
                          global_deadline=end)
        self.assertFalse(second['released']);self.assertIsNone(second['exit_code'])
        self.assertFalse((self.out/'global-next/must-not-run').exists())

    def test_memory_commit_limit(self):
        def small_job():return self.r.Job(32*1024*1024)
        body='try:\n a=bytearray(128*1024*1024)\nexcept MemoryError:\n (p/"memory-rejected").write_text("yes");sys.exit(3)'
        s=self.phase(body,cap=1.5,job_factory=small_job)
        self.assertEqual(s['status'],'MEASUREMENT_FAILURE');self.assertEqual(s['active_processes'],0)
        self.assertTrue((self.out/'phase/memory-rejected').exists())
        self.assertEqual(s['job_memory_limit_bytes'],32*1024*1024)

    def test_root_exit_cannot_leave_descendant(self):
        body='g=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],creationflags=subprocess.CREATE_NO_WINDOW)\ntime.sleep(.15)'
        s=self.phase(body,cap=1.0)
        self.assertEqual(s['active_processes'],0)
        self.assertEqual(s['status'],'DESCENDANT_CLEANUP')

    def test_last_complete_survives_next_tick_interruption(self):
        snap={'tick':7,'value':'complete'}
        body='import termination_compare_runner as m\ns='+repr(snap)+'\nq=p/"state-000007.json"\nm.write_new(q,s)\nm.atomic_owned(p/"last-complete.json",{"path":q.name,"sha256":__import__("hashlib").sha256(q.read_bytes()).hexdigest(),"completed_monotonic":time.monotonic(),"tick":7})\n(p/"state-000008.pending").write_text("incomplete")\nwhile True: pass'
        body='sys.path.insert(0,'+repr(str(ROOT))+')\n'+body
        s=self.phase(body,cap=.7)
        last=self.r.last_snapshot(self.out/'phase',s)
        self.assertEqual(last['snapshot'],snap)
        self.assertFalse((self.out/'phase/final.json').exists())

    def test_commit_crossing_deadline_cannot_promote_state(self):
        out=self.out/'commit';out.mkdir()
        first=self.r.commit_state(out,{'tick':0},core.Meter())
        end=time.monotonic()+1;clock=[time.monotonic()]
        meter=core.Meter(end,clock=lambda:clock[0]);original=self.r.write_new
        def slow_seal(path,value):
            original(path,value);clock[0]=end+1
        with patch.object(self.r,'write_new',side_effect=slow_seal):
            with self.assertRaises(core.BudgetStop):self.r.commit_state(out,{'tick':1},meter)
        self.assertEqual(core.decode((out/'last-complete.json').read_bytes()),first)

    def test_source_binding_model_matches_old_accepted_anchor_without_steps(self):
        repo=Path(os.environ.get('HCR_TEST_REPO',str(ROOT.parents[1])))
        plan=core.decode((repo/self.r.PLAN).read_bytes())
        data=self.r.prepare_input(repo,plan);self.r.validate_input(data)
        reference=core.decode((repo/'experiments/exp-62-top-down/on-fixed-point-distance-entry-certificates-20261014.json').read_bytes())
        self.assertEqual(data['model_digest'],reference['independent_verification']['model_digest'])
        self.assertEqual(self.e.independent_model(data['public']),self.r.model_from_public(data['public']))
        bad=dict(data,model_digest='0'*64)
        with self.assertRaises(ValueError):self.r.validate_input(bad)
        bad=dict(data,world={'truth':'forbidden'})
        with self.assertRaises(ValueError):self.r.validate_input(bad)

    def test_actual_L_and_C_synthetic_workers(self):
        data,path,sha,s=self.policy_phase('C','C')
        self.assertEqual(s['status'],'COMPLETE')
        f=core.decode((self.out/'C/final.json').read_bytes())
        self.assertEqual(f['stop_reason'],'CERTIFIED');self.assertEqual(f['last_complete']['tick'],16)
        self.assertTrue(f['certificate']['bounds']['component_vector'][0]['permanence'])
        # New file namespace for a separate cold L cell, no resume or warm state.
        data,path,sha,s=self.policy_phase('L','L')
        self.assertEqual(s['status'],'COMPLETE')
        f=core.decode((self.out/'L/final.json').read_bytes())
        self.assertEqual(f['stop_reason'],'stable_ambiguous');self.assertEqual(f['last_complete']['tick'],16)

    def test_actual_F_and_pending_C_interruptions(self):
        data,path,sha,s=self.policy_phase('F','F',cap=.8)
        self.assertEqual(s['status'],'BUDGET_INCOMPLETE');self.assertEqual(s['active_processes'],0)
        last=self.r.last_snapshot(self.out/'F',s)
        self.assertIsNotNone(last);self.assertFalse((self.out/'F/final.json').exists())
        self.assertEqual(last['snapshot']['diagnostic']['adopted_value'],'NOT_MEASURED')
        # Hold C inside its certificate call, using the actual worker/commit/watchdog paths.
        body='sys.path.insert(0,'+repr(str(ROOT))+')\nimport termination_compare_runner as m\nimport termination_compare_core as c\ndef stall(*args):\n while True:pass\nc.Arithmetic.certificate=stall\nm.policy_worker('+repr(str(path))+','+repr(sha)+',"C",r)'
        pending=self.phase(body,name='pending-C',cap=.8)
        last=self.r.last_snapshot(self.out/'pending-C',pending)
        self.assertEqual(pending['status'],'BUDGET_INCOMPLETE')
        self.assertEqual(last['snapshot']['tick'],16);self.assertEqual(last['snapshot']['gate_state'],'PENDING')
        self.assertFalse((self.out/'pending-C/final.json').exists())

    def test_kill_on_job_close_owned_tree(self):
        grand='import pathlib,time,sys\np=pathlib.Path(sys.argv[1])\nwhile True:\n p.write_text(str(time.monotonic()));time.sleep(.01)'
        d=self.out/'close';d.mkdir();heartbeat=d/'heartbeat'
        body='import sys,json,subprocess,time\nr=json.loads(sys.stdin.readline())\nsubprocess.Popen([sys.executable,"-c",'+repr(grand)+',r["heartbeat"]],creationflags=subprocess.CREATE_NO_WINDOW)\ntime.sleep(30)'
        job=self.r.Job();p=None
        try:
            p=subprocess.Popen([sys.executable,'-B','-X','utf8','-c',body],stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW|0x4)
            job.assign(p);self.r.resume_owned_bootstrap(p)
            p.stdin.write(core.canonical({'heartbeat':str(heartbeat)})+b'\n');p.stdin.flush();p.stdin.close()
            end=time.monotonic()+2
            while not heartbeat.exists() and time.monotonic()<end:time.sleep(.01)
            self.assertTrue(heartbeat.exists())
            job.close();p.wait(timeout=2)
            old=heartbeat.read_bytes();time.sleep(.06);self.assertEqual(old,heartbeat.read_bytes())
        finally:
            job.close()
            if p and p.poll() is None:p.kill();p.wait(timeout=2)

    def test_sealed_evaluator_actual_process_and_leak_canary(self):
        data,path,sha,s=self.policy_phase('C','eval-C')
        self.assertEqual(s['status'],'COMPLETE')
        child=self.out/'eval-C';last=self.r.last_snapshot(child,s)
        final=core.decode((child/'final.json').read_bytes())
        sealed={'schema':'HCCTerminationSealedCell.v1','input_sha256':sha,'model_digest':data['model_digest'],
            'observation_digest':data['observation_digest'],'processed_digest':data['processed_digest'],
            'supervision':s,'last_complete':last,'final':final}
        seal_path=child/'sealed-cell.json';self.r.write_new(seal_path,sealed)
        world_path=self.out/'world.json';self.r.write_new(world_path,{'schema':'HCCTerminationWorld.v1',
            'observation_digest':data['observation_digest'],'truth':dict.fromkeys(['e0','e1','e2','e3'],True),
            'authored_synthetic_world':True})
        anchor_path=self.out/'closed-form-synthetic-anchor.json'
        self.r.write_new(anchor_path,{'schema':'SyntheticClosedFormAnchorTestOnly',
            'independent_verification':{'accepted':True,'model_digest':data['model_digest'],
                'state_order':core.ORDER,'sample_id':'above_near','all7':True,
                'anchor':{'tick':6144,'x_box_exact':[['0','0']]*7}}})
        def ref(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        request={'schema':'HCCTerminationEvaluationInput.v1','repo':str(self.out),
            'policy_seal':ref(seal_path),'public_input':ref(path),'world':ref(world_path),
            'distance_reference':dict(ref(anchor_path),path=anchor_path.name,bytes=anchor_path.stat().st_size)}
        ep=self.out/'eval-input.json';self.r.write_new(ep,request)
        command=[sys.executable,'-B','-X','utf8',str(ROOT/'termination_compare_runner.py'),
            '--worker','evaluation','--input',str(ep),'--input-sha',hashlib.sha256(ep.read_bytes()).hexdigest()]
        ev=self.r.owned_phase(command,self.out/'eval',3)
        self.assertEqual(ev['status'],'COMPLETE')
        result=core.decode((self.out/'eval/result.json').read_bytes())
        self.assertEqual(result['distance']['status'],'INSIDE')
        self.assertEqual(result['local_certificate_recheck'],'PASS_shared_pinned_numeric_helpers')
        self.assertIsNone(result['candidate_correct']);self.assertEqual(result['adopted_value'],'NOT_MEASURED')
        bad=json.loads(json.dumps(request));bad['policy_seal']['sha256']='0'*64
        bad['world']['path']=str(self.out/'world-must-not-be-read-canary')
        bp=self.out/'bad-evaluation.json';self.r.write_new(bp,bad)
        with self.assertRaisesRegex(ValueError,'evaluation artifact hash'):
            self.e.evaluate_worker(bp,hashlib.sha256(bp.read_bytes()).hexdigest(),
                {'start':time.monotonic(),'deadline':time.monotonic()+3,'out':str(self.out/'unused')})

    def test_distance_full7_equality_and_ambiguous(self):
        B=point();B[2]=[core.grid(Q(4,10**6))]*2;anchor=[['0','0']]*7
        self.assertEqual(self.e.distance(B,anchor)['status'],'OUTSIDE')
        B=point();B[2]=[core.grid(Q(2,10**6))]*2
        self.assertEqual(self.e.distance(B,anchor)['status'],'INSIDE')
        B[2]=[core.grid(Q(0)),core.grid(Q(4,10**6))]
        self.assertEqual(self.e.distance(B,anchor)['status'],'AMBIGUOUS')

    def test_world_identity_and_missing_cells_denominators(self):
        obs={'start':'S','goal':'G','edges':[{'id':'x','source':'S','target':'G'}]}
        self.assertTrue(self.e.reachability(obs,{'x':True}))
        self.assertFalse(self.e.reachability(obs,{'x':False}))
        with self.assertRaises(ValueError):self.e.reachability(obs,{'x':'true'})
        summary=self.e.aggregate([{'cell':'180/L','status':'BUDGET_INCOMPLETE','evaluation':None}])
        self.assertEqual(summary['planned_denominator'],6)
        self.assertEqual(summary['by_budget']['1800']['planned_denominator'],3)
        self.assertIsNone(summary['by_budget']['1800']['conditional_accuracy'])
        with self.assertRaises(ValueError):self.e.aggregate([{'cell':'wrong'}])


if __name__=='__main__':unittest.main()
