# R076 이후: 같은 길이의 두 binding 후보와 prior 없는 native 비교

R076은 길이2/3 pattern을 native feedback으로 형성하고 두 goal-binding 후보를 pool에 넣었다. 하지만 세 번째 prefix 후보가 섞였고, score 변화는 긴 완결과 prefix의 최초 선택을 바꿨다. 짧은 완결 경로는 최초 선택되지 않았다. uncertainty prior·mismatch·구조가 함께 바뀌었으므로 evidence-only 경쟁이나 두 완결 경로 전환은 아직 검증되지 않았다.

다음 질문은 **길이가 같은 두 완결 binding 후보에서, uncertainty prior가 0인 native 계약의 공개 score 변화가 실제 경로 선택을 바꾸는가**다. 아직 동결·구현·실행하지 않았다.

1. 현재 config를 기반으로 prior_gain=0을 처음부터 정하고, 그 config에 맞춘 길이2 native formation recipe를 새로 동결한다. 기존 memory의 signature·strength·ID를 수정해서 config를 맞추지 않는다.
2. S→A→G와 S→B→G처럼 같은 길이의 완결 경로만 최초 pool에 들어갈 최소 world를 확인한다. 길이2 저장 pattern 하나의 서로 다른 binding 두 개이며 저장 회로 두 개로 세지 않는다. 추가 후보·budget·binding 실패가 나타나면 그대로 기록한다.
3. world·memory·config·identity·edge 배열·budget을 고정하고 한 경로의 공개 score만 조작한다. 음수로 mismatch gate가 바뀌는 조건은 별도로 분류하며, score grid·tie 기준·예측을 실행 전에 정한다. ON/OFF 대조를 쓰더라도 inhibition 효과의 독립 인과 검증이라고 부르지 않는다.
4. 최초 pool의 두 후보와 선택, 이후 expansion·proof/readout·terminal adoption, D_DAG·정수 비용을 분리한다. 경로 전환이 없거나 양성 score가 모두 포화되면 해당 음성 결과를 보존하며 성공을 위해 정책·메커니즘을 추가하지 않는다.

R076과 다른 config·world·formation을 쓰는 새 연구이며 동일 원자료의 재분석이나 독립 반복 표본으로 포장하지 않는다. 동일 결과라도 proof·계산 궤적과 비용이 다른지 먼저 판정한다.
