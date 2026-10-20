# R36 상한의 근거와 한계

정확한 입력 수·산식·원자료 경로/SHA는 budget.json에 저장한다. R35 raw는 같은 AI Research SSH에서24source+19008numeric/864inputs/518unique traces를 실행한 관측이다. work CPU51.261065초,봉인 포함54.172070804초였다. 이 관측을 다른 workload의 보장 시간으로 전용하지 않는다.

R36은2304완전 교차+192의미 변형=2496inputs이며 native/exact4992평가다. 후보2개이므로 numeric18×2496=44928호출,새 source28까지44956호출이다. max_ticks160을 그대로 사용하므로 논리적 절대 상한은7192960tick이다. 이 값은 추정 호출 수가 아니라 동결된 실행 루프의 개수다.

고유 trace 상한2692는 역할4(두 기호의x/y조합),AST96(2candidate code×8패턴×6식),classifier96(8패턴×6식×2순서),query2496(평가당1개)을 합한 보수적 수다. namespace 문자열은 numeric kernel의 인자가 아니고 공개 vocabulary의 동일 code로 전달되므로 이 상한을 추가 증폭하지 않는다. 실제 기록 수와 cache bytes는 결과에서 확인한다.

CPU 추정은 R35에서 native core를 호출 비율로,exact core와공통 overhead를입력 비율로,source를28/24로,저장을고유기록상한/518로 각각 스케일한다. 준비·감사·봉인도 관련 입력/고유기록 비율로 스케일한다. 그 결과 work약158.146초/전체약171.727초의 계획값이다. **안전계수3과60초 단위 올림은 이번 운영 정책으로 선택한 값**이며 측정된 신뢰구간이 아니다. 전체540초/단계480초가 실행 중단선이다. 예상보다 오래 걸려도 자동으로 늘리지 않는다.

raw96MiB는 R35 수신JSON9010188bytes에max(입력비율,고유기록비율)와 선택한 여유계수2를 적용하고32MiB 단위로 올린 중단선이다. work payload는 metadata를 위해2MiB를 남긴다. metrics를128평가씩 분리해 전송 채널의 큰 단일 출력 함정을 피한다. child 파일8MiB는 이 고정 chunk 형식의 예상 최대 JSON보다 큰 운영 중단선이며, parent ZIP98MiB는raw96MiB+4096개 미만/이름128bytes 이하 ZIP header를 위한2MiB 여유다.

runtime canonical 보관은2692×128KiB 이하(336.5MiB)에서 중단한다. child AS512MiB는 이 payload 외 Python/Program/source/batch의 여유를 둔 운영 한도이며 실제 RSS 예측이나 OS 예약 보장이 아니다. 기존 full Python trace 객체 보관 대신 canonical bytes로 동일성을 검사하고, 검산은 LRU18(한 numeric 평가의 native reference 수)로 full trace 보관을 제한한다. parent AS512MiB와 child AS512MiB의 합1GiB는 실행 전 읽은 MemAvailable3103196kB보다 작았다. 이 값은 한 시점 관측이며 실행 중 자원 보장이나 증설 근거가 아니다. phase별ru_maxrss 원시 값을 기록하고 단위를 임의 환산하지 않는다.

worker1은 동시 작업이 누적돼 이 자원 경계를 넘지 않게 하는 운영 선택이다. retry0은 실패를 숨기거나 같은 실행을 반복하지 않게 하는 연구 규칙이다. 학습·World.measure0은 이 과제가 기존 생성기의 의미 보존 검사이기 때문이다. 새 유료자원·서비스·의존성·권한 확대는 없다. 모든 상한과 선택 근거는 source/code와 함께 실행 전에 봉인한다.
