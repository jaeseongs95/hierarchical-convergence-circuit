# EXP-12 / R0.3.1 — 회로 선택용 prior와 판단용 prior의 분리

실행·수치 재연산의 검증과 과학적 가설 판정을 구분한다. 학습/pool 정책은 그대로다.
task inference와 고정 network 재실행을 합쳐 정답률로 세지 않는다. 0점과 결측은 별도 조건이다.

| 학습 | 사례 | 조건 | 출력 | 외부 평가(world: correct) | 상태 | 확장 | pool tick | 판단 tick |
|---:|---|---|---|---|---|---:|---:|---:|
| 3 | sweep_strong_negative | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 3 | sweep_strong_negative | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 3 | sweep_strong_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 3 | sweep_weak_negative | route_only | False | {'declared': True} | stable_decision | 1 | 41 | 39 |
| 3 | sweep_weak_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 39 |
| 3 | sweep_weak_negative | legacy | True | {'declared': False} | stable_decision | 1 | 41 | 51 |
| 3 | sweep_zero | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 3 | sweep_zero | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 34 | 38 |
| 3 | sweep_zero | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 34 | 61 |
| 3 | sweep_weak_positive | legacy | True | {'declared': True} | stable_decision | 1 | 32 | 33 |
| 3 | sweep_weak_positive | route_only | True | {'declared': True} | stable_decision | 1 | 32 | 43 |
| 3 | sweep_weak_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 43 |
| 3 | sweep_strong_positive | route_only | True | {'declared': True} | stable_decision | 2 | 35 | 36 |
| 3 | sweep_strong_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 3 | sweep_strong_positive | legacy | True | {'declared': True} | stable_decision | 2 | 35 | 35 |
| 3 | sweep_missing | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 3 | sweep_missing | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 34 | 38 |
| 3 | sweep_missing | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 34 | 61 |
| 3 | familiar | legacy | True | {'declared': True} | stable_decision | 2 | 35 | 35 |
| 3 | familiar | route_only | True | {'declared': True} | stable_decision | 2 | 35 | 36 |
| 3 | familiar | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 3 | counterfactual | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 3 | counterfactual | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 3 | counterfactual | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 3 | longer | graph_only | True | {'declared': True} | stable_decision | 4 | 0 | 38 |
| 3 | longer | legacy | True | {'declared': True} | stable_decision | 2 | 70 | 38 |
| 3 | longer | route_only | True | {'declared': True} | stable_decision | 2 | 70 | 38 |
| 3 | diamond | legacy | True | {'declared': True} | stable_decision | 1 | 33 | 32 |
| 3 | diamond | route_only | True | {'declared': True} | stable_decision | 1 | 33 | 33 |
| 3 | diamond | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 60 |
| 3 | renamed_reordered | route_only | True | {'declared': True} | stable_decision | 2 | 35 | 36 |
| 3 | renamed_reordered | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 3 | renamed_reordered | legacy | True | {'declared': True} | stable_decision | 2 | 35 | 35 |
| 3 | all_missing | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 3 | all_missing | legacy | False | {'first_open': False, 'first_closed': True} | stable_decision | 2 | 65 | 79 |
| 3 | all_missing | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 65 | 59 |
| 3 | all_zero | legacy | False | {'first_open': False, 'first_closed': True} | stable_decision | 2 | 65 | 79 |
| 3 | all_zero | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 65 | 59 |
| 3 | all_zero | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 6 | sweep_strong_negative | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 6 | sweep_strong_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 6 | sweep_strong_negative | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 29 |
| 6 | sweep_weak_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 39 |
| 6 | sweep_weak_negative | legacy | True | {'declared': False} | stable_decision | 1 | 36 | 39 |
| 6 | sweep_weak_negative | route_only | False | {'declared': True} | stable_decision | 1 | 36 | 39 |
| 6 | sweep_zero | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 32 | 34 |
| 6 | sweep_zero | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 32 | 61 |
| 6 | sweep_zero | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 6 | sweep_weak_positive | route_only | True | {'declared': True} | stable_decision | 2 | 30 | 43 |
| 6 | sweep_weak_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 43 |
| 6 | sweep_weak_positive | legacy | True | {'declared': True} | stable_decision | 2 | 30 | 32 |
| 6 | sweep_strong_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 6 | sweep_strong_positive | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 6 | sweep_strong_positive | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 6 | sweep_missing | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 32 | 34 |
| 6 | sweep_missing | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 32 | 61 |
| 6 | sweep_missing | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 6 | familiar | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 6 | familiar | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 6 | familiar | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 6 | counterfactual | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 6 | counterfactual | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 29 |
| 6 | counterfactual | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 6 | longer | legacy | True | {'declared': True} | stable_decision | 2 | 68 | 37 |
| 6 | longer | route_only | True | {'declared': True} | stable_decision | 2 | 68 | 38 |
| 6 | longer | graph_only | True | {'declared': True} | stable_decision | 4 | 0 | 38 |
| 6 | diamond | route_only | True | {'declared': True} | stable_decision | 1 | 32 | 33 |
| 6 | diamond | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 60 |
| 6 | diamond | legacy | True | {'declared': True} | stable_decision | 1 | 32 | 32 |
| 6 | renamed_reordered | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 6 | renamed_reordered | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 6 | renamed_reordered | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 6 | all_missing | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 2 | 41 | 138 |
| 6 | all_missing | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 41 | 59 |
| 6 | all_missing | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 6 | all_zero | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 41 | 59 |
| 6 | all_zero | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 6 | all_zero | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 2 | 41 | 138 |
| 9 | sweep_strong_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 9 | sweep_strong_negative | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 29 |
| 9 | sweep_strong_negative | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 9 | sweep_weak_negative | legacy | True | {'declared': False} | stable_decision | 1 | 35 | 37 |
| 9 | sweep_weak_negative | route_only | False | {'declared': True} | stable_decision | 1 | 35 | 39 |
| 9 | sweep_weak_negative | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 39 |
| 9 | sweep_zero | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 32 | 61 |
| 9 | sweep_zero | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 9 | sweep_zero | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 32 | 34 |
| 9 | sweep_weak_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 43 |
| 9 | sweep_weak_positive | legacy | True | {'declared': True} | stable_decision | 2 | 30 | 31 |
| 9 | sweep_weak_positive | route_only | True | {'declared': True} | stable_decision | 2 | 30 | 43 |
| 9 | sweep_strong_positive | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 9 | sweep_strong_positive | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 9 | sweep_strong_positive | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 9 | sweep_missing | route_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 1 | 32 | 61 |
| 9 | sweep_missing | graph_only | False | {'first_open': False, 'first_closed': True} | stable_decision | 3 | 0 | 61 |
| 9 | sweep_missing | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 1 | 32 | 34 |
| 9 | familiar | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 9 | familiar | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 9 | familiar | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 9 | counterfactual | legacy | False | {'declared': True} | stable_decision | 2 | 67 | 29 |
| 9 | counterfactual | route_only | False | {'declared': True} | stable_decision | 2 | 67 | 28 |
| 9 | counterfactual | graph_only | False | {'declared': True} | stable_decision | 3 | 0 | 28 |
| 9 | longer | route_only | True | {'declared': True} | stable_decision | 2 | 68 | 38 |
| 9 | longer | graph_only | True | {'declared': True} | stable_decision | 4 | 0 | 38 |
| 9 | longer | legacy | True | {'declared': True} | stable_decision | 2 | 68 | 37 |
| 9 | diamond | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 60 |
| 9 | diamond | legacy | True | {'declared': True} | stable_decision | 1 | 31 | 32 |
| 9 | diamond | route_only | True | {'declared': True} | stable_decision | 1 | 31 | 33 |
| 9 | renamed_reordered | legacy | True | {'declared': True} | stable_decision | 2 | 34 | 35 |
| 9 | renamed_reordered | route_only | True | {'declared': True} | stable_decision | 2 | 34 | 36 |
| 9 | renamed_reordered | graph_only | True | {'declared': True} | stable_decision | 3 | 0 | 36 |
| 9 | all_missing | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 38 | 59 |
| 9 | all_missing | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 9 | all_missing | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 2 | 38 | 92 |
| 9 | all_zero | graph_only | None | {'first_open': None, 'first_closed': None} | unsupported | 3 | 0 | 59 |
| 9 | all_zero | legacy | True | {'first_open': True, 'first_closed': False} | stable_decision | 2 | 38 | 92 |
| 9 | all_zero | route_only | None | {'first_open': None, 'first_closed': None} | unsupported | 2 | 38 | 59 |

## 해석 경계

route_only는 pool prior·매칭·첫 macro 선택을 유지하고 최종 relation/goal learned drive만 0으로 만든다. 이후 경로 변경은 별도로 보고한다.
all_missing/all_zero에서 적용되지 않은 prior를 판단 근거로 세지 않는다. fixed_network 결과에는 이 readout support guard를 적용하지 않고 신호 동역학만 비교한다.
funnel의 구조적 universe는 평가기 전용이다. 미매칭/예산 미실행/경쟁 탈락을 원인 확정이나 candidate suppression의 증명으로 바꾸지 않는다.
같은 입력에 숨은 참값 두 개를 평가하는 경우 하나의 추론에 대한 두 채점이다. 추가 정보 없이 둘을 구분했다고 주장하지 않는다.
prior 정책은 session packet과 이벤트에 결속된다. 과거 source hash를 현재 소스에 맞게 고쳐 복원하지 않는다.
강도·검증 횟수·balance는 함께 기록한다. rigidity, 공유 dependency, consolidation, 부정 예외 학습, pool 최적화는 아직 구현하지 않았다.
