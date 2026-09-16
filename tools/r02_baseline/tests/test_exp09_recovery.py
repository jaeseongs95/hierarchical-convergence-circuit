"""실제 실패의 첫 전이 발췌와 부정 대조. HCR 추론을 호출하지 않는다."""
from __future__ import annotations
import ast
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
from collect import BaselineError, canonical, loads, read, sha
from memory_equivalence import compare_revision_memory, differences
from measurement_journal import MeasurementJournal, validate_measurements
from recover_probe import recover, validate_raw, real_root, contract_from_records, verify_recovery
from probe_analysis import semantic_decision


def fixture():
    data=loads(read(Path(__file__).with_name('fixtures')/'exp09_first_error_pair.json'))
    return data['rows'],data['events']


def compare(rows,events):return compare_revision_memory(*rows,events)


def change_after(rows,events,edit):
    """왼쪽 학습 결과와 그 hash만 일관되게 바꾸어 의미 대조까지 도달한다."""
    did=rows[0]['decision']['id'];next_id=rows[1]['decision']['id']
    update=next(e['payload'] for e in events if e['event']=='r02_memory_updated' and e['payload']['patch']['decision_id']==did)
    edit(update['memory_document'])
    digest=sha(canonical(update['memory_document']));update['memory_after']=digest
    start=next(e['payload'] for e in events if e['event']=='r02_attempt_started' and e['payload']['decision_id']==next_id)
    start['memory_hash']=digest
    rows[1]['memory_before']=rows[1]['memory_after_inference']=digest


class MemoryCorrespondence(unittest.TestCase):
    def test_original_error_reproduced_by_exact_hash(self):
        rows,events=fixture()
        self.assertNotEqual(rows[1]['memory_before'],rows[3]['memory_before'])
        self.assertTrue(compare(rows,events)['execution_state_equal'])

    def test_four_typed_reference_differences(self):
        r=compare(*fixture())
        self.assertFalse(r['exact_document_equal'])
        self.assertEqual(len(r['raw_difference_paths']),4)
        self.assertEqual(r['raw_difference_paths'],r['remapped_reference_paths'])

    def test_full_document_after_correspondence(self):
        r=compare(*fixture())
        self.assertTrue(r['full_document_equal_after_correspondence'])
        self.assertTrue(r['provenance_correspondence_valid'])
        self.assertEqual(r['excluded_fields'],[])

    def test_input_and_history_unchanged(self):
        data=fixture();before=canonical(data);compare(*data);self.assertEqual(canonical(data),before)

    def test_strength_difference_is_not_ignored(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0].update(strength=.123))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_active_difference_is_not_ignored(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0].update(active=False))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_failure_count_difference_is_not_ignored(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0].update(failures=5))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_old_feedback_id_cannot_be_arbitrarily_renamed(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0]['feedback_ids'].__setitem__(0,'unrelated'))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_evidence_episode_not_renamed(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0]['evidence_episodes'].__setitem__(0,'other'))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_proof_digest_not_renamed(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['circuits'][0]['proof_digests'].__setitem__(0,'f'*64))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_prior_history_not_discarded(self):
        rows,events=fixture();change_after(rows,events,lambda m:m['patches'][0].update(before_hash='f'*64))
        with self.assertRaisesRegex(BaselineError,'실제 memory'):compare(rows,events)

    def test_missing_pending_not_ignored(self):
        rows,events=fixture();change_after(rows,events,lambda m:m.pop('pending'))
        with self.assertRaises((BaselineError,KeyError)):compare(rows,events)

    def test_wrong_revision_parent_rejected(self):
        rows,events=fixture();next_id=rows[1]['decision']['id']
        next(e['payload'] for e in events if e['event']=='r02_attempt_started' and e['payload']['decision_id']==next_id)['revision_of']='other'
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_missing_feedback_rejected(self):
        rows,events=fixture();events=[e for e in events if not (e['event']=='r02_feedback' and e['payload']['decision_id']==rows[0]['decision']['id'])]
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_missing_update_rejected(self):
        rows,events=fixture();events=[e for e in events if e['event']!='r02_memory_updated']
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_duplicate_attempt_rejected(self):
        rows,events=fixture();events.append(next(e for e in events if e['event']=='r02_attempt_started'))
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_first_input_change_rejected(self):
        rows,events=fixture();rows[0]['observation']['edges'][0]['score']=-.3
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_first_output_change_rejected(self):
        rows,events=fixture();rows[0]['decision']['value']=False
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_feedback_boolean_change_rejected(self):
        rows,events=fixture();next(e['payload'] for e in events if e['event']=='r02_feedback')['correct']=True
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_document_hash_tamper_rejected(self):
        rows,events=fixture();rows[1]['memory_before']='0'*64
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_exact_semantic_decision_keeps_cost_differences(self):
        rows,_=fixture();a=rows[0]['decision'];b=deepcopy(a);b['cost']['kernel_ticks']+=1
        self.assertNotEqual(semantic_decision(a),semantic_decision(b))

    def test_no_global_id_replace(self):
        rows,events=fixture()
        change_after(rows,events,lambda m:m.update(extra=rows[0]['decision']['id']))
        with self.assertRaises(BaselineError):compare(rows,events)

    def test_difference_type_and_order(self):
        self.assertTrue(differences({'x':True},{'x':1}))
        self.assertTrue(differences([1,2],[2,1]))


class DurableMeasurements(unittest.TestCase):
    def data(self,root):
        journal=MeasurementJournal(root/'measurements.jsonl')
        p=dict(memory_digest='m',save_seconds=.1,load_seconds=.2)
        events=[dict(event='r02_engine_created',payload={'memory_hash':'m'}),dict(event='r02_decision',payload={})]
        init=dict(key='x',memory_digest='m',trace_start_seq=0,trace_end_seq=1,memory_copy_seconds=.01,engine_init_seconds=.02)
        journal.append('engine_initialized',init)
        journal.append('memory_saved',dict(checkpoint='live_after_adaptation.json',memory_digest='m',elapsed_seconds=.1))
        journal.append('memory_loaded',dict(checkpoint='live_after_adaptation.json',memory_digest='m',elapsed_seconds=.2))
        journal.append('probe_records_finished',dict(inferences=1,elapsed_seconds=.5))
        journal.close()
        records=[loads(x) for x in read(root/'measurements.jsonl').splitlines()]
        return records,events,p

    def test_durable_before_summary(self):
        with tempfile.TemporaryDirectory() as t:
            r,e,p=self.data(Path(t));self.assertTrue(validate_measurements(r,e,p)['chain_verified'])
            self.assertFalse((Path(t)/'summary.json').exists())

    def test_existing_journal_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x';p.write_bytes(b'keep')
            with self.assertRaises(FileExistsError):MeasurementJournal(p)
            self.assertEqual(p.read_bytes(),b'keep')

    def test_closed_journal_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            j=MeasurementJournal(Path(t)/'x');j.close()
            with self.assertRaises(BaselineError):j.append('x',{})

    def test_hash_tamper(self):
        with tempfile.TemporaryDirectory() as t:
            r,e,p=self.data(Path(t));r[0]['payload']['engine_init_seconds']+=1
            with self.assertRaises(BaselineError):validate_measurements(r,e,p)

    def test_missing_record_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            r,e,p=self.data(Path(t));r.pop()
            with self.assertRaises(BaselineError):validate_measurements(r,e,p)

    def test_io_timing_summary_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            r,e,p=self.data(Path(t));p['save_seconds']=.5
            with self.assertRaises(BaselineError):validate_measurements(r,e,p)

    def test_engine_count_mismatch(self):
        with tempfile.TemporaryDirectory() as t:
            r,e,p=self.data(Path(t));e.append(dict(event='r02_engine_created',payload={'memory_hash':'m'}))
            with self.assertRaises(BaselineError):validate_measurements(r,e,p)

    def test_platform_lf_bytes(self):
        with tempfile.TemporaryDirectory() as t:
            self.data(Path(t));self.assertNotIn(b'\r\n',read(Path(t)/'measurements.jsonl'))


class RecoveryBoundaries(unittest.TestCase):
    def test_existing_output_refused_before_read(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises(BaselineError):recover(p/'missing',p,p/'source')

    def test_nested_output_refused_before_read(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            with self.assertRaises(BaselineError):recover(p,p/'result',p/'source')

    def test_unknown_failure_is_not_recovered(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'FAILED.json').write_bytes(canonical(dict(state='failed',error='unknown',inferences=1)))
            with self.assertRaises(BaselineError):validate_raw(p)

    def test_complete_result_not_accepted_as_failed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'FAILED.json').write_bytes(canonical(dict(state='complete',error='',inferences=1)))
            with self.assertRaises(BaselineError):validate_raw(p)

    def test_duplicate_raw_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'FAILED.json').write_bytes(b'{"state":"failed","state":"complete"}')
            with self.assertRaises(BaselineError):validate_raw(p)

    def test_recovery_requires_its_own_manifest(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises((BaselineError,OSError)):verify_recovery(Path(t))

    def test_recovery_does_not_import_production_inference(self):
        banned={'hcr.runtime','hcr.learning','hcr.dynamics','hcr.expansion','hcr.activation'}
        for n in ('recover_probe.py','memory_equivalence.py','measurement_journal.py','audit_probe.py'):
            tree=ast.parse((HERE/n).read_text(encoding='utf-8'))
            self.assertFalse(any(isinstance(x,ast.ImportFrom) and x.module in banned for x in ast.walk(tree)))

    def test_missing_seed_contract_rejected(self):
        with self.assertRaises(BaselineError):contract_from_records([],[])


if __name__=='__main__':unittest.main()
