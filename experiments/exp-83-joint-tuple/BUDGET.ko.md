# R37 자원·비용 사전 상한

R36 raw 해시는 budget.json에 고정했다. 호출/평가/원천/고유trace 비율로 각 core·저장·공통·준비·감사·봉인 비용을 따로 스케일했다. 계획 work287.741449초, 전체308.723146초에 선택한 안전계수3과60초 올림을 적용해 단계900초·전체960초로 정했다. 이는 통계 보장이 아닌 운영 중단선이다.

실제 호출 상한16원천+119808numeric=119824,최대19171840tick이다. 각 native_joint는12×(|C|+|T|)+10회, native_marginal은그보다1회많다. exact상위native0이다. raw상한64MiB는 R36수신byte×max(기록,trace비율)×2를32MiB단위로올림한 값이다. metadata2MiB를남기며 child파일8MiB/parent66MiB,부모/자식주소공간각512MiB,작업자1/재시도0이다.

고유trace상한1272=field equality8+pairAND16+ordered relation OR128+projection32+classifier64+query1024다. namespace들의 필드별 수치 code는 동일하고, 공개 layout2개 및 완전 관계표·개입 arm의 구조적 경우 수로 계산했다. canonical fullkernel+Config는건당128KiB이내(총159MiB이내)로제한하고 정확bytes충돌검사한다. 나머지353MiB는Python/원천/분할batch용여유이며 실제RSS보장아니다. 저장데이터LRU18은이전의검증된유틸을재사용한고정readcache상한이다. 한평가의최대107native기록을동시에검산할수는있으나장기cache는18개다.

서버메모리점관측은별도JSON에보존한다. 이후가용량보장이아니다. 학습과세계측정은0회,수치계산생략없음이다. 비용배분·저장중복제거를계산가속이나통계적성능우위로주장하지않는다.
