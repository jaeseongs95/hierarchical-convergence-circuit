"""R0.2.1 체크포인트 CLI. 기본 출력은 명시한 새 파일/폴더이며 기존 결과는 수정하지 않는다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import codec, session_io
from .model import ContractError, Mode


def main(argv=None):
    parser = argparse.ArgumentParser(prog='hcr session')
    commands = parser.add_subparsers(dest='command', required=True)
    start = commands.add_parser('start', help='공개 입력의 세션 시작 및 단계별 checkpoint')
    start.add_argument('--input', type=Path, required=True)
    start.add_argument('--out', type=Path, required=True, help='새 checkpoint JSON 파일')
    start.add_argument('--config', type=Path)
    start.add_argument('--memory', type=Path)
    start.add_argument('--session-id')
    start.add_argument('--graph-only', action='store_true')
    start.add_argument('--steps', type=int, default=1)
    resume = commands.add_parser('resume', help='checkpoint 복원 후 계속 진행; 기존 파일은 보존')
    resume.add_argument('--checkpoint', type=Path, required=True)
    resume.add_argument('--out', type=Path, required=True)
    resume.add_argument('--expect-sha256', help='외부에서 보관한 checkpoint document 해시')
    group = resume.add_mutually_exclusive_group()
    group.add_argument('--steps', type=int, default=1)
    group.add_argument('--complete', action='store_true')
    verify = commands.add_parser('verify', help='checkpoint 또는 session demo의 독립 기록 검산; 재추론 없음')
    vg = verify.add_mutually_exclusive_group(required=True)
    vg.add_argument('--checkpoint', type=Path)
    vg.add_argument('--run', type=Path)
    demo = commands.add_parser('demo', help='현재 R0.2 동작의 uninterrupted/snapshot-resume 비교')
    demo.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            from .evaluation.session_protocol import run_demo
            result = run_demo(args.out)
        elif args.command == 'verify':
            if args.run:
                from .evaluation.session_protocol import verify_run
                result = verify_run(args.run)
            else:
                from .sessions import verify_packet
                result = verify_packet(codec.loads(session_io.read_bytes(args.checkpoint)))
        else:
            from .sessions import AdaptiveSession
            if type(args.steps) is not int or not 0 <= args.steps <= 65537:
                raise ContractError('steps must be an integer in [0,65537]')
            source = args.input if args.command == 'start' else args.checkpoint
            session_io.new_output(args.out, inputs=[source])
            if args.command == 'start':
                from .cli import adaptive_config_from
                from .circuits import AdaptiveMemory
                config = adaptive_config_from(args.config)
                memory = AdaptiveMemory.load(args.memory, config) if args.memory else None
                obs = codec.observation_from(codec.loads(session_io.read_bytes(args.input)))
                session = AdaptiveSession(config, memory, session_id=args.session_id,
                                           use_circuits=not args.graph_only)
                session.begin(obs, Mode.FROZEN_EVAL)
            else:
                packet = codec.loads(session_io.read_bytes(args.checkpoint))
                if args.expect_sha256 is not None and packet.get('sha256') != args.expect_sha256:
                    raise ContractError('checkpoint does not match expected hash')
                session = AdaptiveSession.from_packet(packet)
                if session.phase == 'idle':
                    raise ContractError('already completed checkpoint; no pending inference to resume')
            decision = None
            if args.command == 'resume' and args.complete:
                decision = session.complete()
            else:
                for _ in range(args.steps):
                    if session.phase != 'running':
                        break
                    session.advance()
                # readout_ready인 checkpoint도 저장한다. finish는 --complete로 명시한다.
            io = session.save(args.out)
            result = dict(state='complete', phase=session.phase, output=str(args.out.resolve()),
                reference=session.reference, checkpoint_sha256=io['checkpoint_sha256'],
                decision=codec.plain(decision), snapshot_io=io, prior_checkpoint_modified=False)
        print(codec.dumps(result))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        print(codec.dumps(dict(state='failed', error=f'{type(exc).__name__}: {exc}')), file=sys.stderr)
        return 2
