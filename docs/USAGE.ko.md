# 로컬 사용과 개발

모델 서버 없이 Python 3.12+로 실행한다. `hcr.py`는 이 프로젝트의 src를 import하므로 패키지 설치가 필요 없다. 파워셸 진입점도 같은 Python 명령만 호출한다. 기존 프로젝트의 파일을 자동 수정하거나 Git 명령을 실행하지 않는다.

## 명령

- `check --out <새 receipt.json>`: 네트워크 금지 자체시험, 선택적 JSON 영수증.
- `demo --out <새 폴더> [--config <toml>]`: 6 train, 8개 fixture×4조건 frozen, 두 adaptive 조건과 재방문. 개발용 실험이다.
- `verify --run <demo 폴더> [--out <폴더 밖 새 파일>]`: hash/event/tick/reference/summary 재검산. source hash가 다르면 거부한다.
- `infer --input <공개 observation JSON> --out <새 폴더> [--memory <memory JSON>] [--config <toml>]`: feedback 없는 단일 동결 추론. 정답 판정은 하지 않는다.

공개 observation JSON에는 episode_id, revision, start, goal, edges만 있다. 각 edge는 id, source, target, score로 구성된다. score는 [-1,1] 또는 null이다. truth/label은 받지 않는다. engine config가 다른 memory는 호환되는 회로로 몰래 불러오지 않는다.

## API의 책임

```python
from hcr.runtime import Engine
from hcr.model import Mode, Feedback
from hcr.tasks.toy_world import chain
from hcr.evaluation.reference import assess

engine = Engine()
world = chain('new-episode')           # 환경·외부 실행기
first = engine.infer(world.observation, Mode.TRAIN)  # 공개 관측만 전달
external = assess(first, world.observation, dict(world.hidden))  # 판단 이후
engine.feedback(Feedback(
    'feedback-001', first.id, first.observation_digest,
    external.correct,
    external.proof_valid and external.assumption_correct is True,
))
```

위 import는 사용자/실험기에서 한다. runtime는 tasks/evaluation을 import하지 않는다. 임의 feedback 공급자의 진실성까지 암호적으로 인증하는 구조는 아니다. 공정한 연구에서는 trusted reference와 공개 시점을 따로 감사해야 한다.

## 실행 결과

plan은 설정·source hash·개발 case 배정을 기록한다. events는 실제 group 상태와 판단→feedback 순서, memory version을 기록한다. episodes에는 평가기가 공개 관측/외부 truth/첫·수정 판단/외부 판정을 묶는다. 숨은 truth가 episodes에 저장된다고 inference 함수의 입력이 되는 것은 아니다.

memory_after_training.json은 실제 학습 산출물이다. memory_after_adapt_full.json은 오류 수정 이후 산출물이다. 이 둘을 같은 snapshot으로 취급하지 않는다. 소스 ZIP에 환경 증거를 매번 넣지 않고, run이 source hash를 참조하도록 한다.

`verify_release.py`는 배포 파일 원형 확인용이다. 개발로 소스를 수정하는 것은 허용되지만 기존 run의 같은 source 버전으로 재검산했다고 쓰지는 않는다. 변경 후에는 새 실험 식별자와 source hash로 실행한다.
