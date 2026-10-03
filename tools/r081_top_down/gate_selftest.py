"""Synthetic orchestration checks: never runs a native HCC condition."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools.r050_review_boundary.common import dump, files, load, canonical, IntegrityError
from tools.r081_top_down import worker
from tools.r081_top_down.review_gate import completed, request_for, reviewed

def main():
    checks=[]
    with TemporaryDirectory() as tmp:
        out=Path(tmp)/'synthetic-run'; incoming=Path(tmp)/'reviews'
        plan=dict(cells=[dict(id='c'+str(i),use_circuits=False,top_down=bool(i%2)) for i in range(4)])
        dump(out/'source/experiments/exp-62-top-down/frozen_spec.json',plan)
        dump(out/'plan.json',plan)
        dump(out/'source_manifest.json',dict(files=files(out/'source')))
        dump(out/'parent/memory/3.json',{})
        dump(out/'repeat/placeholder.json',{})
        dump(out/'input_manifest.json',dict(files=files(out/'parent')))
        dump(out/'repeat_manifest.json',dict(files=files(out/'repeat')))
        dump(out/'review_policy.json',dict(writer_id='writer',reviewer_id='reviewer'))
        dump(out/'validation/selftest.json',dict(verified=True))
        calls=[]
        def execute(*args,**kwargs):
            calls.append(args[1]['id']); return dict(stop='synthetic-only')
        def approve(cell=None, **changes):
            request=request_for(out,cell)
            receipt=dict(schema='hcc-r081-external-review-v1',request=request,reviewer_id='reviewer',
                         verdict='PASS',blocking_findings=[],evidence='synthetic test fixture only',reviewed_at='2026-10-03T00:00:00Z')
            receipt.update(changes)
            dump(incoming/(request['subject']+'.json'),receipt)
        with patch.object(worker,'execute',execute):
            worker.main(out,incoming,'writer','reviewer')
            assert calls==[];checks.append('missing design blocks first native')
            approve()
            worker.main(out,incoming,'writer','reviewer')
            assert calls==['c0'];checks.append('one new condition per invocation')
            worker.main(out,incoming,'writer','reviewer')
            assert calls==['c0'];checks.append('missing cell review blocks next condition without rerun')
            for i in range(4):
                assert not completed(out,incoming,'writer','reviewer')
                approve('c'+str(i))
                worker.main(out,incoming,'writer','reviewer')
            assert calls==['c0','c1','c2','c3'] and completed(out,incoming,'writer','reviewer')
            checks.append('four distinct conditions and final review required')
            worker.main(out,incoming,'writer','reviewer')
            assert len(calls)==4;checks.append('repeated resume never reruns native')
        # Validation failures use separate copies; approved real evidence is never rewritten.
        original=load(out/'external_reviews/c0.json')
        for label, edit in [
            ('wrong run',lambda r:r['request'].update(run_id='other')),
            ('wrong raw',lambda r:r['request'].update(raw_sha256='0'*64)),
            ('wrong source',lambda r:r['request'].update(source_sha256='0'*64)),
            ('wrong plan',lambda r:r['request'].update(plan_sha256='0'*64)),
            ('self review',lambda r:r.update(reviewer_id='writer')),
            ('failed review',lambda r:r.update(verdict='FAIL')),
            ('blocking finding',lambda r:r.update(blocking_findings=['open'])),
            ('missing evidence',lambda r:r.update(evidence=''))]:
            bad=deepcopy(original);edit(bad)
            real_read=Path.read_bytes
            def changed(path):
                return canonical(bad) if path==out/'external_reviews/c0.json' else real_read(path)
            with patch.object(Path,'read_bytes',changed):
                try: reviewed(out,incoming,'writer','reviewer','c0')
                except IntegrityError: checks.append(label+' rejected')
                else: raise AssertionError(label)
        # Partial native artifacts cannot be overwritten even if no final inference exists.
        (out/'evaluation/c3/inference.json').unlink()  # This temporary synthetic fixture only.
        with patch.object(worker,'execute',execute):
            try: worker.main(out,incoming,'writer','reviewer')
            except FileExistsError: checks.append('partial native directory cannot rerun')
            else: raise AssertionError('partial rerun')
            assert len(calls)==4
        # A changed producer identity fails before any native call.
        try: worker.main(out,incoming,'other-writer','reviewer')
        except IntegrityError: checks.append('identity change rejected')
        else: raise AssertionError('identity')
        (out/'evaluation/c0/extra.json').write_text('{}',encoding='utf-8')
        try: reviewed(out,incoming,'writer','reviewer','c0')
        except IntegrityError: checks.append('raw mutation invalidates acceptance')
        else: raise AssertionError('raw drift')
    print({'verified':True,'checks':checks,'new_native_executions':0})

if __name__=='__main__':main()
