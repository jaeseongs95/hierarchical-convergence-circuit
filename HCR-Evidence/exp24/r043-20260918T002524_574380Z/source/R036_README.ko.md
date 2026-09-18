# R0.3.6 / EXP-17 추가 실험 도구

EXP-16의 동일 상태 proof 선택 대조에서 다음으로 이동한다: **입력 재표현 → 새 native Graph 실행 → 실제 readout별 proof 선택 대조**.

기존 native source는 수정하지 않는다. EXP-15의 동결 memory와 기본 입력 8개, prior 2개, 입력 재표현 8개를 사용해 128개 native trial을 계획한다. 경로와 activation을 사후 보정하지 않는다. 세 선택 정책은 native 계산을 제어하지 않고 얻어진 같은 readout에서 비교된다.

실행:

```powershell
python -X utf8 -B Run-HCR-R036.py --out HCR-Evidence/exp17/r036-first
```

- 설계: `docs/R036_DESIGN.ko.md`
- 적용/실행: `docs/R036_USAGE.ko.md`
- 개발 검증 범위: `docs/R036_ACCEPTANCE.ko.md`
- 새 모듈: `tools/r036_input_representation/`
- 핵심 결과: `analysis/summary.ko.md`, `analysis/audit.json`

현재 단계는 자율 수정 controller 구현이 아니라 입력에서 지지 경로가 형성되는지의 판별 실험이다.
