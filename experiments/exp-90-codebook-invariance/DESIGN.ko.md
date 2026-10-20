# R44 / EXP-90: 고정 codebook의 의미 불변성

R43 HIGH 방향 판정의 B를 수행한다. 기존 R35/R36 namespace 변형은 실제 code 대응을 보존했다. 이번에는 의미·원천·AST·Config·순서·initial0.5를 유지하고 token→3bit bijection만 바꾼다. 학습된 codebook이 아니며 학습 효율·H03·일반 AI·속도 우위나 core 도입을 주장하지 않는다.

기존 encoder에 inverse vocabulary를 전달하므로 monkeypatch가 없다. 8개 map은 identity, bit_reverse, xor7, cnot01, cnot12, cnot20, cnot_chain, swap01다. 마지막은 비선형이며 CNOT는 일부 Hamming 거리를 바꾼다. 입력 dtype·injectivity·token domain을 사전 확인한다. core·모든 guard·settle/controller/history/Cost는 그대로다.

R36 canonical의 C/Tmask8×8과 AST(4,5)/(5,4)를 선택한128base에8maps=1024native를 실행한다. exact는 의미가 같아 identity의128조건에서 한 번씩 실행하며 독립 집합 oracle은 모든 native 기록에 적용한다. native는 후보2/leaf3의원래18settle이며 원천28+role64+상위18432=18524settle, 최대2963840tick이다. 학습/World.measure/localnative0, worker1/retry0이다. 이름·순서·다른initial·다른AST·새topology 일반화 표본은 아니다.

64role kernel은 가능한 모든 3bit ordered pair를 실제 실행한다. 같은 Program/Config/initial과 encoder index만 쓰는 역할 단계에서 모든40320bijection×64tokenpair의 대응을 savedoutput lookup으로 검사한다. 이 역할 단계의 finite-domain 전이 근거를 전체 파이프라인40320실행으로 표현하지 않는다. 시간/CPU 절약이나 학습으로도 세지 않는다. 모든 mapping의 전체 단계 수렴 성질을 증명하지 않는다.

896개 nonidentity→identity 대응의 kind/selected candidate identity/value/reason과 모든 native 역할/AST의 의미를 비교한다. code 값·수치 activation·ticks·hash는 변할 수 있어 mapping간 trace bytes 동일을 요구하지 않는다. 각 trace의 실제 Program/drives/초기상태·scalar/controller/count·proof·source/revision/slot·packet-onlyT 경계는 독립 재생한다. unresolved와 다른 abstain사유도 보존한다. 모두 맞을 때에만 이8maps/128base의 유한 불변성을 채택하며, 실패는 원자료와 함께 음성으로 닫는다. 조건·임계값·후보·반복·상한 사후 조정이나 native 재실행은 없다.

단계240초/전체600초,raw128MiB/cache128MiB/AS각512MiB/건당128KiB/고유6000/LRU18/childfile8MiB,parentfile130MiB는 중단선이며 완료/RSS 보장이 아니다. R36 실제44956호출의work/audit 관측을 참고해 더작은18524호출을 이 경계로 정했으며 미래 시간 예측으로 보장하지 않는다. 저장 cache는 kernel+Config의 정확 bytes를 확인하고 저장만 공유한다. 모든 physical 계산을 실행한다. 준비·work·audit·source·parent봉인·launcher CPU/wall을 기록하되 효율/통계적 속도 채택선은 없다. 총비용은서버실행범위이며 로컬개발/패키징/MCP전송/인력비용을포함하지않는다.

전체source/raw의직접size/SHA검사와saved-data 검산은작성자검증이다. same-channel manifest는hostattestation이아니며upstream완전성unknown/빈logs·ZIP미수신여부를구분한다.
