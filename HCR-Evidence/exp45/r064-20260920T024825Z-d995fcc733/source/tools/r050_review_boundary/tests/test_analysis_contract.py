"""Synthetic audit-table tampering tests. Not HCC or research evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from tools.r050_review_boundary.analysis_contract import validate_audit_tables, validate_report_inputs, verify_analysis
from tools.r050_review_boundary.common import IntegrityError, load
from tools.r050_review_boundary.reporting import create, render_artifacts
from test_reporting import fixture, write_fixture


class AnalysisContract(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.audit=write_fixture(self.root); create(self.root)
    def tearDown(self): self.tmp.cleanup()
    def test_valid_render_and_readonly_recheck(self):
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report=verify_analysis(self.root,self.audit)
        self.assertTrue(report['verified']); self.assertEqual(report['new_inferences'],0)
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
    def test_summary_tampering_is_rejected(self):
        path=self.root/'analysis/summary.json'; doc=json.loads(path.read_text())
        doc['groups']['hold']['correct_adoptions']=24
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(IntegrityError,'summary.json'):verify_analysis(self.root,self.audit)
    def test_csv_tampering_is_rejected(self):
        path=self.root/'analysis/trials.csv'; path.write_bytes(path.read_bytes()+b'fabricated,row\n')
        with self.assertRaisesRegex(IntegrityError,'trials.csv'):verify_analysis(self.root,self.audit)
    def test_markdown_tampering_is_rejected(self):
        path=self.root/'analysis/summary.ko.md';path.write_text('all trials passed')
        with self.assertRaisesRegex(IntegrityError,'summary.ko.md'):verify_analysis(self.root,self.audit)
    def test_saved_audit_not_used_as_its_own_evidence(self):
        path=self.root/'analysis/audit.json';doc=load(path);doc['extra_claim']='invented';path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(IntegrityError,'Saved audit differs'):verify_analysis(self.root,self.audit)
    def test_duplicate_case_arm_rejected_despite_same_count(self):
        doc=fixture();doc['rows'][-1]=deepcopy(doc['rows'][0])
        with self.assertRaisesRegex(IntegrityError,'duplicate'):validate_audit_tables(doc)
    def test_missing_comparison_rejected(self):
        doc=fixture();doc['numerical_comparisons'].pop()
        with self.assertRaisesRegex(IntegrityError,'coverage'):validate_audit_tables(doc)
    def test_abstention_not_counted_correct(self):
        doc=fixture();doc['rows'][0]['final']['adopted_correct']=True
        with self.assertRaisesRegex(IntegrityError,'abstention'):validate_audit_tables(doc)
    def test_baseline_counted_only_once(self):
        doc=fixture();doc['unique_baseline_counters']['kernel_ticks']=1
        with self.assertRaisesRegex(IntegrityError,'Baseline cost'):validate_audit_tables(doc)
    def test_paired_initial_source_must_match(self):
        doc=fixture();doc['rows'][1]['baseline_sha256']='other'
        with self.assertRaisesRegex(IntegrityError,'Paired rows'):validate_audit_tables(doc)
    def test_boolean_restart_count_rejected(self):
        doc=fixture();doc['rows'][1]['restarts']=True
        with self.assertRaisesRegex(IntegrityError,'event count'):validate_audit_tables(doc)
    def test_non_evaluated_comparison_cannot_have_result(self):
        doc=fixture();doc['numerical_comparisons'][0]['comparison']={'final_state_close':True}
        with self.assertRaisesRegex(IntegrityError,'Unevaluated'):validate_audit_tables(doc)
    def test_foreign_plan_rejected(self):
        doc=fixture();doc['plan_sha256']='0'*64
        with self.assertRaisesRegex(IntegrityError,'another plan'):validate_report_inputs(self.root,doc)
    def test_new_raw_file_after_audit_rejected(self):
        (self.root/'raw').mkdir();(self.root/'raw/late.json').write_text('{}')
        with self.assertRaisesRegex(IntegrityError,'Raw evidence changed'):validate_report_inputs(self.root,self.audit)
    def test_render_has_no_filesystem_side_effect(self):
        before=set(self.root.rglob('*'));summary,artifacts=render_artifacts(self.audit)
        self.assertEqual(set(artifacts),{'summary.json','trials.csv','summary.ko.md'})
        self.assertEqual(before,set(self.root.rglob('*')))


if __name__=='__main__':unittest.main()
