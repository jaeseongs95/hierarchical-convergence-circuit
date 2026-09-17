"""CLI는 입출력만 연결한다. 판단과 학습 로직은 runtime에 한 번만 구현한다."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import tomllib
from .model import Config, ContractError, Mode
from . import codec


def config_from(path:Path|None) -> Config:
    if path is None: return Config()
    data=tomllib.loads(path.read_text(encoding='utf-8'))
    if set(data)!={'engine'}:raise ContractError('설정은 [engine] 항목만 허용한다.')
    try:return Config(**data['engine'])
    except TypeError as exc:raise ContractError('알 수 없는 engine 설정') from exc



def adaptive_config_from(path: Path | None):
    """R0.1 설정과 섞지 않고 [engine]+[adaptive]를 명시적으로 읽는다."""
    from .model import AdaptiveConfig
    if path is None:
        return AdaptiveConfig()
    data = tomllib.loads(path.read_text(encoding='utf-8-sig'))
    if set(data) != {'engine', 'adaptive'}:
        raise ContractError('R0.2 설정은 [engine]과 [adaptive] 항목이 필요하다.')
    return codec.adaptive_config_from(dict(kernel=data['engine'], **data['adaptive']))

def main(argv:list[str]|None=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == 'session':
        from .session_cli import main as session_main
        return session_main(argv[1:])
    parser=argparse.ArgumentParser(prog='hcr',description='HCR: R0.1 기준선 / R0.2 adaptive graph↔circuit 개발 엔진')
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('session', help='R0.2.1: start/resume/verify/demo — hcr session --help')
    check=commands.add_parser('check',help='소스·단위·통합 시험. 실제 네트워크 접속 금지.')
    check.add_argument('--out',type=Path,help='선택: 시험 영수증 JSON. 기존 파일 덮어쓰기 없음.')
    demo=commands.add_parser('demo',help='학습·동결평가·오수렴·재확장·재시작 개발 실행')
    demo.add_argument('--out',type=Path,required=True);demo.add_argument('--config',type=Path)
    demo.add_argument('--engine', choices=('r01', 'r02'), default='r01', help='생략 시 R0.1 호환 동작')
    verify=commands.add_parser('verify',help='완료 demo 결과의 해시·tick·proof·집계 재검산')
    verify.add_argument('--run',type=Path,required=True);verify.add_argument('--out',type=Path)
    infer=commands.add_parser('infer',help='공개 관측만으로 동결 추론. 정답/feedback 없음.')
    infer.add_argument('--input',type=Path,required=True);infer.add_argument('--memory',type=Path)
    infer.add_argument('--config',type=Path);infer.add_argument('--out',type=Path,required=True)
    infer.add_argument('--engine', choices=('r01', 'r02'), default='r01')
    args=parser.parse_args(argv)
    try:
        if args.command=='check':
            import importlib.util
            root=Path(__file__).resolve().parents[2]
            script=root/'scripts/selftest.py'
            if not script.is_file():raise ContractError('check는 tests/scripts를 포함한 소스 배포본에서 실행하세요.')
            spec=importlib.util.spec_from_file_location('hcr_selftest',script)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            result=module.run_tests(root)
            if args.out:codec.save(args.out,result)
            print(codec.dumps(result))
            return 0 if result['failures']==result['errors']==0 else 2
        if args.command=='demo':
            if args.engine == 'r02':
                from .evaluation.adaptive_protocol import run_demo
                summary = run_demo(args.out, adaptive_config_from(args.config))
                print(codec.dumps(dict(complete=True, engine='r02', directory=str(args.out.resolve()),
                                       groups=summary['groups'], adaptation=summary['adaptation'],
                                       actual_llm_calls=0, actual_network_calls=0)))
                return 0
            from .evaluation.protocol import run_demo
            summary=run_demo(args.out,config_from(args.config))
            print(codec.dumps({'complete':True,'directory':str(args.out.resolve()),'new_llm_calls':0,
                              'training':summary['training'],'frozen_eval':summary['frozen_eval'],
                              'adaptation':summary['adaptation'],'retention':summary['retention']}))
            return 0
        if args.command=='verify':
            from .evaluation.audit import verify_run
            if args.out and args.out.resolve().is_relative_to(args.run.resolve()):
                raise ContractError('검산 출력은 원 run 폴더 밖에 저장하세요.')
            manifest = codec.loads((args.run / 'manifest.json').read_bytes())
            if manifest.get('schema') == 'hcr-run-manifest-r02':
                from .evaluation.adaptive_audit import verify_run
            receipt=verify_run(args.run)
            if args.out:codec.save(args.out,receipt)
            print(codec.dumps(receipt));return 0
        if args.command=='infer':
            from .runtime import Engine
            from .circuits import Memory
            from .trace import Trace
            config = adaptive_config_from(args.config) if args.engine == 'r02' else config_from(args.config)
            obs=codec.observation_from(codec.loads(args.input.read_bytes()))
            if args.engine == 'r02':
                from .runtime import AdaptiveEngine as Engine
                from .circuits import AdaptiveMemory
                memory = AdaptiveMemory.load(args.memory, config) if args.memory else AdaptiveMemory.empty(config)
            else:
                memory=Memory.load(args.memory,config) if args.memory else Memory()
            args.out.mkdir(parents=True,exist_ok=False)
            trace=Trace(args.out/'events.jsonl')
            try:decision=Engine(config,memory,trace).infer(obs,Mode.FROZEN_EVAL)
            finally:trace.close()
            codec.save(args.out/'decision.json',decision)
            codec.save(args.out/'observation.json',obs)
            codec.save(args.out/'state.json',{'memory_hash':memory.digest,'mode':'frozen_eval','correctness_evaluated':False,
                       'event_count':trace.count,'event_head':trace.head})
            print(codec.dumps(decision));return 0
        return 2
    except (ContractError,OSError,ValueError) as error:
        print(f'{type(error).__name__}: {error}',file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
