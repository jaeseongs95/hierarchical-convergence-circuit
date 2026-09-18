"""Test analysis sealing with explicitly synthetic evaluator output. No native replay claimed."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from r045_direct_support import audit,reporting,storage as io
from r045_direct_support.tests.fixtures import report_records


def fixture():
    rs=report_records();summary=reporting.summarize(rs)
    report=dict(schema='synthetic-unit-audit-only',raw_manifest_sha256='a'*64,verified=True)
    return summary,report,{r['trial']['id']:r for r in rs},{}


class AnalysisSealTests(unittest.TestCase):
    def test_write_and_readonly_verify(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=fixture()):
                audit.write_analysis(root)
                before={n:io.file_hash(root/n) for n in io.inventory(root)}
                audit.write_analysis(root,check_only=True)
                self.assertEqual(before,{n:io.file_hash(root/n) for n in io.inventory(root)})
    def test_analysis_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=fixture()):
                audit.write_analysis(root);before=io.file_hash(root/'analysis/summary.json')
                with self.assertRaises(FileExistsError):audit.write_analysis(root)
            self.assertEqual(before,io.file_hash(root/'analysis/summary.json'))
            self.assertEqual(len(list((root/'audit_failures').glob('*.json'))),1)
    def test_summary_tamper_detected_even_after_resealing_file_hash(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=fixture()):
                audit.write_analysis(root)
                p=root/'analysis/summary.json';s=io.load(p);s['native_trials']=999;p.write_bytes(io.canonical(s)+b'\n')
                p=root/'analysis/manifest.json';m=io.load(p);m['files']['summary.json']=io.file_hash(root/'analysis/summary.json');p.write_bytes(io.canonical(m)+b'\n')
                with self.assertRaises(ValueError):audit.write_analysis(root,check_only=True)
    def test_unlisted_analysis_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(audit,'verify_raw',return_value=fixture()):
                audit.write_analysis(root);io.put(root/'analysis/hidden_retry.json',{})
                with self.assertRaises(ValueError):audit.write_analysis(root,check_only=True)
    def test_failure_class_preserved(self):
        for exc,kind in ((ImportError('missing-native'),'dependency_failure'),(UnicodeError('bad-bytes'),'parsing_failure')):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                root=Path(d)
                with patch.object(audit,'verify_raw',side_effect=exc):
                    with self.assertRaises(type(exc)):audit.write_analysis(root)
                f=io.load(next((root/'audit_failures').glob('*.json')));self.assertEqual(f['status'],kind)
                self.assertFalse((root/'analysis/manifest.json').exists())
    def test_no_runtime_imports_in_new_measurements(self):
        import ast
        from r045_direct_support import measurements
        tree=ast.parse(Path(measurements.__file__).read_text(encoding='utf-8'))
        modules=[n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
        self.assertEqual(modules,['copy','functools','storage'])

if __name__=='__main__':unittest.main()
