"""Reports preserve all conditions and failed predictions; no mechanism fitted to outcomes."""
import csv
import io
import json
from . import io as storage


def csv_bytes(rows):
    if not rows:return b''
    columns=list(dict.fromkeys(k for row in rows for k in row));f=io.StringIO(newline='')
    w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader()
    for row in rows:
        w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    return f.getvalue().encode('utf-8')


def render(s):
    lines=['# EXP-29 / R048 — 관측 강도와 초기 상태의 수치 정밀도','',
        '## 결론','',f"모집단: `{s['population']}`. A 14개 공유, B 98조건. 독립 무작위 반복은 없습니다.",
        '실제 A 상태와 fixed 0.99의 비교는 아래 전체 조건에 대해 그대로 보고합니다. 잘못된 결과나 미적용을 효율 개선으로 세지 않습니다.',
        '', '## A source의 가용성','', '| 관측 강도 | ID | raw | 채택 | 정답 채택 | ticks | 재사용 가능 |', '|---|---|---|---|---|---:|---|']
    for r in s['sources']:
        lines.append(f"| {r['strength']} | {r['variant']} | {r['raw_value']} | {r['accepted']} | {r['accepted_correct']} | {r['native_ticks']} | {r['positive_reuse_available']} |")
    lines+=['','## 관찰: 실제 상태 대 고정값','', '| 강도 | ID | mask | actual | fixed | 차이 | 비교 가능 | 제외가 아닌 미판정 사유 |', '|---|---|---|---:|---:|---:|---|---|']
    for p in s['pairs']:
        lines.append(f"| {p['strength']} | {p['variant']} | {p['mask']} | {p['actual_ticks']} | {p['fixed_ticks']} | {p['actual_minus_fixed_ticks']} | {p['eligible']} | {', '.join(p['eligibility_failures'])} |")
    lines+=['','## 사전 가설 전체 판정','', '| 조건 | 처리 | 가설 | 판정 |', '|---|---|---|---|']
    for h in s['hypotheses']:
        lines.append(f"| {h.get('case',h.get('strength'))} | {h.get('mask',h.get('arm'))} | {h['hypothesis']} | {h['status']} |")
    lines+=['','## 해석과 대안 설명','',
        '음수 Δticks는 actual이 더 적은 native ticks를 썼다는 뜻입니다. 실제 A와 B가 올바르게 채택되고 gate가 적용된 경우에만 효율 비교를 해석합니다.',
        'A가 양성 채택에 실패한 조건도 B 7군을 모두 실행했습니다. gate 거부 후 같아진 cold 궤적을 초기값 정밀도의 동등성 증거로 사용하지 않습니다.',
        '0.92 조건은 이미 알려진 EXP-28 대조점입니다. 이전 6개 H_source_specificity 실패를 소급 수정하거나 새 독립 증거로 세지 않습니다.',
        '서로 다른 궤적이 같은 ticks로 종료할 수 있습니다. checkpoints.csv는 실제 양쪽에 존재하는 시점만 비교하고, 조기 종료 후의 상태를 복제하거나 계산을 연장하지 않습니다.',
        '관측 강도 변화가 만드는 동역학의 차이는 관찰 대상입니다. 임계 구간, attractor, 의미적 메커니즘에 관한 원인은 추가 판별 없이 확정하지 않습니다.',
        '', '## 비용과 주장 범위','',
        '동일 block 안에서는 A/B의 공유 근거 score와 binding을 유지합니다. 추가 B edge는 0.92로 고정합니다. 모든 world edge는 별도로 True로 고정하고 runtime에 전달하지 않았습니다.',
        'native ticks, group updates, signals, dependency/descriptor 검사, bytes, wall time을 분리합니다. native/bridge proof 수는 같은 생성 작업의 별칭이므로 더하지 않습니다.',
        '모든 처리에서 전체 A packet을 사용하는 기존 구현입니다. partial-mask 저장량 최적화, 전송 최소화, source 계산 생략을 시험하지 않았습니다.',
        'wall time에는 기록·fsync 비용이 포함됩니다. 에너지와 peak memory는 null이며 실행시간·전력 절감을 주장하지 않습니다.',
        '고정 잠재 연결 공간, 가소성, 학습된 Circuit 경쟁, 자연어 문맥 이해, 전체 HCC lifecycle은 이번 실험 대상이 아닙니다.',
        '', '## 다음 판별 실험','',
        '이번에 동결한 전 범위의 Δticks와 정확도·채택·가용성을 함께 본 뒤 다음 질문을 정합니다. 유리한 강도만 남기거나 fixed 값을 사후 조정하지 않습니다.','']
    return '\n'.join(lines).encode('utf-8')


def contents(summary,audit,source_audits,record_audits):
    objects={'summary.json':summary,'audit.json':audit,'source_audits.json':source_audits,'record_audits.json':record_audits,
             'claims.json':summary['scope']}
    out={n:storage.encode(x)+b'\n' for n,x in objects.items()}
    out['summary.ko.md']=render(summary)
    for key in ('sources','trials','pairs','checkpoints','vs_cold','ID_controls','hypotheses','transfer_maps','dependency_scans','signatures'):
        out[key+'.csv']=csv_bytes(summary[key])
    return out
