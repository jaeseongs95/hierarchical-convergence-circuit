# R0.3.5 — EXP-16 고정 상태 proof 선택 실험

현재 native 기준선은 EXP-15 커밋 `a9c643954696cbe309f29691bf63e5d4fe463f91`이다. 이 추가 패키지는 기존 `src/hcr`와 과거 evidence를 변경하지 않는다.

```powershell
python -X utf8 -B .\Run-HCR-R035.py --out "HCR-Evidence\exp16\r035-first"
```

기존 회귀시험, EXP-15 재검산, EXP-16 조건 동결/선택 실행/별도 audit/재검산 순으로 수행한다. `--check-only`는 앞의 검사만 수행한다. 실제 실행·commit/push는 사용자 환경에서 한다.

이번 실험은 동일 readout 상태에서 native 보존 / native 재구성 / support-first의 차이를 분리한다. node/edge 이름과 edge slot/경로 순서의 16개 조합은 **선택 경계**에만 적용한다. 입력부터의 Graph 형성 강건성이나 자율 controller의 학습 결과로 해석하지 않는다.

- 설계: `docs/R035_DESIGN.ko.md`
- 사용: `docs/R035_USAGE.ko.md`
- 배포 검증: `docs/R035_ACCEPTANCE.ko.md`
- 결과: 지정한 EXP-16 폴더의 `analysis/summary.ko.md`

원 EXP-15 실행 자료 `HCR-Evidence/exp15/r034-first`도 계속 보관한다. 이 패키지는 source audit 계약을 유지하기 위해 native `__version__`과 과거 release manifest를 변경하지 않는 추가 실험 패키지다.
