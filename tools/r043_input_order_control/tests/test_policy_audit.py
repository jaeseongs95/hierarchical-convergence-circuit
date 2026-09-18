from copy import deepcopy
import unittest
from r043_input_order_control import policy_audit
from r043_input_order_control.storage import digest

def fixture(ids=None,paths=None):
    ids=['z','a','m'] if ids is None else ids
    paths=[[0],[1,2]] if paths is None else paths
    view=dict(schema='hcr-frontier-view-r041-v1',edge_ids=ids,frontier_paths=paths)
    path=None if not paths else paths[0]
    usage=dict(decision_calls=1,frontier_items_examined=int(bool(paths)),edge_id_reads=0 if path is None else len(path),
        key_comparisons=0,priority_transitions=0,priority_match_scans=0)
    d=dict(schema='hcr-frontier-choice-r041-v1',scheduler='input_order',input_sha256=digest(view),
        selected_index=None if not paths else 0,selected_path=path,
        selected_edge_ids=None if path is None else [ids[i] for i in path],priority_required=False,usage=usage)
    return dict(scheduler='input_order',scheduler_usage=deepcopy(usage),events=[
        dict(event='schedule_requested',scheduler='input_order',input_sha256=digest(view),view=view),
        dict(event='schedule_decided',decision=d)])

class PolicyAudit(unittest.TestCase):
    def test_first_slot_not_minimum_ID(self):
        b=fixture();r=policy_audit.check(b)
        self.assertEqual(r['slot_decisions'][0]['selected_native_IDs'],['z'])
        self.assertEqual(r['usage']['key_comparisons'],0);self.assertEqual(r['usage']['edge_id_reads'],1)
    def test_ID_relabel_changes_log_not_slot(self):
        a=policy_audit.check(fixture());b=policy_audit.check(fixture(['a','z','m']))
        self.assertEqual(a['slot_decisions'][0]['selected_slot_path'],b['slot_decisions'][0]['selected_slot_path'])
        self.assertNotEqual(a['slot_decisions'][0]['selected_native_IDs'],b['slot_decisions'][0]['selected_native_IDs'])
    def test_empty_frontier(self):
        r=policy_audit.check(fixture(paths=[]));self.assertIsNone(r['slot_decisions'][0]['selected_slot_index'])
    def test_empty_root_path(self):
        r=policy_audit.check(fixture(paths=[[]]));self.assertEqual(r['slot_decisions'][0]['selected_slot_path'],[])
        self.assertEqual(r['usage']['edge_id_reads'],0)
    def test_no_mutation(self):
        b=fixture();before=digest(b);policy_audit.check(b);self.assertEqual(digest(b),before)
    def test_decision_mutations_rejected(self):
        for key,value in [('selected_index',1),('selected_path',[1,2]),('selected_edge_ids',['a','m']),
                          ('priority_required',True),('scheduler','edge_id_min'),('input_sha256','bad')]:
            with self.subTest(key=key):
                b=fixture();b['events'][1]['decision'][key]=value
                with self.assertRaises(ValueError):policy_audit.check(b)
    def test_usage_mutations_rejected(self):
        for key in ('edge_id_reads','key_comparisons','priority_transitions','priority_match_scans','decision_calls'):
            with self.subTest(key=key):
                b=fixture();b['events'][1]['decision']['usage'][key]+=1
                with self.assertRaises(ValueError):policy_audit.check(b)
    def test_aggregate_mutation_rejected(self):
        b=fixture();b['scheduler_usage']['edge_id_reads']+=1
        with self.assertRaises(ValueError):policy_audit.check(b)
    def test_priority_event_rejected(self):
        b=fixture();b['events'].append(dict(event='priority_requested'))
        with self.assertRaises(ValueError):policy_audit.check(b)
    def test_missing_decision_rejected(self):
        b=fixture();b['events'].pop()
        with self.assertRaises(ValueError):policy_audit.check(b)
    def test_undeclared_world_projection_rejected(self):
        b=fixture();b['events'][0]['view']['world']='oracle'
        with self.assertRaises(ValueError):policy_audit.check(b)
    def test_invalid_frontier_slots(self):
        for paths in ([[True]],[[9]],[[0],[0]]):
            with self.subTest(paths=paths):
                b=fixture();b['events'][0]['view']['frontier_paths']=paths
                b['events'][0]['input_sha256']=digest(b['events'][0]['view'])
                with self.assertRaises(ValueError):policy_audit.check(b)
