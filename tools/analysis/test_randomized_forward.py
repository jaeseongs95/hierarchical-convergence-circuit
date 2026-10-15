"""무작위화/스레드 관측 경계와 원 검산기 결속. 새 수치 궤적 재생은 하지 않는다."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_forward_crossover as prior
import termination_randomized_forward as study
from test_forward_crossover import CrossoverTests

core, runner = study.core, study.runner


def sample(q, cpu, cycle=100, status='AVAILABLE'):
    return dict(pid=1, tid=2, qpc_before_ns=q, qpc_after_ns=q+10,
                thread=dict(status=status, kernel_100ns=cpu, user_100ns=cpu),
                process=dict(status=status, kernel_100ns=cpu, user_100ns=cpu),
                cycles=dict(status=status, raw=cycle))


class RandomizedTests(unittest.TestCase):
    def test_contract_binds_debit_and_predraw_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            def pin(name,value):
                raw=core.canonical(value);(root/name).write_bytes(raw)
                return dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            protocol=pin('protocol.json',dict(code_pins=[]))
            seed=bytes(32).hex();order=['C0','C1','C0','C1']
            draw=pin('draw.json',dict(protocol_sha256=protocol['sha256'],seed_hex=seed,order=order))
            timing=pin('timing.json',dict(draw_sha256=draw['sha256'],before_entropy_qpc_ns=0,
                after_draw_receipt_qpc_ns=100000000,debit_seconds=.1))
            cfg=dict(code_pins=[],draw_pin=draw,randomization_protocol_pin=protocol,
                draw_timing_pin=timing,sequential_order=order,draw_debit_seconds=.1)
            contract=root/'contract.json'
            with patch.object(study,'ROOT',root),patch.object(study,'CONTRACT',contract):
                contract.write_bytes(core.canonical(cfg));study.contract()
                cfg['draw_debit_seconds']=.09
                contract.write_bytes(core.canonical(cfg))
                with self.assertRaisesRegex(ValueError,'debit binding'):study.contract()
                cfg['draw_debit_seconds']=.1
                cfg['randomization_protocol_pin']=pin('other-protocol.json',dict(code_pins=[dict(path='different')]))
                cfg['draw_pin']=pin('draw2.json',dict(protocol_sha256=cfg['randomization_protocol_pin']['sha256'],seed_hex=seed,order=order))
                cfg['draw_timing_pin']=pin('timing2.json',dict(draw_sha256=cfg['draw_pin']['sha256'],
                    before_entropy_qpc_ns=0,after_draw_receipt_qpc_ns=100000000,debit_seconds=.1))
                contract.write_bytes(core.canonical(cfg))
                with self.assertRaisesRegex(ValueError,'predraw code binding'):study.contract()

    def test_two_independent_bits_all_four_orders(self):
        orders = [study.assignment(bytes([i]+[0]*31).hex()) for i in range(4)]
        self.assertEqual(orders, [['C0','C1','C0','C1'], ['C1','C0','C0','C1'],
                                  ['C0','C1','C1','C0'], ['C1','C0','C1','C0']])
        with self.assertRaises(ValueError): study.assignment('00')

    def test_raw_cpu_difference_and_signed_residual(self):
        a, b = sample(0, 0, 100), sample(1000000010, 6000000, 400)
        result = study.span(a, b)
        self.assertEqual(result['wall_seconds'], 1)
        self.assertAlmostEqual(result['thread']['cpu_seconds'], 1.2)
        self.assertAlmostEqual(result['thread']['wall_minus_cpu_seconds'], -.2)
        self.assertEqual(result['cycles']['raw_difference'], 300)
        b['tid'] = 3
        with self.assertRaisesRegex(ValueError, 'lifetime'): study.span(a, b)

    def test_unavailable_is_not_zero(self):
        result = study.span(sample(0,0,status='UNAVAILABLE'), sample(100,0))
        self.assertEqual(result['thread'], {'status': 'UNAVAILABLE'})
        self.assertEqual(result['cycles'], {'status': 'UNAVAILABLE'})

    def test_forward_and_certificate_are_disjoint_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            o = study.Observer(tmp, (prior.Clock(), prior.Clock(), prior.Clock()), lambda: None,
                iter([sample(0,0),sample(1000000010,2000000),sample(1100000000,2000000),sample(1600000010,3000000)]).__next__)
            o.state_hash = 'x0'
            o.call('advance', lambda: None)
            o.tick, o.state_hash = 16, 'x16'
            o.call('certificate', lambda: 3)
            a=core.decode((Path(tmp)/'forward-window-0001.json').read_bytes())
            b=core.decode((Path(tmp)/'certificate-window-0001.json').read_bytes())
            self.assertEqual(a['tick_start_exclusive'], 0)
            self.assertEqual(a['tick_end_inclusive'], 16)
            self.assertEqual(a['metrics']['wall_seconds'], 1)
            self.assertEqual(b['metrics']['wall_seconds'], .5)
            self.assertGreater(b['start']['qpc_before_ns'], a['end']['qpc_after_ns'])

    def test_failed_certificate_window_is_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            o=study.Observer(tmp, (prior.Clock(),prior.Clock(),prior.Clock()),lambda:None,
                iter([sample(0,0),sample(100,0),sample(200,0),sample(300,0)]).__next__)
            o.call('advance',lambda:None); o.tick=16
            with self.assertRaises(ValueError):
                o.call('certificate', lambda: (_ for _ in ()).throw(ValueError('stop')))
            b=core.decode((Path(tmp)/'certificate-window-0001.json').read_bytes())
            self.assertFalse(b['complete'])

    def test_native_api_snapshot_or_explicit_unavailable(self):
        a,b=study.thread_snapshot(),study.thread_snapshot()
        r=study.span(a,b)
        self.assertGreaterEqual(r['read_bracket_seconds'],0)
        self.assertIn(r['thread']['status'], ('AVAILABLE','UNAVAILABLE'))


def verify_mechanisms(out, result):
    out=Path(out); diagnostics=[]
    for row in result['cells']:
        child=out/row['cell_id']
        if row['status'] != 'COMPLETE':
            diagnostics.append(dict(cell_id=row['cell_id'], status='PARTIAL_OR_NOT_RUN',
                saved_forward_window_files_not_validated_complete=len(list(child.glob('forward-window-*.json')))))
            continue
        meta=core.decode((child/'mechanisms.json').read_bytes())
        n=row['tick']//16
        assert meta['windows']=={'forward':n,'certificate':n} and not meta['partial_forward']
        totals={}; identity=None; previous_end=None
        for index in range(1,n+1):
            for kind in ('forward','certificate'):
                w=core.decode((child/f'{kind}-window-{index:04d}.json').read_bytes())
                assert w['complete'] and w['kind']==kind
                assert w['tick_end_inclusive']==index*16
                assert w['tick_start_exclusive']==((index-1)*16 if kind=='forward' else index*16)
                state=core.decode((child/f'state-{index*16:06d}.json').read_bytes())
                assert w['state_digest_at_end']==core.digest(state['current_x_box'])
                a,b=w['start'],w['end']; m=w['metrics']
                ident=(a['pid'],a['tid'])
                assert ident==(b['pid'],b['tid'])
                if identity is None: identity=ident
                assert ident==identity
                assert a['qpc_before_ns']<=a['qpc_after_ns']<=b['qpc_before_ns']<=b['qpc_after_ns']
                if previous_end is not None: assert a['qpc_before_ns']>=previous_end
                previous_end=b['qpc_after_ns']
                assert m['wall_seconds']==(b['qpc_before_ns']-a['qpc_after_ns'])/1e9
                summary=totals.setdefault(kind,dict(wall_seconds=0.,thread_cpu_seconds=0.,process_cpu_seconds=0.,
                    kernel_seconds=0.,user_seconds=0.,raw_cycles=0,read_bracket_seconds=0.,available_windows=0))
                summary['wall_seconds']+=m['wall_seconds']; summary['read_bracket_seconds']+=m['read_bracket_seconds']
                available=True
                for who in ('thread','process'):
                    ok=a.get(who,{}).get('status')==b.get(who,{}).get('status')=='AVAILABLE'
                    if not ok:
                        assert m[who]=={'status':'UNAVAILABLE'};available=False;continue
                    cpu=0.
                    for mode in ('user','kernel'):
                        value=(b[who][mode+'_100ns']-a[who][mode+'_100ns'])/1e7
                        assert value>=0 and m[who][mode+'_seconds']==value
                        cpu+=value
                        if who=='thread':summary[mode+'_seconds']+=value
                    assert m[who]['cpu_seconds']==cpu
                    assert abs(m[who]['wall_minus_cpu_seconds']-(m['wall_seconds']-cpu))<1e-12
                    summary[who+'_cpu_seconds']+=cpu
                ok=a.get('cycles',{}).get('status')==b.get('cycles',{}).get('status')=='AVAILABLE'
                if ok:
                    delta=b['cycles']['raw']-a['cycles']['raw'];assert delta>=0 and m['cycles']['raw_difference']==delta
                    summary['raw_cycles']+=delta
                else: assert m['cycles']=={'status':'UNAVAILABLE'};available=False
                summary['available_windows']+=int(available)
        for t in totals.values():
            if t['available_windows']==n:
                t['wall_minus_thread_cpu_seconds']=t['wall_seconds']-t['thread_cpu_seconds']
                t['status']='AVAILABLE'
            else:
                t['status']='UNAVAILABLE_FOR_FULL_CELL'
                for key in ('thread_cpu_seconds','process_cpu_seconds','kernel_seconds','user_seconds','raw_cycles'):
                    t[key]=None
        diagnostics.append(dict(cell_id=row['cell_id'],status='PASS',window_count_each=n, totals=totals,
            pure_numeric_CPU=False, cycles_to_frequency=False, residual_clipped=False))
    result['mechanism_verification']=diagnostics
    result['randomization']=dict(order=study.contract()[0]['sequential_order'],
        allocation_space_size=4, randomized_unit='cell', window_is_independent_sample=False,
        retrospective_r12_or_r11_correction=False, no_statistical_superiority=True)
    result['schema']='HCCRandomizedForwardVerification.v1'
    return result


def verify_study(out):
    started=__import__('time').perf_counter_ns()
    study.activate()
    original=runner.write_new
    def write(path, value):
        if Path(path).name=='result.json':
            value=verify_mechanisms(out,value)
            value['inherited_verification_body_highres_wall_seconds']=value.pop('verification_highres_wall_seconds')
            value['verification_highres_wall_seconds']=(__import__('time').perf_counter_ns()-started)/1e9
        return original(path,value)
    with patch.object(runner,'write_new',write): prior.verify_study(out)


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--verify-study': verify_study(sys.argv[2])
    else: unittest.main()
