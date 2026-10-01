# R080 / EXP-61 작은 양수의 첫 상태 경계

R079의 교환 OFF에서 0은 stable False 후 coverage를 확장했지만 .05/.2/.4는 첫 True였다. (0,.05)가 비어 있어 sign 경계와 작은 양수의 상태 경계를 구별할 수 없다.

고정 native runtime·R077 memory/3.json·config/world/public IDs/episode·배열[e2,e3,e0,e1]·OFF에서 e3={0,.005,.01,.02,.03,.04,.05}를 한 번씩 실행한다. 재현2와 새 입력5, 독립 발견·학습·feedback0이다. 7셀은 제안한 구간의 다섯 내부점을 한 턴에 비교하는 최소 고정 grid로 유지하며 ON/원래 배열을 곱하지 않는다. 예측은 유한 점의 비교이며 경계 부근 점을 사후 추가하지 않는다.

H1/H2는 같은 안정 상태 대안 비교 한 건이다. H1: 검사한 양수의 첫 stable 상태가 True/ready. H2: 새 내부점 중 stable False/ambiguous·ready False·같은 생성 advance의 progress가 존재한다. False의 reason은 negative_requires_dependency_coverage, ambiguous는 unresolved_or_no_goal_candidate다. graph_complete=True인 ambiguous/False는 ready=False 증인이 아니며 별도 상태로 보존한다. 관측된 증인은 다른 미평가 셀이 있어도 H1 반증/H2 지지지만, 증인이 없으면 전체 stable evaluability가 필요하다. H3는 새 내부점 중 첫 network가 budget_exhausted/oscillating인 별도 예측이다. measured nonstable은 H3 증거이며 H1/H2에는 미평가다. session budget와 network budget도 분리한다.

1차 metric은 가장 이른 r02_network(kind=decision)의 status와 생성 advance의 network-local progress.kind다. transition의 event_start <= index < event_end로 대응하고 network_id=None의 선행 progress와 pool은 제외한다. 확장 수만으로 False/ambiguous를 구별하지 않는다. 개별 neutral score0과 all-zero unsupported gate는 다르다. 이번 다른 세 score는 1/.6/1이라 unsupported gate가 적용되지 않는다.

모든 network·route·후속 progress·candidate/pending/readiness/completeness/frontier·Proof.paths inventory와 final parent closure·D_DAG·raw/readout/adoption을 보존한다. 첫 e3는 slot e:1이며 drive=4*score, 실제 goal dependency closure를 확인한다. group 전체 max residual로 종료하므로 경로가 연결되지 않은 일반 상황의 tick 불변성은 가정하지 않는다. natural digest/IDs/궤적은 강제 동기화하지 않는다.

실제 링크 항은 weight*(2*previous_activation-1), terminal 중심화 항과 terminal 비중심 activation product는 별도 이름으로 기록한다. OFF pool metric은 null/비해당이다. pending cost.wall_seconds는 duration이 아니며 active/finish/finished duration/capture는 각각 보존한다. capture는 finish와 겹칠 수 있어 합산하지 않는다. UTC 동일값은 허용하고 subprocess 순서와 perf_counter duration을 보존한다.

freeze→self-test(기존11 journal/합성 readout·nonstable 판정)→native7→raw 보존→독립 evaluator→변조거부→core 회귀1회→bundle 순서다. runtime/producer를 import하지 않는 기존 독립 수식 검산기를 재사용한다. max_ticks160·max_advances16·session ticks5120·허용오차2e-12를 유지한다. 과학적 budget/nonstable 결과는 남은 예정 셀을 계속 실행한다. 장치 integrity/runtime/measurement 오류는 즉시 중단하고 부분 evidence와 최초 traceback을 보존한다. 자동 retry·host correction·원자료 덮어쓰기0, Git 조작은 장치 밖에서 수행한다.

현재 결론은 source와 R079 관찰뿐이며 R080 native 실행 전이다. 이 finite-grid 예측의 실패는 HCC 전체 반증이 아니다. 정밀 임계값·전구간 단조성·sign 자체 충분성·gate 필요성·에너지 우위는 판정하지 않는다.
