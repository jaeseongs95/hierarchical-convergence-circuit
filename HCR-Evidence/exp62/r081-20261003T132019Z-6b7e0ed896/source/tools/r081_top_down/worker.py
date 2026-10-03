"""Native evaluation only; no world, reference scoring, learning or repair."""
import argparse
from pathlib import Path
from tools.r050_review_boundary.common import dump, load
from tools.r050_review_boundary.common import require

def execute(plan, case, memory, gate, mode, location, identity, *, top_down):
    from hcr import codec
    from hcr.circuits import AdaptiveMemory
    from hcr.model import Mode
    from hcr.sessions import AdaptiveSession
    from hcr.review import capture_candidate
    cfg = codec.adaptive_config_from(plan['config'])
    session = AdaptiveSession(cfg, AdaptiveMemory.from_document(memory, cfg), session_id=identity,
        use_circuits=gate, top_down=top_down, allow_reexpansion=True, judgment_prior='route_only')
    dump(location/'step-000-init.json', session.packet())
    session.begin(codec.observation_from(case['observation']), Mode(mode))
    dump(location/'step-001-begin.json', session.packet())
    advances = 0
    # Existing core admits at most one activation pool plus one decision kernel.
    bound = cfg.kernel.max_ticks * (2 if gate and memory['circuits'] else 1)
    while session.phase == 'running':
        before = session.current['pending']['cost']['kernel_ticks']
        if advances >= plan['limits']['max_advances_per_session'] or before+bound > plan['limits']['max_kernel_ticks_per_session']:
            break
        session.advance()
        advances += 1
        dump(location/f'step-{advances+1:03d}-advance.json', session.packet())
        require(session.current['pending']['cost']['kernel_ticks']-before <= bound, 'Native advance exceeded reservation')
    candidate = capture_candidate(session, 0) if session.phase=='readout_ready' else None
    if candidate is not None:
        dump(location/'candidate.json', candidate)
    require(session.memory_document == memory, 'Inference changed persistent memory')
    return dict(packet=session.packet(),candidate=candidate,advances=advances,
        ready=session.phase=='readout_ready',stop='readout_ready' if session.phase=='readout_ready' else 'external_compute_budget')



def main(out, review_dir=None, writer_id=None, reviewer_id=None):
    from tools.r081_top_down.review_gate import check_source, reviewed
    check_source(out)
    require(not (out/'failure.json').exists(), 'Prior failure requires diagnosis; no retry')
    require(load(out/'review_policy.json') == dict(writer_id=writer_id,reviewer_id=reviewer_id), 'Frozen review identities changed')
    require(load(out/'validation/selftest.json')['verified'] is True, 'Pre-native selftest required')
    if not reviewed(out, review_dir, writer_id, reviewer_id):
        return
    plan = load(out/'plan.json')
    memory = load(out/'parent/memory/3.json')
    for cell in plan['cells']:
        location = out/'evaluation'/cell['id']
        if (location/'inference.json').exists():
            if not reviewed(out, review_dir, writer_id, reviewer_id, cell['id']):
                return
            continue
        # Exclusive directory creation preserves partial first failures and blocks reruns.
        location.mkdir(parents=True, exist_ok=False)
        from datetime import datetime, timezone
        from time import perf_counter
        started_at=datetime.now(timezone.utc).isoformat(); started=perf_counter()
        execution = execute(plan, cell, memory, cell['use_circuits'], 'frozen_eval',
            out/'evaluation'/cell['id']/'progress', 'r081-'+cell['id'], top_down=cell['top_down'])
        dump(out/'evaluation'/cell['id']/'inference.json', dict(cell=cell, execution=execution))
        dump(location/'native_timing.json',dict(started_at=started_at,
             finished_at=datetime.now(timezone.utc).isoformat(),duration_seconds=perf_counter()-started))
        print(cell['id'], execution['stop'], flush=True)
        reviewed(out, review_dir, writer_id, reviewer_id, cell['id'])
        return  # At most one new condition per invocation; never pre-approve future raw.


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--review-dir', type=Path)
    p.add_argument('--writer-id', required=True); p.add_argument('--reviewer-id', required=True)
    a=p.parse_args(); main(a.out,a.review_dir,a.writer_id,a.reviewer_id)
