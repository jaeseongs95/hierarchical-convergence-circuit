"""HF1 regression tests: preserve hash differences, reject meaningful drift."""
from copy import deepcopy
from math import nextafter, inf
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from tools.r048_precision import io
from tools.r049_signal_boundary import spec, device, audit, regression, evaluate, reporting
ROOT=Path(__file__).resolve().parents[3]


class PortableReference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prior=io.load(ROOT/'docs/R049_PRIOR_EXPLORATION.json')
        cls.refs=regression.references(cls.prior)
        p=spec.body();cls.cases={c['id']:c for c in p['cases']};cls.items=[]
        for t in p['trials']:
            if t['evidence_role']!='prior_exploration_replication':continue
            c=cls.cases[t['case']];r=device.run_query(c['observation'],p['kernel_config'],t['arm'])
            audit.audit_record(r,p['worlds'][t['case']])
            key=c['strength'],c['pattern'],t['arm'];ref=cls.refs[key]
            d=io.digest(dict(ticks=ref['ticks'],convergence=ref['convergence']))
            cls.items.append((r,ref,d,p['worlds'][t['case']]))
    def test_all_sixteen_native_references(self):
        self.assertEqual(len(self.items),16)
        for r,b,d,w in self.items:self.assertTrue(regression.compare(r,b,d)['regression_passed'])
    def test_reference_uses_original_digest_not_newly_generated_expected(self):
        for e in self.prior['entries']:
            r=self.refs[e['strength'],e['pattern'],e['arm']]
            self.assertEqual(io.digest(dict(ticks=r['ticks'],convergence=r['convergence'])),e['dynamics_sha256'])
    def test_reference_source_corruption_rejected(self):
        with TemporaryDirectory() as d:
            dst=Path(d)/regression.REFERENCE_FILE;dst.parent.mkdir(parents=True);dst.write_bytes(b'{}\n')
            with self.assertRaises(ValueError):regression.references(self.prior,Path(d))
    def test_reference_digest_corruption_rejected(self):
        p=deepcopy(self.prior);p['entries'][0]['dynamics_sha256']='0'*64
        with self.assertRaises(ValueError):regression.references(p)
    def test_one_ulp_injected_exp_variation_still_audited(self):
        import hcr.dynamics as dyn
        original=dyn.exp
        changed=[]
        with patch.object(dyn,'exp',lambda v:nextafter(original(v),inf)):
            for r,b,d,w in self.items:
                x=device.run_query(r['observation'],r['config'],r['arm']);audit.audit_record(x,w)
                c=regression.compare(x,b,d);self.assertTrue(c['regression_passed'],c)
                if not c['dynamics_equal']:changed.append(c)
        self.assertTrue(changed)
        self.assertTrue(all(x['classification']=='numeric_equivalent_hash_different' for x in changed))
    def test_small_stored_difference_is_not_silently_rounded(self):
        r,b,d,w=self.items[0];x=deepcopy(r);key='e:0';x['ticks'][5]['state'][key]=nextafter(x['ticks'][5]['state'][key],inf)
        before=io.digest(x);c=regression.compare(x,b,d)
        self.assertEqual(before,io.digest(x));self.assertFalse(c['dynamics_equal']);self.assertTrue(c['regression_passed'])
    def reject(self,change):
        r,b,d,w=self.items[0];x=deepcopy(r);change(x)
        self.assertFalse(regression.compare(x,b,d)['regression_passed'])
    def test_large_numeric_difference_rejected(self):self.reject(lambda r:r['ticks'][5]['state'].__setitem__('e:0',.1))
    def test_residual_drift_rejected(self):self.reject(lambda r:r['ticks'][5].__setitem__('residual',.7))
    def test_missing_tick_rejected(self):self.reject(lambda r:r['ticks'].pop())
    def test_extra_tick_rejected(self):self.reject(lambda r:r['ticks'].append(deepcopy(r['ticks'][-1])))
    def test_early_stop_change_rejected(self):self.reject(lambda r:r['convergence'].__setitem__('ticks',87))
    def test_status_change_rejected(self):self.reject(lambda r:r['convergence'].__setitem__('status','stable_ambiguous'))
    def test_stable_steps_change_rejected(self):self.reject(lambda r:r['ticks'][5].__setitem__('stable_steps',1))
    def test_raw_flip_rejected(self):self.reject(lambda r:r.__setitem__('raw_value',True))
    def test_adoption_change_rejected(self):self.reject(lambda r:r.__setitem__('accepted',True))
    def test_config_change_rejected(self):self.reject(lambda r:r['config'].__setitem__('damping',.46))
    def test_mask_change_rejected(self):self.reject(lambda r:r['intervention'].__setitem__('top_down',False))
    def test_initial_change_rejected(self):self.reject(lambda r:r['initial_state'].__setitem__('goal',.99))
    def test_proof_boundary_change_rejected(self):self.reject(lambda r:r['proof'].__setitem__('under_assumptions_valid',False))
    def test_integer_bool_confusion_rejected(self):self.reject(lambda r:r['convergence'].__setitem__('stable_steps',4.0))
    def test_tiny_point_five_crossing_not_hidden_by_tolerance(self):self.reject(lambda r:r['ticks'][0]['state'].__setitem__('goal',.5+1e-14))
    def test_nan_rejected(self):
        r,b,d,w=self.items[0];x=deepcopy(r);x['ticks'][0]['state']['e:0']=float('nan')
        with self.assertRaises(ValueError):regression.compare(x,b,d)
    def test_checksum_still_requires_bit_identical_bytes(self):
        with TemporaryDirectory() as d:
            p=Path(d);io.write(p/'raw.json',b'{"v":0.5}\n')
            wanted=io.hashes(p);(p/'raw.json').write_bytes(b'{"v":0.5000000000000001}\n')
            with self.assertRaises(ValueError):io.verify_files(p,wanted)
    def test_summary_does_not_relabel_hash_mismatch_as_equal(self):
        p=dict(spec.body(),population='implementation_validation');cases={c['id']:c for c in p['cases']};rs={};aa={}
        import hcr.dynamics as dyn
        exp=dyn.exp
        with patch.object(dyn,'exp',lambda v:nextafter(exp(v),inf)):
            for t in p['trials']:
                c=cases[t['case']];r=device.run_query(c['observation'],p['kernel_config'],t['arm'])
                rs[t['id']]=r;aa[t['id']]=audit.audit_record(r,p['worlds'][t['case']])
        s=evaluate.summarize(p,rs,aa,self.prior)
        self.assertTrue(any(not x['dynamics_equal'] for x in s['prior_regressions']))
        self.assertTrue(all(x['regression_passed'] for x in s['prior_regressions']))
        self.assertIn('exact SHA256',reporting.render(s).decode())
