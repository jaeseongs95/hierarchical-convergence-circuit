# R43 / EXP-89 결과: 중복 호출 감소 확인, 총비용 기준 미달로 미채택

HIGH 방향 토론을 거쳐 음수 sigmoid의 동일 `math.exp(z)` 결과를 한 번만 계산하는 후보를 AI Research SSH에서 한 번 실행했다. 전체 반환 기록과 kernel+Config의 정확 bytes, state key 순서, 원래 controller·논리 Cost를 보존했다. 총비용 채택 여부는 **False**다. 이 결과로 미세최적화 계열을 닫고, 다음 방향 검토에서는 동결한 codebook coverage에서 표현 변화의 의미 보존을 우선한다.

## 1. 방향 결정과 비중복성

[토론 기록](DELIBERATION.ko.md), [판정 구조](decision-record.json), [설계](DESIGN.ko.md), [실행 전 결과별 판단](OUTCOMES.ko.md)이 기준이다. 네 blind 관점·비원저자 교차검토·별도 fresh Judge는 A를 한 번 수행하고 종료하는 조건부 합의에 도달했다. R25의 고정점 생략, R30의 공간 공유, R31의 학습 macro 비교, R42의 관측 외피와 개입이 다르다. 이번은 runtime 구현 연구이며 H03 학습·압축·회로 재사용의 성공 근거로 세지 않는다. 다음 후보 B는 동일 coverage 안의 의미 불변성, C인 equivalent AST/top_down 비교는 구조·피드백 혼입 때문에 후순위다. 실제 내부 모델/effort 관측 제한을 포함해 토론 assurance는 `partially_independent`다.

## 2. 고정된 개입과 실행

원래 음수 분기의 `exp(z)/(1+exp(z))`를 `ez=exp(z); ez/(1+ez)`로 바꾼 연구 외피만 사용했다. 양수 분기, 나머지 부동소수 연산 순서, 입력 검증, link 순서·중복, 원래 settle/controller/history/trace/Cost는 유지했다. 공통 엔진 파일은 수정하지 않았다. 프로세스의 `dynamics.tick` 하나를 임시 연결하고 정상·예외·중첩 거부 후 finally 복원했다. 같은 유한 입력과 Python/libm의 결정적 builtin exp가 전제이며 실제 결과는 전체 bytes로 대조했다.

32맥락×3반복×5셀=480기록·1920질의·192native짝이다. joint와 factor 각각 baseline/exp_once, exact_joint baseline이 대조다. 각 호출은 fresh producer/initial0.5이며 학습·세계측정은0이다. 원천24+시간대조34560+계수/컨트롤134=34718settle을 수행했다. 실제 settle tick은 1,048,028회다. 직접 tick **36호출 중24회는 정상 연산,12회는 연산 전 오류 거부**이며 이들을 정상 산술 tick으로 합하지 않는다.

서버 Linux/Python3.12.3에서 준비·계수·work·audit 네 단계가 모두 exit0이었다. 전체 봉인 포함 110.825283초, 관측 process CPU 합계 110.823006초다. 단계240초/전체300초·worker1/retry0을 지켰다. 상한은 운영 중단선이며 일반적인 완료·CPU/RSS 보장이 아니다.

## 3. 정확성·실제 호출 감소

65개 기존 고유 kernel 입력×두 방식의 전체 bytes와2controller짝이 일치했다. 18개 직접 조건은 양수·0·음수0 입력·작은 양/음수·underflow·초기0/1·중복 link/top_down ON/OFF와6오류를 포함한다. 실제 exp counter는 baseline=G+Nnegative, candidate=G였다. 계수 settle의 exp는 26,093→16,136회다. 직접24정상연산의 별도 합계는 방식별 G14/Nnegative5이며12거부는 exp0이다.

시간대조에서는 counter를 제거하고 builtin exp를 직접 사용했다. 모든 시간대조 고유 kernel 내용이 계수검사의65입력에 포함됨을 확인했다. 이 직접계수 coverage에서 유도한 native 표현별3반복 합계는 4,378,776→2,812,608회, **35.7673% 호출 감소**다. 시간대조 중 counter로 직접 센 수치나 CPU 감소율로 표현하지 않는다.

192짝의 전체 반환 기록에서 선언한 mode·참조이름·두 CPU필드만 제외했고, 참조를 확장한 모든 kernel+Config bytes도 정확히 같았다. 모든 중간 계층·질의·전체집합 oracle·source proof·리비전·seal·controller·논리 Cost·반복/이름/순서 불변성을 검산했다. scalar 독립 재생 최대오차 1.734723475976807e-18 / 허용1e-14였으며 이 허용오차를 짝 bytes 비교에 적용하지 않았다. semantic/계수/복원/원장/짝 교란17개를 거부했다. 로컬 추가 native 추론은0이다. 검산·CS 평가는 구현자의 saved-data 재생이며 독립 감사로 부르지 않는다.

## 4. 준비·저장·검증을 포함한 총비용

네 native셀은 독립 seen/cache 수명과 참조 영역을 사용했다. 동일 bytes의 저장만 줄이고 모든 계산을 실행했다. 각 저장기65고유 trace, 전체260trace이며 cache192MiB/raw128MiB는 네 저장기 합계 상한이다. 먼저 기록한 방식이 다른 방식의 저장 비용을 대신 내지 않는다.

각 기록의 core(설치·export/guard·검증·계산·trace·digest 포함), 저장, audit CPU/wall을 관측했다. 준비·계수·source·work/audit 잔여·parent seal·launcher CPU를 포함한 공통 CPU 44.637388초를15arm-rep그룹에 동일 배분했다. 전체 completion wall에서 개별 측정시간을 뺀 공통 wall 44.632734초도15등분했다. bootstrap wall은 completion에 이미 포함돼 다시 더하지 않았다. 이는 한 유한 실행 비용의 배분이며 그룹별 독립 OS process 비용으로 확대하지 않는다.

이 총비용은 동결한 서버 실행 범위다. 로컬 개발·검사·ZIP 생성과 MCP 전송·수신 시간, 연구 인력 비용은 포함하지 않는다. 따라서 연구 업무 전체나 학습 포함 시스템 전체의 비용 절감을 주장하지 않는다.

실행 전 기준은 두 native표현 각각 **3반복 모두** candidate/baseline 총CPU<=0.95, 총wall<=1.05다. 집계 평균·좋은 반복 선택·사후 상각 변경을 허용하지 않았다.

| 표현 | 반복 | 총CPU 비율 | 총wall 비율 | 기준 |
|---|---:|---:|---:|---|
| native_factor | 1 | 0.997523 | 0.997518 | FAIL |
| native_factor | 2 | 1.000033 | 1.000028 | FAIL |
| native_factor | 3 | 0.997988 | 0.997992 | FAIL |
| native_joint | 1 | 0.999675 | 0.999749 | FAIL |
| native_joint | 2 | 1.000368 | 1.000372 | FAIL |
| native_joint | 3 | 0.992493 | 0.992487 | FAIL |

판정: **중복 호출 감소 확인, 총비용 기준 미달로 미채택**. 정확성/실행 검증 PASS와 비용 채택 판정은 구분한다.5% 기준은 기술 판별선이며 통계 유의성이나 제품 성능 약속이 아니다. 새 반복·retune·상한 증가·core 도입을 하지 않았다.

## 5. 근거·한계·다음 방향

[전체 분석](../../evidence/exp-once-20261020-r43/analysis.json), [로컬 검산](../../evidence/exp-once-20261020-r43/local-verification.json), [수신 검산](../../evidence/exp-once-20261020-r43/receipt-verification.json), [서버 manifest](../../evidence/exp-once-20261020-r43/raw/manifest.json), [완료](../../evidence/exp-once-20261020-r43/server-completion.json), [CS 검토](../../evidence/exp-once-20261020-r43/cs/review.json)를 보존한다. 299개 manifest JSON과 manifest 자체를 수신했으며 각 원본 파일의 크기·SHA를 직접 확인했다. source242파일·input204핀도 그대로다. 빈 stdout/stderr8개와 evidence ZIP 자체는 수신하지 않았다. manifest는 자기 해시 밖에 있으며 동일 채널 해시는 host attestation이 아니다. SSH upstream completeness는 unknown으로 남긴다. 초기 완료조회는 실행 중 파일 미생성으로 실패했고 재실행 없이 후속 완료 자료를 조회했다.

32폐쇄 관계표 맥락·3반복은 독립 일반화 표본이 아니다. 학습비0인 runtime 연구이므로 학습 포함 효율·일반CSP·AI 능력·운영성능을 입증하지 않는다. 이번 구현은 연구 폴더에 보존하고 core에 자동 반영하지 않는다. 미세최적화 연속 실험을 종료한다. 다음 연구는 기존 R31과 중복되지 않게 codebook coverage를 먼저 고정한 뒤, 허용한 표현 변형에서 learned structure의 의미 불변성을 확인하는 계약을 검토한다. 원래 계산을 대체하는 과제의 비용 비교에는 학습·생성·검증·binding·실행 비용을 모두 포함해야 한다. 이번 요청에서 R44를 자동 실행하지 않는다.
