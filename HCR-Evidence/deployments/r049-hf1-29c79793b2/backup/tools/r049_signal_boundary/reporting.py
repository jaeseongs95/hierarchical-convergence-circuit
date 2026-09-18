"""Complete reports: simultaneous failure flags and every hypothesis, including failures."""
import csv
import io as textio
import json
from collections import Counter
from tools.r048_precision import io


def csv_bytes(rows):
    if not rows:return b''
    fields=list(dict.fromkeys(k for r in rows for k in r));f=textio.StringIO(newline='')
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
    for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in r.items()})
    return f.getvalue().encode('utf-8')


def render(s):
    lines=['# EXP-30 / R049 — 역방향 신호 × 초기조건', '', '## 결론', '',
        f"모집단: `{s['population']}`. 48개 조건 중 기존 탐색 대조 {s['regression_cells']}개, 새 조건 {s['new_condition_cells']}개입니다.",
        'ID 변형과 재실행은 독립 무작위 반복으로 세지 않습니다. 가설 지지와 장치 검증 통과는 별개입니다.',
        '0.99 초기화는 모든 world에 같은 방식으로 주어진 실험 조건이며 실제 A 재사용·학습이 아닙니다.', '',
        '## 관찰', '', '| 강도 | 관계 | ID | 처리 | ticks | raw | 채택 | 분류 | D_DAG |', '|---:|---|---|---|---:|---|---|---|---:|']
    for r in s['trials']:lines.append(f"| {r['strength']} | {r['pattern']} | {r['variant']} | {r['arm']} | {r['native_ticks']} | {r['raw_value']} | {r['accepted']} | {r['classification']} | {r['D_DAG']} |")
    lines+=['','## 실패 경계 — 동시에 여러 항목이 참일 수 있음','','| 조건 | raw 오판 | edge/관측 충돌 | proof 구성 실패 | proof 지지 충돌 | 채택 거부 | 예산 종료 |','|---|---|---|---|---|---|---|']
    for r in s['boundaries']:
        lines.append('| '+r['trial']+' | '+' | '.join(str(r[k]) for k in ('raw_value_incorrect','edge_activation_observation_sign_conflict',
            'proof_construction_failed','proof_assumption_support_conflict','adoption_rejected','budget_terminated'))+' |')
    lines+=['','## 사전 가설 전체 판정','','| 강도/관계 | ID | 처리 | 가설 | 상태 |','|---|---|---|---|---|']
    for h in s['hypotheses']:lines.append(f"| {h['strength']}/{h['pattern']} | {h['variant']} | {h['arm']} | {h['hypothesis']} | {h['status']} |")
    lines+=['','## 해석·대안 설명', '',
        'top-down OFF에서 메시지 수가 줄어드는 것은 실행 함수가 바뀐 직접 효과입니다. 같은 계산을 더 효율적으로 했다는 주장으로 합치지 않습니다.',
        '중립 activation 0.5라도 AND형 prefix bias는 음수입니다. edge 부호 유지, goal 방향, proof 구성, 근거 지지, 채택을 각각 판단해야 합니다.',
        '수렴은 정답이 아니며 채택 거부는 정답 수정이 아닙니다. 높은 초기값에서 양성 답이 나와도 음성 대조와 함께 해석합니다.',
        'signal_ledger.csv는 모든 tick/group의 읽기 전용 분해입니다. masked_top_down_term은 실제 전송이 아니라 같은 기록 상태에서 계산한 비활성 연결 항입니다.',
        'target_implied_by_native_update는 원자료 전후 값에서 역산한 목표값입니다. 별도 tanh 감사가 수치 정합성을 확인하며, ledger 생성은 실행기에 되먹임하지 않습니다.',
        'self_competition_logit에는 자가흥분과 억제의 합이 들어갑니다. 현재 두 계수를 독립 기제로 분리했다고 주장하지 않습니다.', '',
        '## 기존 탐색과 회귀', '',f"기존 탐색 비교 결과: {dict(Counter(x['dynamics_equal'] for x in s['prior_regressions']))}",
        'prior_regressions.csv에서 기존 방정식 탐색과 이번 native 실행의 궤적 서명을 비교합니다. 기존 탐색값을 신규 독립 증거로 세지 않습니다.', '',
        '## 다음 판별 질문과 현재 주장 범위', '',
        '어떤 항이 edge·goal·proof 경계를 갈라놓는지 이 대조에서 확인하고, 이후 기존 재검토/session 구조와 연결합니다.',
        'bias나 초기값을 결과에 맞춰 조정하지 않습니다. 이 단계는 자동 구조 수정, 학습, Graph 재확장, 고정 잠재 공간의 구현이 아닙니다.',
        'D_DAG·ticks·검사 수·messages·wall time은 별개입니다. wall time에는 raw 기록 비용이 포함되며 전력·peak memory는 null입니다.','']
    return '\n'.join(lines).encode('utf-8')


def contents(s,audits,stream,raw_hash):
    compact={k:v for k,v in s.items() if k!='signals'}
    a=dict(schema='hcr-exp30-audit-v1',verified=True,population=s['population'],queries=s['queries'],
        scalar_ticks=s['unique_native_ticks'],stream_records=stream,tolerance=2e-12,
        all_numeric_proof_and_event_checks_passed=True,raw_manifest_sha256=raw_hash,
        effective_link_mask_verified=True,hypothesis_support_required=False,full_AdaptiveSession_replayed=False)
    out={n:io.encode(v)+b'\n' for n,v in {'summary.json':compact,'audit.json':a,'record_audits.json':audits,'claims.json':s['claims']}.items()}
    out['summary.ko.md']=render(s)
    for k in ('trials','boundaries','pairs','interactions','ID_controls','hypotheses','prior_regressions','signatures'):
        out[k+'.csv']=csv_bytes(s[k])
    out['signal_ledger.csv']=csv_bytes(s['signals'])
    return out
