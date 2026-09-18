"""Verified EXP26 OFF table references + unchanged native core; not full AdaptiveSession replay."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tools")]
from dataclasses import asdict
import json,unittest
from hcr.model import Config
from r046_thought_carry.runtime import run_query
from r046_thought_carry.evaluator import audit_record
REF=json.loads((Path(__file__).parent/'data/EXP26_OFF_reference.json').read_text(encoding='utf-8'))
class ParentCoreRegression(unittest.TestCase):pass

def make(row):
    def test(self):
        cfg=Config();self.assertEqual(cfg.signature,REF['kernel_config_signature'])
        r=run_query(row['observation'],asdict(cfg));a=audit_record(r)
        self.assertEqual(a['dynamics_sha256'],row['dynamics_sha256'])
        self.assertEqual(r['native_cost']['kernel_ticks'],row['ticks'])
        self.assertIs(r['raw_value'],row['value']);self.assertIs(r['accepted'],row['accepted'])
    return test
for r in REF['rows']:setattr(ParentCoreRegression,'test_OFF_'+r['trial_id'],make(r))
