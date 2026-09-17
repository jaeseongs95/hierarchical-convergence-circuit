"""소스 배포본의 표준 unittest 실행. 실제 네트워크 연결을 모두 거부한다."""
from pathlib import Path
from unittest.mock import patch
import unittest
import socket
import platform
import sys
import time


def run_tests(root:Path) -> dict:
    root=Path(root)
    if str(root/'src') not in sys.path:sys.path.insert(0,str(root/'src'))
    suite=unittest.defaultTestLoader.discover(str(root/'tests'),pattern='test_*.py')
    def denied(*args,**kwargs):raise AssertionError('자체시험의 실제 네트워크 요청 금지')
    start=time.perf_counter()
    with patch.object(socket.socket,'connect',denied),patch.object(socket.socket,'connect_ex',denied),patch.object(socket,'create_connection',denied):
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    return {'schema':'hcr-selftest-r031','suites':['r01-regression','r02-adaptive','r021-session','r03-methods','r031-prior-scope'],'tests_run':result.testsRun,
            'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
            'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
            'skip_details':[{'test':t.id(),'reason':reason} for t,reason in result.skipped],
            'failure_details':[{'test':t.id(),'traceback':tb} for t,tb in result.failures+result.errors],
            'seconds':time.perf_counter()-start,'python':sys.version,'platform':platform.platform(),
            'actual_network_calls':0,'actual_llm_calls':0,'hypothesis_proved':False}

if __name__=='__main__':
    import json
    r=run_tests(Path(__file__).resolve().parents[1]);print(json.dumps(r,ensure_ascii=False,indent=2))
    raise SystemExit(0 if r['failures']==r['errors']==0 else 2)
