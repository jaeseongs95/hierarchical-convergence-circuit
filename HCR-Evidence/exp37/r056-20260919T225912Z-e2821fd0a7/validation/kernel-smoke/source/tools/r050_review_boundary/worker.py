"""Actual AdaptiveSession worker. No evaluator or hidden-world answer is imported.

All interventions are explicit arms. Existing core methods, states, IDs, proofs,
and first failures are preserved. Restart is never described as continuation.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import fields
from pathlib import Path
from time import perf_counter
import traceback
from .common import dump, load, require, seal, unseal
from .protocol import ARMS, revised_input, select_probe, terminal


def native():
    from hcr import codec
    from hcr.model import AdaptiveCost, Mode
    from hcr.circuits import AdaptiveMemory
    from hcr.sessions import AdaptiveSession
    from hcr.review import capture_candidate, choose_action, consume_measurement, measurement_request, ReviewLimits
    return codec, AdaptiveCost, Mode, AdaptiveMemory, AdaptiveSession, capture_candidate, choose_action, consume_measurement, measurement_request, ReviewLimits


def execute_session(plan: dict, case: dict, observation: dict, location: Path,
                    label: str, segment: int) -> dict:
    codec, Cost, Mode, Memory, Session, capture, *_ = native()
    cfg = codec.adaptive_config_from(plan['config'])
    mem = Memory.from_document(deepcopy(plan['empty_memory']), cfg)
    # Critical: preserve ALL switches, including top_down=False, on restart.
    switches = dict(use_circuits=True, top_down=case['top_down'], allow_reexpansion=True)
    session = Session(cfg, mem, session_id='r050-' + case['id'] + '-' + label,
                      judgment_prior='legacy', **switches)
    dump(location / 'step-000-init.json', session.packet())
    session.begin(codec.observation_from(deepcopy(observation)), Mode.FROZEN_EVAL)
    dump(location / 'step-001-begin.json', session.packet())
    advances = 0
    limit = plan['limits']
    while session.phase == 'running':
        before = session.current['pending']['cost']['kernel_ticks']
        # Empty frozen memory -> one kernel maximum per native advance.
        if advances >= limit['max_advances_per_session'] or before + cfg.kernel.max_ticks > limit['max_kernel_ticks_per_session']:
            break
        session.advance()
        advances += 1
        dump(location / f'step-{advances + 1:03d}-advance.json', session.packet())
        require(session.current['pending']['cost']['kernel_ticks'] <= limit['max_kernel_ticks_per_session'],
                'Native advance exceeded the reserved budget')
    packet = session.packet()
    candidate = capture(session, segment) if session.phase == 'readout_ready' else None
    if candidate is not None:
        dump(location / 'candidate.json', candidate)
    require(session.memory_document == plan['empty_memory'], 'Frozen memory changed')
    require(packet['document']['engine']['switches'] == switches, 'Session switch drift')
    return dict(packet=packet, candidate=candidate, advances=advances,
                ready=session.phase == 'readout_ready',
                stop='readout_ready' if session.phase == 'readout_ready' else 'external_compute_budget')


def make_baseline(plan: dict, case: dict, root: Path) -> dict:
    started = perf_counter()
    execution = execute_session(plan, case, case['observation'], root / 'progress' / case['id'] / 'baseline', 'baseline', 0)
    candidate = execution['candidate']
    *_, choose, consume, request, Limits = native()
    core = execution['packet']['document']['engine']
    from hcr import codec
    limits = Limits(max_extra_advances=plan['limits']['max_advances_per_session'],
                    max_extra_kernel_ticks=plan['limits']['max_kernel_ticks_per_session'], max_measurements=1)
    action, target = choose('observe_first', core, candidate,
                            dict(extra_advances=0, extra_kernel_ticks=0, measurements=0, restarts=0),
                            limits, codec.adaptive_config_from(plan['config']), False)
    return seal(dict(schema='hcc-r050-baseline-v1', case=case, execution=execution,
                     native_observe_first_next_action=dict(action=action, target=target),
                     experimental_probe_target=select_probe(case['observation'], candidate),
                     preparation_seconds=perf_counter() - started))


def run_arm(plan: dict, case: dict, baseline: dict, arm: str, root: Path) -> dict:
    require(arm in ARMS, 'Unexpected arm')
    started = perf_counter()
    first = baseline['execution']['candidate']
    target = deepcopy(baseline['experimental_probe_target'])
    result = dict(schema='hcc-r050-arm-v1', case_id=case['id'], arm=arm,
                  baseline_sha256=baseline['sha256'],
                  initial_candidate_id=None if first is None else first['candidate_id'],
                  target=target, request=None, reply=None, consumption=None,
                  restart_observation=None, execution=None, restart_reason=None,
                  terminal=terminal(first), stop_reason=None,
                  same_state_continuation=False, learned=False, hidden_world_access=False)
    if not baseline['execution']['ready']:
        result['stop_reason'] = 'baseline_external_compute_budget'
    elif first['readout']['accepted']:
        result['stop_reason'] = 'initially_supported'
    elif arm == 'hold':
        result['stop_reason'] = 'hold_after_gate'
    elif arm != 'same_input_restart' and target['edge_id'] is None:
        result['stop_reason'] = 'no_probe_target'
    elif baseline['execution']['packet']['document']['engine']['pending']['failure_reason'] is not None:
        result['stop_reason'] = 'baseline_engine_failure'
    else:
        proposed = revised_input(case['observation'], arm, target)
        if arm in ('echo_revision_restart', 'strength_revision_restart'):
            codec, *_ = native()
            from hcr.review import measurement_request, consume_measurement
            obs = codec.observation_from(deepcopy(case['observation']))
            request = measurement_request(obs, first, 1, target['edge_id'])
            score = proposed['edges'][target['slot']]['score']
            response = dict(request_sha256=request['sha256'], status='measured',
                            scores={target['edge_id']: score},
                            source='r050-public-score-echo' if arm == 'echo_revision_restart' else 'r050-sign-preserving-strength-manipulation')
            measure = root / 'measurements' / case['id'] / arm
            dump(measure / 'request.json', request)
            dump(measure / 'response.json', response)  # preserve before validation
            revised, status = consume_measurement(obs, request, response)
            result.update(request=request, reply=response, consumption=status)
            if arm == 'echo_revision_restart':
                require(revised is None and status == 'measurement_no_new_information', 'Echo changed native observation')
                # Explicit revision-only metadata control. Do not pretend native
                # consume_measurement requested a restart for an unchanged score.
                result['restart_reason'] = 'explicit_echo_revision_control_not_native_retry'
            else:
                require(revised is not None and status == 'measurement_applied'
                        and codec.plain(revised) == proposed, 'Unexpected measurement application')
                result['restart_reason'] = 'explicit_single_score_strength_intervention'
        else:
            result['restart_reason'] = 'explicit_same_input_recomputation_control'
        result['restart_observation'] = proposed
        dump(root / 'interventions' / case['id'] / (arm + '.json'),
             dict(arm=arm, baseline_sha256=baseline['sha256'], reason=result['restart_reason'],
                  observation=proposed, target=target, request=result['request'], reply=result['reply'],
                  consumption=result['consumption']))
        execution = execute_session(plan, case, proposed, root / 'progress' / case['id'] / arm, arm, 1)
        result.update(execution=execution, terminal=terminal(execution['candidate']),
                      stop_reason=execution['stop'])
    result['arm_wall_seconds'] = perf_counter() - started
    return seal(result)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True, type=Path)
    a = ap.parse_args(argv)
    plan = unseal(load(a.run / 'plan.json'), 'hcc-r050-plan-v1')
    # No external truth labels appear in the producer plan.
    require(all(set(c) == {'id', 'strength', 'relation', 'identity_variant', 'top_down', 'observation'}
                for c in plan['cases']), 'Unexpected private case fields')
    for case in plan['cases']:
        try:
            baseline = make_baseline(plan, case, a.run)
            dump(a.run / 'baselines' / (case['id'] + '.json'), baseline)
            for arm in ARMS:
                record = run_arm(plan, case, baseline, arm, a.run)
                dump(a.run / 'raw' / case['id'] / (arm + '.json'), record)
            print(case['id'], 'recorded', flush=True)
        except BaseException as exc:
            dump(a.run / 'worker_failure.json', dict(case_id=case['id'], exception=type(exc).__name__,
                 message=str(exc), traceback=traceback.format_exc(), automatic_retry=False,
                 partial_evidence_retained=True))
            raise
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
