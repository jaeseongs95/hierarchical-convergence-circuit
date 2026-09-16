# EXP-08 — R0.2 Adaptive Graph/Circuit 개발 통합 protocol

상태: 실행 코드 작성, 이 배포 세션 미실행. 엔진은 `src/hcr` 공통 구현을 사용한다.

## 목적 및 경계

R0.1 baseline은 보존하고 D-expansion/부분회로/경쟁/학습 순환이 연결되는지 확인한다. A/M 자동화를 함께 추가하지 않는다. 데이터는 symbolic fixture이며 연구적 holdout 성능 평가가 아니다.

## 사전 고정된 조건

- Training: 객체/episode를 달리한 양의 길이3 chain 6회. 외부 검증한 직접 proof에서 길이2·3 motif를 등록한다.
- Familiarity: 같은 구조, 강한 반대 관측, 재명명+edge 순서 변경을 cold memory/warm memory에 동일 입력으로 제공한다.
- Novelty: 길이4 조합과 diamond 분기. 같은 memory snapshot/입력을 full 및 graph-only에 제공한다. circuit 사용 차이 이외의 지원 정보를 동일하게 한다.
- Misconvergence: `(-0.06, 0.92, 0.92)`의 약한 충돌 입력을 full/no-reexpansion으로 비교한다. 실제 오답일 때만 feedback 뒤 추가 측정을 요청한다.
- Retention: full의 수정 후 checkpoint를 reload해 새로운 episode의 같은 측정 profile에 적용한다.
- Compression/flexibility: training3/9를 별도 memory로 시작하고 같은 약한 충돌 profile에서 비교한다.

실험 분류 문자열과 hidden truth는 evaluation 계층에만 있다. 엔진 입력의 episode/object ID는 opaque 값이다. 원형/재명명 효과를 신규 topology 검증과 같은 것으로 세지 않는다. 입력마다 별도 추론 및 외부 평가를 기록한다.

## 주요 지표

정답/오답/보류, 근거와 assumption까지 포함한 정답, wrong_stable, primitive proof D, dependency nodes/arcs/expansions, binding scan, candidate count, pool calls, signal operations, proof reconstruction, learning/storage, wall time.

정확도 상승이나 총비용 감소를 성공하도록 하드코딩하지 않는다. 같은 값/반대 결과도 그대로 summary에 남긴다. wall time은 단일 개발 실행 계측으로, 안정적 benchmark 추정치가 아니다.

## 실행

```powershell
python -X utf8 -B hcr.py demo --engine r02 --config configs/r02.toml --out runs/r02_first
python -X utf8 -B hcr.py verify --run runs/r02_first
```

원래 EXP-01~07의 연구 가설 문서는 덮어쓰지 않는다. 이 protocol은 그 일부 메커니즘에 대한 R0.2의 구체적 개발 실험이다.
