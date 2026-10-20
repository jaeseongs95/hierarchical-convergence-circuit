# R39 비용 계획과 운영 중단선

R38 source해시와스케일을budget.json에고정했다. L=|R|+|S|+|U|. membership=12L+12,8tripleAND뒤producer는joint12L+20/compact12L+26이다. 5질의는joint7/compact13수렴이므로두native arm합은24L+66.32context총6336numeric+24source=6360,최대1017600ticks다.32context×5질의=160context-query쌍,3arm포함480출력이며독립통계표본480개가아니다.

R38의nativecore/storage를호출비6336/120384,exact를질의비160/608,공통overhead를record비96/1824,source를1배로계획했다. 이전다른단계잔여시간은줄이지않았다. 계획work10.844603초/전체44.805885초에선택안전계수3·60초올림및단계최소120초정책을적용해단계120초/전체180초로정했다. 새composition/정확성/완료·통계적속도보장이아닌운영중단선이다.

R38과같은raw128MiB(메타2MiB reserve)/canonicalcache192MiB/record128KiB/AS부모·자식각512MiB/파일130·8MiB/LRU18상한을재사용한다. 고유trace수는실제numeric호출6336보다클수없지만그수만큼메모리확보를보장하지않으며별도cache바이트상한이먼저중단할수있다. worker1/retry0/학습0/세계측정0이다. 부모와자식은동시에여러연구worker를돌리지않는다.

source/Program생성·검증/수치계산/저장/공통프로세스/감사/봉인비용을분리기록한다. 원천1회씩각arm및공통1/3배분은회계가정이며독립성능측정이아니다. 모든numeric계산은실행하고동일fullkernel+Config의저장만공유한다. rawRSS는플랫폼원값으로기록하고단위변환·이후가용메모리보장을주장하지않는다.
