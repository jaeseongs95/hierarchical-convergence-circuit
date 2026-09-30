from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import ast
import math
import shutil
import subprocess
import tempfile
import unittest
from hcr.model import (Config,EdgeObservation,Observation,ContractError,Program,Group,Link,Cost,Status,Mode,Feedback)
from hcr.dynamics import tick,settle
from hcr.binding import Topology,Binding,bind
from hcr.workspace import expand
from hcr.runtime import Engine
from hcr.tasks.toy_world import chain,diamond
from hcr.evaluation.reference import assess
from hcr import codec


class Contracts(unittest.TestCase):
    def test_config_finite_and_range(self):
        for kwargs in [{'damping':0},{'temperature':float('nan')},{'max_ticks':True},{'max_edges':999},{'learning_rate':1.1}]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ContractError):Config(**kwargs)
    def test_no_hidden_label_in_public_input(self):
        value=codec.plain(chain('x').observation);value['truth']=True
        with self.assertRaises(ContractError):codec.observation_from(value)
    def test_input_is_typed_immutable(self):
        with self.assertRaises(ContractError):Observation('x',0,'a','b',({'id':'e'},))
        with self.assertRaises(Exception):chain('x').observation.edges[0].score=1
    def test_duplicate_edge_and_arc_rejected(self):
        edge=EdgeObservation('e','a','b',.1)
        with self.assertRaises(ContractError):Observation('x',0,'a','b',(edge,edge))
        with self.assertRaises(ContractError):Observation('x',0,'a','b',(edge,EdgeObservation('f','a','b',.2)))
    def test_score_finite_range(self):
        for score in [True,float('inf'),1.01,-1.01]:
            with self.subTest(score=score),self.assertRaises(ContractError):EdgeObservation('e','a','b',score)
    def test_json_duplicate_and_nonfinite_rejected(self):
        for text in ['{"x":1,"x":2}','{"x":NaN}','{"x":1e999}']:
            with self.subTest(text=text),self.assertRaises(ContractError):codec.loads(text)
    def test_feedback_uses_real_bool(self):
        with self.assertRaises(ContractError):Feedback('f','d','0'*64,1,True)
    def test_binding_names_and_order_not_identity(self):
        first=chain('a',prefix='old').observation
        later=chain('b',prefix='new').observation;later=replace(later,edges=tuple(reversed(later.edges)))
        b=bind(Topology.from_observation(first),later,Config(),Cost())
        self.assertIsNotNone(b);self.assertEqual(b.edge_order,(1,0))
    def test_binding_stale_revision_rejected(self):
        obs=chain('a').observation;b=Binding(obs.digest,obs.revision,(0,1))
        with self.assertRaises(ContractError):b.check(replace(obs,revision=1))
    def test_guard_distinguishes_novel_topology(self):
        a=chain('a').observation;b=diamond('b').observation
        self.assertIsNone(bind(Topology.from_observation(a),b,Config(),Cost()))
    def test_inference_has_no_reference_or_environment_dependency(self):
        root=Path(__file__).resolve().parents[1]/'src/hcr'
        for name in ('runtime.py','binding.py','workspace.py','compiler.py','learning.py','dynamics.py','circuits.py','proof.py'):
            tree=ast.parse((root/name).read_text(encoding='utf-8'))
            imports=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):imports += [n.name for n in node.names]
                elif isinstance(node,ast.ImportFrom):imports.append(node.module or '')
            self.assertFalse(any('evaluation' in n or 'toy_world' in n for n in imports),(name,imports))
    def test_python312_syntax_all_sources(self):
        root=Path(__file__).resolve().parents[1]
        for file in list((root/'src').rglob('*.py'))+list((root/'tests').glob('*.py'))+list((root/'scripts').glob('*.py'))+[root/'hcr.py']:
            ast.parse(file.read_text(encoding='utf-8-sig'),filename=str(file),feature_version=(3,12))
    def test_windows_launcher_native_parser_when_available(self):
        exe=shutil.which('pwsh') or shutil.which('powershell')
        if exe is None:self.skipTest('PowerShell native parser unavailable in this environment')
        path=str(Path(__file__).resolve().parents[1]/'Run-HCR.ps1').replace("'","''")
        code="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+path+"',[ref]$t,[ref]$e);if($e.Count){$e;exit 1}"
        result=subprocess.run([exe,'-NoProfile','-Command',code],capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace'))


class Dynamics(unittest.TestCase):
    def test_same_kernel_independent_of_level_name(self):
        program=Program((Group('e',0,.3),Group('goal',1,.3)),(),((0,),),1)
        state={'e':.4,'goal':.4};drives={'e':.1,'goal':.1};new=tick(program,state,drives,Config(),Cost())
        self.assertEqual(new['e'],new['goal']);self.assertEqual(state,{'e':.4,'goal':.4})
    def test_synchronous_order_invariance(self):
        obs=chain('a').observation;p=expand(Topology.from_observation(obs),Config(),Cost())
        state={g.id:.37 for g in p.groups};d={'e:0':3,'e:1':3};cost=Cost()
        one=tick(p,state,d,Config(),cost)
        reordered=replace(p,groups=tuple(reversed(p.groups)))
        self.assertEqual(one,tick(reordered,state,d,Config(),Cost()))
    def test_all_states_bounded(self):
        obs=diamond('a').observation;p=expand(Topology.from_observation(obs),Config(),Cost())
        x={g.id:.5 for g in p.groups}
        for _ in range(70):
            x=tick(p,x,{'e:0':100,'e:1':-100},Config(),Cost())
            self.assertTrue(all(0<=v<=1 and math.isfinite(v) for v in x.values()))
    def test_invalid_state_not_silently_fixed(self):
        p=Program((Group('goal',1),),(),((0,),),1)
        with self.assertRaises(ContractError):tick(p,{'goal':float('nan')},{},Config(),Cost())
    def test_stable_ambiguous_not_a_decision(self):
        p=Program((Group('goal',1),),(),((0,),),1)
        _,c=settle(p,{},Config(),Cost());self.assertEqual(c.status,Status.STABLE_AMBIGUOUS)
    def test_oscillation_reported(self):
        p=Program((Group('goal',1),),(Link('goal','goal',-6,'support'),),((0,),),1)
        config=Config(damping=1,self_excitation=0,inhibition=0)
        _,c=settle(p,{},config,Cost(),initial={'goal':.9});self.assertEqual(c.status,Status.OSCILLATING)
    def test_tick_budget_is_not_convergence(self):
        p=Program((Group('goal',1),),(),((0,),),1)
        _,c=settle(p,{'goal':1},Config(max_ticks=4,patience=4),Cost())
        self.assertEqual(c.status,Status.BUDGET_EXHAUSTED)
    def test_top_down_changes_actual_lower_state(self):
        obs=chain('x',(False,True),(-.06,.92)).observation;p=expand(Topology.from_observation(obs),Config(),Cost())
        drives={g.id:1.3 if g.level==1 else -.24 if g.id=='e:0' else 3.68 for g in p.groups}
        on,_=settle(p,drives,Config(),Cost(),top_down=True);off,_=settle(p,drives,Config(),Cost(),top_down=False)
        self.assertGreater(abs(on['e:0']-off['e:0']),.01)
    def test_path_budget_not_silently_pruned(self):
        engine=Engine(Config(max_paths=1));d=engine.infer(diamond('x').observation)
        self.assertIsNone(d.value);self.assertEqual(d.convergence.status,Status.BUDGET_EXHAUSTED)
    def test_no_path_yields_no_candidate_not_fake_proof(self):
        obs=Observation('x',0,'a','c',(EdgeObservation('e','a','b',.9),EdgeObservation('f','c','b',.9)))
        d=Engine().infer(obs);self.assertIsNone(d.value);self.assertEqual(d.convergence.status,Status.NO_CANDIDATE)

    def test_same_input_can_have_two_stable_states_in_explicit_unit_fixture(self):
        p=Program((Group('goal',1),),(),((0,),),1)
        c=Config(self_excitation=5,inhibition=0)
        left,lc=settle(p,{},c,Cost(),initial={'goal':.4})
        right,rc=settle(p,{},c,Cost(),initial={'goal':.6})
        self.assertEqual(lc.status,Status.STABLE_DECISION);self.assertEqual(rc.status,Status.STABLE_DECISION)
        self.assertLess(left['goal'],.1);self.assertGreater(right['goal'],.9)
