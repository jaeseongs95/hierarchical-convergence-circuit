"""Synthetic receipt races and JSON rejection only; no native evaluation."""
import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from tools.r050_review_boundary.common import dump, load, IntegrityError
from tools.r081_top_down.review_gate import request_for, reviewed


def main():
    checks=[]
    with TemporaryDirectory() as tmp:
        root=Path(tmp)
        def fixture(label):
            out=root/label;incoming=root/(label+'-incoming')
            dump(out/'plan.json',dict(cells=[]))
            dump(out/'source_manifest.json',dict(files={}))
            receipt=dict(schema='hcc-r081-external-review-v1',request=request_for(out,None),
                         reviewer_id='reviewer',verdict='PASS',blocking_findings=[],
                         evidence='synthetic fixture only',reviewed_at='2026-10-03T00:00:00Z')
            incoming.mkdir();return out,incoming,receipt
        # Replace the incoming file immediately after its first read. The exact
        # first bytes must determine both the verdict and persisted evidence.
        for first_valid in (False,True):
            out,incoming,good=fixture('race-'+str(first_valid))
            bad=deepcopy(good);bad['verdict']='FAIL'
            first=json.dumps(good if first_valid else bad,indent=2).encode('utf-8')
            second=json.dumps(bad if first_valid else good).encode('utf-8')
            target=incoming/'design.json';target.write_bytes(first)
            real_read=Path.read_bytes;reads=[]
            def replaced(path):
                raw=real_read(path)
                if path==target:
                    reads.append(1)
                    path.write_bytes(second)
                return raw
            with patch.object(Path,'read_bytes',replaced):
                try: result=reviewed(out,incoming,'writer','reviewer')
                except IntegrityError:
                    assert not first_valid and not (out/'external_reviews/design.json').exists()
                else:
                    assert first_valid and result
                    assert (out/'external_reviews/design.json').read_bytes()==first
            assert reads==[1]
            checks.append('PASS snapshot preserved despite later FAIL' if first_valid else 'FAIL snapshot rejected despite later PASS')
        for label,extra in [('duplicate-key','"verdict":"FAIL"'),('nested-duplicate','"extra":{"x":1,"x":2}'),
                            ('NaN','"extra":NaN'),('Infinity','"extra":Infinity'),
                            ('negative-Infinity','"extra":-Infinity'),('overflow','"extra":1e999')]:
            out,incoming,receipt=fixture(label)
            raw=json.dumps(receipt)[:-1]+','+extra+'}'
            (incoming/'design.json').write_text(raw,encoding='utf-8')
            try: reviewed(out,incoming,'writer','reviewer')
            except ValueError: pass
            else: raise AssertionError('Accepted '+label)
            assert not (out/'external_reviews/design.json').exists()
            checks.append(label+' rejected')
        out,incoming,receipt=fixture('finite-control')
        receipt['extra']=1.25;raw=json.dumps(receipt,indent=3).encode('utf-8')+b'\n'
        (incoming/'design.json').write_bytes(raw)
        assert reviewed(out,incoming,'writer','reviewer')
        assert (out/'external_reviews/design.json').read_bytes()==raw
        checks.append('finite control preserves exact bytes')
        # Another publisher cannot insert a different accepted file while this
        # incoming receipt is being read and have it silently win publication.
        out,incoming,receipt=fixture('publication-race')
        target=incoming/'design.json';dump(target,receipt)
        real_read=Path.read_bytes
        def inserted(path):
            raw=real_read(path)
            if path==target:dump(out/'external_reviews/design.json',dict(verdict='FAIL'))
            return raw
        with patch.object(Path,'read_bytes',inserted):
            try: reviewed(out,incoming,'writer','reviewer')
            except IntegrityError: pass
            else: raise AssertionError('Concurrent acceptance silently won')
        checks.append('concurrent publication fails closed')
    print(json.dumps(dict(verified=True,checks=checks,new_native_executions=0)))


if __name__=='__main__':main()
