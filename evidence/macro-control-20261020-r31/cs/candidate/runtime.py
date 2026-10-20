"""Direct native engine; explicit research records, never native checkpoint claims."""
from contextlib import contextmanager
import time
from hcr import codec,expansion
from hcr.circuits import AdaptiveMemory
from hcr.model import Mode,Feedback
from hcr.runtime import AdaptiveEngine
from hcr.trace import Trace
from tools.r31_macro_control.macro import OrdinaryMacroPool

@contextmanager
def control(arm):
    original=expansion.CircuitActivationPool
    try:
        if arm=='macro':expansion.CircuitActivationPool=OrdinaryMacroPool
        yield
    finally:expansion.CircuitActivationPool=original

def infer(public,memory,p,arm,training=False):
    cfg=codec.adaptive_config_from(p['config']);m=AdaptiveMemory.from_document(memory,cfg)
    trace=Trace();cpu=time.process_time();wall=time.perf_counter()
    with control(arm):
        engine=AdaptiveEngine(cfg,m,trace,use_circuits=arm!='primitive',top_down=True,allow_reexpansion=True,judgment_prior='route_only')
        before=m.document();engine.begin(codec.observation_from(public),Mode.TRAIN if training else Mode.FROZEN_EVAL)
        advances=0
        while not engine._pending.ready:
            if advances>=p['max_advances_per_session']:raise ValueError('advance cap')
            # One advance may settle a pool and a decision network.
            if engine._pending.cost.kernel_ticks+2*cfg.kernel.max_ticks>p['max_kernel_ticks_per_session']:raise ValueError('reserved tick cap')
            engine.advance();advances+=1
        decision=codec.plain(engine.finish())
    if m.document()!=before:raise ValueError('inference memory mutation')
    result=dict(schema='hcr-r31-research-record-v1',arm=arm,training=training,public=public,memory_before=before,
        memory_after_inference=m.document(),decision=decision,advances=advances)
    # Include one full result+trace JSON serialization within the measured session.
    codec.dumps(dict(result,records=trace.records))
    result['session_timing']=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
    return result,engine

def learn(record,engine,truth,index):
    from hcr.evaluation.reference import assess
    cpu=time.process_time();wall=time.perf_counter()
    assessment=codec.plain(assess(codec.adaptive_decision_from(record['decision']),codec.observation_from(record['public']),truth))
    record['reference_timing']=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
    feedback=Feedback('r31-feedback-'+str(index),record['decision']['id'],record['decision']['observation_digest'],
        assessment['correct'],assessment['proof_valid'] and assessment['assumption_correct'] is True)
    engine.trace.emit('r31_external_assessment',dict(assessment=assessment,truth=truth))
    cpu=time.process_time();wall=time.perf_counter();patch=engine.feedback(feedback)
    record['learning_timing']=dict(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
    record.update(assessment=assessment,feedback=codec.plain(feedback),patch=patch,memory_after_learning=engine.memory.document())
